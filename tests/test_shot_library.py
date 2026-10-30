import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import app as w
import shot_tools
from shot_models import ShotRender
from fastapi.testclient import TestClient


class ShotLibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.old=w.DATA
        w.DATA=Path(self.temp.name); self.c=TestClient(w.app,base_url='http://localhost')
        self.pid=self.c.post('/api/projects',json={'title':'Shot parameter contract','simulation':True}).json()['id']
        self.url=f'/api/projects/{self.pid}/shot-renders'
        self.body={'request_id':'first','project_revision':1,'reason':'Explain a change with readable text',
                   'shot':{'kind':'typewriter-rewrite','title':'判断与行动','initial':'只凭感觉','replacement':'根据证据做判断'},
                   'duration':4.,'width':640,'height':360}

    def tearDown(self):
        self.c.close();w.DATA=self.old;self.temp.cleanup()

    def queued(self,path,mid,kind,task):
        self.worker=task
        job={'id':'a'*32,'kind':kind,'media_id':None,'status':'queued','created_at':w.now()}
        w.write(path/'jobs'/(job['id']+'.json'),job);return job

    def test_catalog_discovery_distinguishes_reference_and_execution(self):
        r=self.c.get('/api/visual/shots').json()
        self.assertEqual(len(r['cards']),124);self.assertEqual(len(r['adaptations']),9)
        self.assertEqual(sum(len(c['styles']) for c in r['cards']),150)
        self.assertEqual(len(self.c.get('/api/visual/shots?status=adapted_subset').json()['cards']),9)
        self.assertTrue(self.c.get('/api/visual/shots?q=打字').json()['cards'])
        self.assertEqual(self.c.get('/api/visual/shots?status=executable').status_code,422)
        caps=self.c.get('/api/agent/v1/capabilities').json()
        self.assertIn('render_shot',caps['actions']);self.assertIn('shot-render',caps['schemas'])
        schema=self.c.get(caps['schemas']['shot-render']).json()
        self.assertEqual(len(schema['properties']['shot']['oneOf']),9)
        self.assertEqual(self.c.get('/ui/').status_code,404)

    def test_schema_rejects_code_urls_nan_wrong_clocks_and_unknown_shots(self):
        for change in [{'fps':24},{'duration':float('inf')},{'width':641},
                       {'width':640,'height':400},{'shot':{'kind':'unadapted-demo','title':'x'}},
                       {'shot':{'kind':'marker-title','title':'x','code':'process.exit()'}}]:
            b=copy.deepcopy(self.body);b.update(change)
            with self.assertRaises(ValueError):ShotRender.model_validate(b)
        b=copy.deepcopy(self.body);b['shot']={'kind':'before-after','title':'Compare',
            'before':{'asset_id':'https://example.com/a.png','sha256':'a'*64},
            'after':{'asset_id':'a'*32,'sha256':'a'*64}}
        with self.assertRaises(ValueError):ShotRender.model_validate(b)

    def test_missing_optional_runtime_and_stale_requests_do_not_change_project(self):
        with patch.object(shot_tools,'runtime_status',return_value={'available':False}):
            self.assertEqual(self.c.post(self.url,json=self.body).status_code,503)
        b=copy.deepcopy(self.body);b['project_revision']=2
        self.assertEqual(self.c.post(self.url,json=b).status_code,409)
        self.assertEqual(w.read(w.DATA/self.pid/'project.json')['revision'],1)
        self.assertFalse(list((w.DATA/self.pid/'jobs').glob('*.json')))
        self.assertEqual(len(list((w.DATA/self.pid/'shot-attempts').glob('*.json'))),2)

    def test_frozen_request_replay_conflicts_and_tamper_detection(self):
        with patch.object(shot_tools,'runtime_status',return_value={'available':True,'node':'node','browser':'browser'}),patch.object(w,'launch',side_effect=self.queued):
            response=self.c.post(self.url,json=self.body);self.assertEqual(response.status_code,200,response.text)
            first=response.json();dest=w.DATA/self.pid/'shot-renders'/first['render_id']
            self.assertEqual(w.read(dest/'request.json')['request'],ShotRender.model_validate(self.body).model_dump())
            self.assertEqual(self.c.post(self.url,json=self.body).json()['idempotent_replay'],True)
            changed=copy.deepcopy(self.body);changed['shot']['replacement']='Changed'
            self.assertEqual(self.c.post(self.url,json=changed).status_code,409)
            self.assertEqual(w.read(w.DATA/self.pid/'project.json')['revision'],2)
            frozen=w.read(dest/'props.json');frozen['shot']['title']='Tampered';w.write(dest/'props.json',frozen)
            with self.assertRaisesRegex(ValueError,'props changed'):self.worker()
            self.assertEqual(len(w.read(w.DATA/self.pid/'project.json')['media']),0)

    def test_text_overflow_and_unregistered_images_reject_before_jobs(self):
        with patch.object(shot_tools,'runtime_status',return_value={'available':True}):
            b=copy.deepcopy(self.body);b['shot']['title']='\n'.join(['文字']*45)
            self.assertEqual(self.c.post(self.url,json=b).status_code,422)
            b=copy.deepcopy(self.body);b['shot']={'kind':'before-after','title':'Compare',
                'before':{'asset_id':'a'*32,'sha256':'a'*64},'after':{'asset_id':'b'*32,'sha256':'b'*64}}
            self.assertEqual(self.c.post(self.url,json=b).status_code,422)
        self.assertEqual(w.read(w.DATA/self.pid/'project.json')['revision'],1)
        self.assertFalse(list((w.DATA/self.pid/'jobs').glob('*.json')))


if __name__=='__main__':unittest.main()
