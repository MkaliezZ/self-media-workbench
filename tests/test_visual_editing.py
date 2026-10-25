"""Real FFmpeg composition and isolated API checks; manually aligned synthetic input.

VISUAL_EVIDENCE_ROOT retains all original attempts and exports for inspection.
This suite does not measure ASR accuracy, listening quality or publishing effect.
"""
import copy
import json
import os
import struct
import subprocess
import sys
import tempfile
import time
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
from fixture_tools import fixture_path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from fastapi.testclient import TestClient
import app as w
from visual_tools import sha, geometry, status


def make_image(path):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    # Self-generated diagram: red left half, green right half, 160 x 80.
    row=b'\x00'+bytes([255,0,0])*80+bytes([0,255,0])*80
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',160,80,8,2,0,0,0))+
        chunk(b'IDAT',zlib.compress(row*80))+chunk(b'IEND',b''))


class VisualEditingTests(unittest.TestCase):
    def setUp(self):
        root=os.environ.get('VISUAL_EVIDENCE_ROOT')
        if root:Path(root).mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='visual-',dir=root)
        self.data=Path(self.temp.name)
        (self.data/'projects').mkdir()
        self.patch=patch.object(w,'DATA',self.data/'projects');self.patch.start()
        self.client=TestClient(w.app,base_url='http://localhost')
        self.project=self.client.post('/api/projects',json={'title':'本地视觉合成测试','simulation':True}).json()
        self.pid=self.project['id'];self.path=w.DATA/self.pid
        imported=self.client.post(f'/api/projects/{self.pid}/media',json={
            'path':str(fixture_path()),'media_nature':'generated',
            'source_note':'Self-generated colour video and sine wave; manually aligned text, not real speech',
            'usage_scope':'technical tests only'})
        self.assertEqual(imported.status_code,200,imported.text)
        self.media=imported.json()['media'];self.mid=self.media['id']
        self.url=f'/api/projects/{self.pid}/media/{self.mid}'
        self.review={'duration':4.,'revision':0,'source_sha256':self.media['sha256'],
            'words':[{'id':0,'text':'不保证','start':.2,'end':.8},
                     {'id':1,'text':'都适用','start':2.1,'end':3.0}],
            'caption_groups':[[0],[1]],'selected_ids':[],
            'candidates':[{'id':'gap','start':1.0,'end':1.7}]}
        self.out=self.path/'media'/self.mid/'asr/run1'
        w.write(self.out/'review.json',self.review);w.write(self.out/'transcript.original.json',self.review)
        w.write(self.path/'media'/self.mid/'current-asr.json',{'run_id':'run1'})
        self.image=self.data/'自行绘制 配图.png';make_image(self.image)
        self.body={'request_id':'visual-1','project_revision':self.context()['project']['revision'],
            'review_revision':0,'asr_run':'run1','source_sha256':self.media['sha256'],
            'reason':'Verify local composition, not semantic acceptance',
            'captions':{'font_height':.07},
            'emphasis':[{'word_ids':[0],'reason':'Keep the negative together'}],
            'images':[{'word_ids':[1],'reason':'Show colour diagram at the explanation',
                'path':str(self.image),'sha256':sha(self.image),'nature':'illustration',
                'source_note':'Self-generated two-colour PNG','usage_scope':'technical tests',
                'slot':{'x':.5,'y':.1,'width':.5,'height':.5},
                'highlight':{'x':0.,'y':0.,'width':.5,'height':1.}}],
            'regions':[{'word_ids':[0],'reason':'Direct attention to the top-left region',
                'rect':{'x':.05,'y':.05,'width':.2,'height':.2}}]}

    def tearDown(self):
        self.client.close();self.patch.stop()
        if os.environ.get('VISUAL_EVIDENCE_ROOT'):
            self.temp._finalizer.detach()
        else:self.temp.cleanup()

    def context(self):return self.client.get(f'/api/agent/v1/projects/{self.pid}/context').json()

    def save(self,body=None):return self.client.post(self.url+'/visual-plans',json=body or self.body)

    def export(self,plan,revision=0):
        result=self.client.post(self.url+'/export',json={'revision':revision,'asr_run':'run1',
            'source_sha256':self.media['sha256'],'visual_plan_id':plan['id']})
        self.assertEqual(result.status_code,200,result.text)
        job=result.json();deadline=time.monotonic()+90
        while job['status'] not in ('done','failed') and time.monotonic()<deadline:
            time.sleep(.05)
            job=self.client.get(f'/api/projects/{self.pid}/jobs/'+job['id']).json()
        self.assertEqual(job['status'],'done',json.dumps(job,ensure_ascii=False))
        dest=self.path/'exports'/job['result']['export_id']
        subprocess.run(['ffmpeg','-v','error','-i',str(dest/'visual.mp4'),'-f','null','-'],check=True,capture_output=True)
        return dest

    def test_real_composition_cut_restore_and_pixels(self):
        self.assertTrue(status()['available'],status())
        original=sha(self.path/self.media['relative_path'])
        saved=self.save();self.assertEqual(saved.status_code,200,saved.text)
        first=saved.json();dest=self.export(first)
        baseline_hash=sha(dest/'visual.mp4')
        timeline=w.read(dest/'visual-timeline.json')
        self.assertTrue(timeline['captions'][0]['emphasized'])
        self.assertEqual(timeline['captions'][0]['text'],'不保证')
        placement=timeline['events'][0]['placed_rect']
        self.assertEqual(placement,{'x':160,'y':44,'width':160,'height':80})
        # Actual decoded RGB, not only a plan/command assertion.
        raw=subprocess.check_output(['ffmpeg','-v','error','-ss','2.4','-i',str(dest/'visual.mp4'),
            '-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-'])
        pixel=lambda x,y:tuple(raw[(y*320+x)*3:(y*320+x)*3+3])
        self.assertGreater(pixel(180,80)[0],180);self.assertGreater(pixel(290,80)[1],180)
        self.assertLess(pixel(40,80)[0],30)  # unchanged blue source outside overlay
        for revision,selected,offset in [(0,['gap'],.7),(1,[],0.)]:
            change=self.client.put(self.url+'/review',json={'revision':revision,'asr_run':'run1',
                'source_sha256':self.media['sha256'],'selected_ids':selected})
            self.assertEqual(change.status_code,200,change.text)
            self.assertTrue(self.context()['visual_plans'][0]['stale'])
            stale=self.client.post(self.url+'/export',json={'revision':revision+1,'asr_run':'run1',
                'source_sha256':self.media['sha256'],'visual_plan_id':first['id']})
            self.assertEqual(stale.status_code,409,stale.text)
            body={**self.body,'request_id':f'revision-{revision+1}','review_revision':revision+1,
                'project_revision':self.context()['project']['revision']}
            result=self.save(body);self.assertEqual(result.status_code,200,result.text)
            output=self.export(result.json(),revision+1)
            event=w.read(output/'visual-timeline.json')['events'][0]
            self.assertAlmostEqual(event['start'],2.1-offset,places=5)
        self.assertEqual(sha(dest/'visual.mp4'),baseline_hash)
        self.assertEqual(sha(self.path/self.media['relative_path']),original)
        self.assertEqual(w.read(self.out/'transcript.original.json'),self.review)

    def test_invalid_bindings_assets_and_replay_are_recorded(self):
        variations=[({'review_revision':4},409),({'project_revision':999},409),
                    ({'asr_run':'old'},409),({'source_sha256':'b'*64},409),
                    ({'emphasis':[{'word_ids':[99],'reason':'bad'}]},422),
                    ({'emphasis':[{'word_ids':[0,1],'reason':'not a cue'}]},422)]
        for fields,expected in variations:
            response=self.save({**self.body,**fields})
            self.assertEqual(response.status_code,expected,response.text)
        wrong=copy.deepcopy(self.body);wrong['images'][0]['sha256']='a'*64
        self.assertEqual(self.save(wrong).status_code,422)
        invalid=copy.deepcopy(self.body);invalid['images'][0]['slot']['x']=.9
        self.assertEqual(self.save(invalid).status_code,422)
        response=self.save();self.assertEqual(response.status_code,200,response.text)
        replay=self.save();self.assertEqual(replay.json()['id'],response.json()['id'])
        self.assertTrue(replay.json()['idempotent_replay'])
        self.assertEqual(self.save({**self.body,'reason':'changed'}).status_code,409)
        attempts=[w.read(p) for p in (self.path/'media'/self.mid/'visual-attempts').glob('*.json')]
        self.assertEqual(sum(not a['accepted'] for a in attempts),9)
        record=response.json();frozen=self.path/'media'/self.mid/'visual-plans'/record['id']/record['assets'][0]['relative_path']
        frozen.write_bytes(b'tampered')
        result=self.client.post(self.url+'/export',json={'revision':0,'asr_run':'run1',
            'source_sha256':self.media['sha256'],'visual_plan_id':record['id']})
        self.assertEqual(result.status_code,409,result.text)

    def test_agent_discovery_image_intake_and_deleted_anchors(self):
        caps=self.client.get('/api/agent/v1/capabilities').json()
        self.assertIn('visual-plan',caps['schemas'])
        self.assertEqual(self.client.get(caps['schemas']['visual-plan']).status_code,200)
        task=self.client.post('/api/agent/v1/tasks',json={'task':'继续给画面配图','project':self.pid,
            'input_paths':[str(self.image)],'source_note':'Self-generated image','usage_scope':'test'})
        self.assertEqual(task.status_code,200,task.text)
        self.assertEqual(task.json()['intent'],'edit')
        asset=task.json()['registered'][0];self.assertEqual(asset['kind'],'image')
        self.assertEqual(sha(Path(asset['path'])),sha(self.image))
        deleted=self.client.put(self.url+'/review',json={'revision':0,'asr_run':'run1',
            'source_sha256':self.media['sha256'],'speech_cuts':[{'id':'omit-1','kind':'mistake',
            'word_ids':[1],'reason':'Controlled test deletion'}],'caption_groups':[[0]]})
        self.assertEqual(deleted.status_code,200,deleted.text)
        body={**self.body,'project_revision':self.context()['project']['revision'],'review_revision':1}
        self.assertEqual(self.save(body).status_code,422)

    def test_literal_text_and_preserved_failed_render_then_revision(self):
        self.review['words'][0]['text']='字{\\N}%{n}'
        w.write(self.out/'review.json',self.review)
        saved=self.save();self.assertEqual(saved.status_code,200,saved.text)
        dest=self.export(saved.json())
        self.assertEqual(w.read(dest/'visual-timeline.json')['captions'][0]['display_text'],'字{\\N}%{n}')
        # Excessively long unreviewed wording must fail instead of spilling off screen.
        self.review['revision']=1;self.review['words'][0]['text']='过长字幕'*60
        w.write(self.out/'review.json',self.review)
        body={**self.body,'request_id':'too-long','review_revision':1,
            'project_revision':self.context()['project']['revision']}
        saved=self.save(body);self.assertEqual(saved.status_code,200,saved.text)
        queued=self.client.post(self.url+'/export',json={'revision':1,'asr_run':'run1',
            'source_sha256':self.media['sha256'],'visual_plan_id':saved.json()['id']}).json()
        deadline=time.monotonic()+90
        while queued['status'] not in ('done','failed') and time.monotonic()<deadline:
            time.sleep(.05);queued=self.client.get(f'/api/projects/{self.pid}/jobs/'+queued['id']).json()
        self.assertEqual(queued['status'],'failed',queued)
        self.assertIn('too long',queued['error'])
        failed_dirs=[p for p in (self.path/'exports').iterdir() if not (p/'provenance.json').exists()]
        self.assertEqual(len(failed_dirs),1)
        self.assertTrue((failed_dirs[0]/'reviewed_cut.mp4').exists())
        self.review['revision']=2;self.review['words'][0]['text']='不保证'
        w.write(self.out/'review.json',self.review)
        fixed={**body,'request_id':'shortened','review_revision':2,
            'project_revision':self.context()['project']['revision']}
        saved=self.save(fixed);self.assertEqual(saved.status_code,200,saved.text)
        self.export(saved.json(),2)
        self.assertTrue((failed_dirs[0]/'reviewed_cut.mp4').exists())

    def test_multiple_images_jpeg_and_captions_disabled(self):
        jpg=self.data/'第二张.jpg'
        subprocess.run(['ffmpeg','-v','error','-i',str(self.image),'-frames:v','1',str(jpg)],check=True,capture_output=True)
        body=copy.deepcopy(self.body)
        body['captions']={'enabled':False};body['emphasis']=[];body['regions']=[]
        extra=copy.deepcopy(body['images'][0]);extra.update({'path':str(jpg),'sha256':sha(jpg)})
        extra['slot']={'x':0.,'y':.1,'width':.4,'height':.4}
        body['images'].append(extra)
        saved=self.save(body);self.assertEqual(saved.status_code,200,saved.text)
        output=self.export(saved.json())
        timeline=w.read(output/'visual-timeline.json')
        self.assertEqual(len(timeline['events']),2);self.assertEqual(timeline['captions'],[])


if __name__=='__main__':unittest.main()
