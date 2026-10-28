"""Meaningful scene, provenance, revision and physical-adapter boundaries."""
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import app as w
from lighting_models import Scene,Fixture
from lighting_tools import generate_tiers,calculate,segment_hit
from task_api import infer_intent


class LightingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        self.patcher=patch.object(w,'DATA',self.path);self.patcher.start()
        self.client=TestClient(w.app,base_url='http://localhost')
        self.project=self.client.post('/api/projects',json={'title':'布光隔离验收','simulation':True}).json()
        self.base='/api/projects/'+self.project['id']+'/lighting'
        b=io.BytesIO();Image.new('RGB',(360,240),'#efe9d2').save(b,format='PNG');self.raw=b.getvalue()
        v=self.client.post(self.base+'/images?name=scene.png',content=self.raw).json()
        self.image=v['image'];self.revision=v['revision']

    def tearDown(self):self.client.close();self.patcher.stop();self.temp.cleanup()

    def body(self,**scene):
        return {'request_id':uuid.uuid4().hex,'project_revision':self.revision,
                'scene':{'image_ids':[self.image['id']],**scene}}

    def test_upload_decodes_dedups_and_does_not_claim_image_understanding(self):
        self.assertEqual(self.image['sha256'],hashlib.sha256(self.raw).hexdigest())
        v=self.client.post(self.base+'/images',content=self.raw).json()
        self.assertTrue(v['reused']);self.assertEqual(v['revision'],self.revision)
        r=self.client.get(self.base+'/images/'+self.image['id'])
        self.assertEqual(r.headers['content-type'],'image/png')
        self.assertEqual(r.content,self.raw)
        p=self.client.get('/api/projects/'+self.project['id']).json()
        self.assertEqual(p['verification'],'needs_review')
        self.assertEqual(self.client.post(self.base+'/images',content=b'bad').status_code,422)
        self.assertEqual(self.client.get('/api/projects/'+p['id']).json()['revision'],p['revision'])

    def test_assumption_only_upload_gives_three_honest_drafts(self):
        r=self.client.post(self.base+'/plans',json=self.body())
        self.assertEqual(r.status_code,200,r.text);p=r.json()['plan']
        self.assertEqual([t['id'] for t in p['tiers']],['simple','standard','ideal'])
        self.assertTrue(any('未进行图片' in a for a in p['assumptions']))
        for tier in p['tiers']:
            for light in tier['lights']:
                self.assertIsNone(light['distance_m']);self.assertIsNone(light['power']['input_watts'])
                self.assertIsNone(light['calculation'])
        self.assertEqual(p['status'],'needs_review');self.assertEqual(p['human_acceptance'],'not_tested')

    def test_window_changes_simple_but_not_all_tiers(self):
        v=self.client.post(self.base+'/plans',json=self.body(windows=[{'point':{'x':0.,'y':.3},'usable':True}],assessment='user_confirmed')).json()['plan']
        self.assertEqual(v['tiers'][0]['lights'][0]['kind'],'window')
        self.assertEqual(v['tiers'][1]['lights'][0]['kind'],'lamp')
        self.assertEqual(v['tiers'][0]['new_powered_lights'],0)

    def test_scale_geometry_obstacles_and_actual_layout_share_positions(self):
        body=self.body(width_m=4.,depth_m=3.,ceiling_m=2.6,face_height_m=1.25,
            obstacles=[{'label':'左侧柜子','x':0.,'y':.25,'width':.39,'depth':.5,'height_m':2.2}])
        p=self.client.post(self.base+'/plans',json=body).json()['plan']
        key=p['tiers'][0]['lights'][0]
        self.assertGreater(key['point']['x'],.39)
        text=self.client.get(self.base+'/plans/'+p['id']+'/files/simple.svg').text
        self.assertIn('L1',text);self.assertIn('主光',text)
        self.assertTrue(key['distance_m']>0)
        self.assertNotIn('<script',text)
        self.assertEqual(self.client.get(self.base+'/plans/'+p['id']+'/files/../../project.json').status_code,404)

    def test_tiny_room_returns_conditional_instead_of_outside_positions(self):
        p=self.client.post(self.base+'/plans',json=self.body(width_m=.6,depth_m=.6)).json()['plan']
        self.assertTrue(all(t['feasibility']=='conditional' for t in p['tiers']))
        self.assertTrue(all(not t['lights'] for t in p['tiers']))

    def test_revision_idempotency_selection_history_and_feedback(self):
        body=self.body();a=self.client.post(self.base+'/plans',json=body).json();p=a['plan']
        retry=self.client.post(self.base+'/plans',json=body).json();self.assertTrue(retry['idempotent_replay'])
        wrong={**body,'revision_reason':'改变请求'}
        self.assertEqual(self.client.post(self.base+'/plans',json=wrong).status_code,409)
        pick=self.client.post(self.base+'/plans/'+p['id']+'/select',json={'project_revision':a['revision'],'tier':'standard'}).json()
        self.assertEqual(pick['selection']['tier'],'standard')
        newbody=self.body();newbody.update(project_revision=pick['revision'],supersedes=p['id'])
        b=self.client.post(self.base+'/plans',json=newbody).json()
        self.assertEqual(self.client.get(self.base+'/plans/'+p['id']).json(),p)
        self.assertEqual(self.client.post(self.base+'/plans/'+p['id']+'/select',json={'project_revision':b['revision'],'tier':'simple'}).status_code,409)
        feedback={'project_revision':b['revision'],'tier':'standard','note':'眼镜反光','next_adjustment':'只移动主光侧向','measured_lux':300.}
        target=self.base+'/plans/'+b['plan']['id']+'/field-checks'
        self.assertEqual(self.client.post(target,json=feedback).status_code,422)
        feedback['measurement_point']='面部位置，传感器朝向相机'
        f=self.client.post(target,json=feedback)
        self.assertEqual(f.status_code,200,f.text)
        self.assertEqual(f.json()['field_check']['human_acceptance'],'not_independently_verified')
        ctx=self.client.get('/api/agent/v1/projects/'+self.project['id']+'/context').json()
        self.assertEqual(len(ctx['lighting']['plans']),2);self.assertEqual(len(ctx['lighting']['field_checks']),1)

    def test_tampered_and_foreign_images_are_not_silently_reused(self):
        invalid=self.body(image_ids=[uuid.uuid4().hex])
        self.assertEqual(self.client.post(self.base+'/plans',json=invalid).status_code,422)
        Path(self.image['path']).write_bytes(b'tampered')
        self.assertEqual(self.client.post(self.base+'/plans',json=self.body()).status_code,409)

    def test_partial_dimensions_nonfinite_and_false_agent_review_rejected(self):
        for extra in ({'width_m':4.},{'width_m':float('inf'),'depth_m':3.},
                      {'assessment':'agent_reviewed'},{'subject':{'x':2.,'y':.5}}):
            body=self.body(**extra)
            r=self.client.post(self.base+'/plans',content=json.dumps(body),headers={'content-type':'application/json'})
            self.assertEqual(r.status_code,422,r.text)
        self.assertEqual(self.client.get(self.base+'/plans').json()['plans'],[])

    def test_matching_photometry_and_minimum_distance(self):
        photo={'reference_lux':1000.,'reference_distance_m':1.,'modifier':'裸灯','cct_k':5600,
               'source':'合成数学验收数据，不是真实灯具','measured_at':'synthetic','basis':'user_measurement','minimum_distance_m':.5}
        fixture=Fixture(label='模拟灯',input_watts=78.,modifier='裸灯',photometry=photo)
        scene=Scene(width_m=4.,depth_m=4.,face_height_m=1.2,ceiling_m=2.8)
        lamp={'point':{'x':.5,'y':.7},'height_m':1.2}
        v=calculate(scene,lamp,fixture)
        self.assertAlmostEqual(v['illuminance_lux'],1000.,delta=.1)
        lamp['point']['y']=.95
        v2=calculate(scene,lamp,fixture);self.assertAlmostEqual(v2['illuminance_lux'],250.,delta=.1)
        bad={**fixture.model_dump(),'modifier':'柔光箱'}
        with self.assertRaises(ValueError):Fixture(**bad)
        lamp['point']['y']=.5
        self.assertIsNone(calculate(scene,lamp,fixture)['illuminance_lux'])

    def test_obstacle_height_distinguishes_overhead_ray(self):
        from lighting_models import Obstacle
        ob=Obstacle(label='矮桌',x=.2,y=.2,width=.2,depth=.2,height_m=.7)
        self.assertFalse(segment_hit((0,0),(2,2),ob,4,4,1.6,1.2))
        self.assertTrue(segment_hit((0,0),(2,2),ob,4,4,.5,.5))

    def test_routes_schema_and_frontend_entry(self):
        self.assertEqual(infer_intent('按照片给三档打光方案'),'lighting')
        self.assertEqual(infer_intent('不要打光，只写脚本'),'script')
        task=self.client.post('/api/agent/v1/tasks',json={'task':'给这张图布光','project':self.project['id']}).json()
        self.assertEqual(task['start_at'],'lighting');self.assertIn('lighting',task)
        for name in ('lighting-plan','lighting-scene','lighting-selection','lighting-field-check'):
            self.assertEqual(self.client.get('/api/agent/v1/schemas/'+name).status_code,200)
        page=self.client.get('/ui/');self.assertEqual(page.status_code,200);self.assertIn('拍摄布光',page.text)
        self.assertEqual(self.client.get('/ui/lighting.html').status_code,200)
        self.assertEqual(self.client.get('/ui/lighting.js').status_code,200)

    def test_optional_real_radiance_cross_check(self):
        from lighting_radiance import binaries
        if not binaries():self.skipTest('Optional Radiance not configured on this host')
        photo={'reference_lux':1000.,'reference_distance_m':1.,'modifier':'裸灯','cct_k':5600,
               'source':'合成数据，非厂商测光','measured_at':'synthetic','basis':'user_measurement','minimum_distance_m':.5}
        p=self.client.post(self.base+'/plans',json=self.body(width_m=4.,depth_m=4.,face_height_m=1.2,ceiling_m=2.7,
            fixtures=[{'label':'模拟灯','modifier':'裸灯','input_watts':78.,'photometry':photo}])).json()['plan']
        tier=p['tiers'][0];self.assertEqual(tier['radiance']['state'],'done',tier['radiance'])
        analytic=tier['lights'][0]['calculation']['illuminance_lux']
        self.assertAlmostEqual(tier['radiance']['illuminance_lux']/analytic,1.,delta=.02)
        self.assertEqual(tier['radiance']['included_lights'],['L1'])
        ideal=p['tiers'][2]['radiance']
        self.assertEqual(ideal['included_lights'],['L1'])
        self.assertEqual(ideal['excluded_lights'],['L2','L3'])
        self.assertIn('非整套方案总照度',ideal['scope'])
        report=self.client.get(self.base+'/plans/'+p['id']+'/files/report.html').text
        self.assertIn('78.0W',report)
        self.assertIn('合成数据，非厂商测光',report)


if __name__=='__main__':unittest.main()
