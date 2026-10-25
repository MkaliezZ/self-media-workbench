"""Real native timeline, music/visual clocks, revision recovery and multitrack audio."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'));sys.path.insert(0,str(ROOT/'scripts'))
import app as w
from fastapi.testclient import TestClient
from timeline_case import exercise
from visual_tools import sha,probe


class NativeTimelineTests(unittest.TestCase):
    def setUp(self):
        root=os.environ.get('TIMELINE_EVIDENCE_ROOT')
        if root:Path(root).mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='native-',dir=root);self.folder=Path(self.temp.name).resolve()
        if root:self.temp._finalizer.detach()  # Retain failures even when setUp cannot finish.
        self.data=self.folder/'state/projects';self.data.mkdir(parents=True)
        self.patch=patch.object(w,'DATA',self.data);self.patch.start()
        self.client=TestClient(w.app,base_url='http://localhost')
        self.result=exercise(self.client,self.folder)
        self.pid=self.result['project_id'];self.base=f'/api/projects/{self.pid}';self.project=self.data/self.pid
        self.record=self.result['plan'];self.plan=self.record['request']
        self.original=self.project/'exports'/self.result['job']['result']['export_id']/'timeline.mp4'

    def tearDown(self):
        self.client.close();self.patch.stop()
        if os.environ.get('TIMELINE_EVIDENCE_ROOT'):self.temp._finalizer.detach()
        else:self.temp.cleanup()

    def context(self):return self.client.get(f'/api/agent/v1/projects/{self.pid}/context').json()

    def save(self,body):return self.client.post(self.base+'/timeline-plans',json=body)

    def export(self,id):
        response=self.client.post(self.base+'/timeline/export',json={'plan_id':id});self.assertEqual(response.status_code,200,response.text)
        job=response.json();deadline=time.monotonic()+120
        while job['status'] not in ('done','failed') and time.monotonic()<deadline:
            time.sleep(.05);job=self.client.get(self.base+'/jobs/'+job['id']).json()
        self.assertEqual(job['status'],'done',job)
        return self.project/'exports'/job['result']['export_id']/'timeline.mp4'

    def audio(self,file):
        data=subprocess.check_output(['ffmpeg','-v','error','-i',str(file),'-vn','-ac','1','-ar','48000','-f','f32le','-'])
        return np.frombuffer(data,dtype='<f4')

    def test_actual_frames_durations_and_scene_identity(self):
        meta=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(self.original)]))
        video=next(s for s in meta['streams'] if s['codec_type']=='video')
        self.assertEqual(int(video['nb_read_frames']),300);self.assertEqual((video['width'],video['height']),(640,360))
        for shot in self.record['map']['shots']:
            segment=self.original.parent/f"segment-{self.record['map']['shots'].index(shot):04}.mkv"
            actual=probe(segment,count_frames=True)
            stream=next(s for s in actual['streams'] if s['codec_type']=='video')
            self.assertEqual(int(stream['nb_read_frames']),shot['frames'])
            self.assertAlmostEqual(len(self.audio(segment)),shot['frames']/25*48000,delta=1)
        subprocess.run(['ffmpeg','-v','error','-i',str(self.original),'-f','null','-'],check=True,capture_output=True)
        for i,t in enumerate([.8,3.8,6.8,10.]):
            source=self.folder/'materials'/f'scene-{i}.mp4';local=t-self.record['map']['shots'][i]['output_start']
            def frame(path,at,filter=None):
                command=['ffmpeg','-v','error','-ss',str(at),'-i',str(path)]
                if filter:command+=['-vf',filter]
                return np.frombuffer(subprocess.check_output(command+['-frames:v','1','-pix_fmt','rgb24','-f','rawvideo','-']),dtype='uint8').reshape(360,640,3)
            actual=frame(self.original,t)
            expected=frame(source,local,'scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2:color=0x16181A')
            difference=np.abs(actual[:240].astype(float)-expected[:240].astype(float)).mean()
            self.assertLess(difference,7.,(i,difference))
        self.assertTrue(all(abs(e['error_seconds'])<=1/25 for e in self.record['map']['beat_alignment']))

    def test_onset_timing_and_no_asr_for_silent_sources(self):
        analysis=json.loads((self.folder/'music-analysis.json').read_text('utf-8'))
        errors=[min(abs(c['source_time']-target) for c in analysis['candidates']) for target in np.arange(.5,13.6,.5)]
        self.assertLess(max(errors),.025)
        self.assertLess(float(np.median(errors)),.015)
        self.assertFalse(any(m.get('asr') for m in self.context()['media']))
        silent=self.context()['media'][1]
        self.assertFalse(silent['has_audio'])
        self.assertEqual(self.client.post(self.base+'/media/'+silent['id']+'/transcribe').status_code,422)

    def test_revision_cut_restore_idempotency_and_invalid_requests(self):
        initial_hash=sha(self.original)
        replay=self.save(self.plan);self.assertEqual(replay.status_code,200,replay.text);self.assertTrue(replay.json()['idempotent_replay'])
        # A saved pre-FX request/receipt must replay without schema-default conflicts.
        from timeline_tools import digest
        old=copy.deepcopy(self.record);old['request'].pop('transitions',None);old['request'].pop('masks',None)
        old['request_sha256']=digest(old['request'])
        w.write(self.project/'timeline-plans'/old['id']/'plan.json',old)
        w.write(self.project/'timeline-requests'/(old['request']['request_id']+'.json'),{'id':old['id'],'signature':old['request_sha256']})
        replay=self.save(old['request']);self.assertEqual(replay.status_code,200,replay.text);self.assertTrue(replay.json()['idempotent_replay'])
        changed=copy.deepcopy(self.plan);changed['intent']='different intent'
        self.assertEqual(self.save(changed).status_code,409)
        def revision(id):
            return {**copy.deepcopy(self.plan),'request_id':id,'supersedes':self.context()['project']['timeline_head'],
                'project_revision':self.context()['project']['revision']}
        for key,value in [('source_out',99.),('source_in',6.)]:
            invalid=revision('invalid-'+key);invalid['shots'][0][key]=value
            self.assertEqual(self.save(invalid).status_code,422)
        invalid=revision('offbeat');invalid['shots'][0]['source_out']=2.5
        self.assertEqual(self.save(invalid).status_code,422)
        cut=revision('cut');cut['shots'][0]['source_out']=2.;cut['music_grid']=None;cut['audio'][0]['duration']=11.
        response=self.save(cut);self.assertEqual(response.status_code,200,response.text)
        shortened=self.export(response.json()['id'])
        self.assertAlmostEqual(float(probe(shortened)['format']['duration']),11.,delta=.05)
        response=self.save(revision('restore'));self.assertEqual(response.status_code,200,response.text)
        restored=self.export(response.json()['id'])
        self.assertEqual(response.json()['map'],self.record['map'])
        self.assertAlmostEqual(float(probe(restored)['format']['duration']),12.,delta=.05)
        self.assertEqual(sha(self.original),initial_hash)
        for source in self.record['sources']:
            self.assertEqual(sha(self.project/'timeline-plans'/self.record['id']/source['relative_path']),source['sha256'])
        corrupted=copy.deepcopy(response.json());corrupted['map']['duration']=99
        w.write(self.project/'timeline-plans'/corrupted['id']/'plan.json',corrupted)
        self.assertEqual(self.client.post(self.base+'/timeline/export',json={'plan_id':corrupted['id']}).status_code,409)

    def test_independent_audio_start_and_silence(self):
        plan=copy.deepcopy(self.plan);plan.update(request_id='audio-clock',project_revision=self.context()['project']['revision'],
            supersedes=self.record['id'],music_grid=None,titles=[])
        plan['sources']=[r for r in plan['sources'] if r['id'] in ('s0','s1','s4')]
        plan['shots']=[{**plan['shots'][1],'source_out':4.}]
        plan['audio']=[{'source_id':'s4','role':'music','start':1.,'source_in':.5,'duration':2.,'gain':.4,'reason':'Music begins after the silent establishing interval'},
            {'source_id':'s0','role':'ambient','start':2.,'source_in':0.,'duration':1.,'gain':.4,'reason':'Independent original sound bridges footage'}]
        response=self.save(plan);self.assertEqual(response.status_code,200,response.text)
        movie=self.export(response.json()['id']);audio=self.audio(movie)
        rms=lambda a,b:float(np.sqrt(np.mean(audio[int(a*48000):int(b*48000)]**2)))
        self.assertLess(rms(.1,.7),.0001);self.assertGreater(rms(1.2,1.4),.005)
        self.assertGreater(rms(2.2,2.4),rms(1.2,1.4)*1.3)
        self.assertLess(float(np.abs(audio).max()),1.02)

    def test_registered_still_image_without_asr_or_music(self):
        response=self.client.post('/api/agent/v1/tasks',json={'task':'继续原生时间轴剪辑','project':self.pid,
            'input_paths':[str(self.folder/'materials/scene-3.png')],'source_note':'Self-generated landscape illustration','usage_scope':'technical test'})
        self.assertEqual(response.status_code,200,response.text);asset=response.json()['registered'][0]
        plan=copy.deepcopy(self.plan);plan.update(request_id='still',project_revision=self.context()['project']['revision'],
            supersedes=self.record['id'],music_grid=None,audio=[],titles=[])
        plan['sources']=[{'id':'still','kind':'image','asset_id':asset['id'],'sha256':asset['sha256']}]
        plan['shots']=[{'id':'hold','source_id':'still','source_in':0.,'source_out':2.,'role':'reflection','reason':'Hold the meaningful silent view'}]
        response=self.save(plan);self.assertEqual(response.status_code,200,response.text)
        movie=self.export(response.json()['id']);self.assertAlmostEqual(float(probe(movie)['format']['duration']),2.,delta=.05)
        self.assertLess(float(np.abs(self.audio(movie)).max()),.0001)


    def test_publish_binds_real_timeline_and_rejects_wrong_or_changed_export(self):
        eid=self.result['job']['result']['export_id']
        timeline={'kind':'timeline','timeline_plan_id':self.record['id'],'export_id':eid}
        def submit(assets,refs,request_id='publish-timeline',pid=None):
            pid=pid or self.pid
            state=self.client.get(f'/api/agent/v1/projects/{pid}/context').json()
            body={'request_id':request_id,'revision':state['project']['revision'],'context_id':state['context_id'],
                'stage':'publish','input_artifact_ids':[],'standalone_reason':'Only prepare an already rendered simulation.',
                'payload':{'script_artifact_id':None,'title':'Synthetic native export','caption':'Not externally published',
                    'disclosure':'Synthetic graphics and audio for a technical test','assets':assets,
                    'checklist':[{'item':'Bound exported video','state':'checked','evidence':[],'export_ids':refs}]},
                'declared_status':'needs_review','unresolved':['No human listening or rights certification'],
                'supersedes':None,'revision_reason':None}
            return self.client.post(f'/api/agent/v1/projects/{pid}/artifacts',json=body)
        before=self.context()['project']
        wrong={'media_id':before['media'][0]['id'],'export_id':eid}
        for assets,refs in [([wrong],[eid]),([],[eid]),([{**timeline,'timeline_plan_id':'0'*32}],[eid])]:
            response=submit(assets,refs)
            self.assertEqual(response.status_code,422,response.text)
            self.assertEqual(self.context()['project'],before)
        response=submit([timeline],[eid]);self.assertEqual(response.status_code,200,response.text)
        bound=response.json()['computed']['publication_exports'][0]
        self.assertEqual(bound['video_sha256'],sha(self.original))
        self.assertEqual(bound['hash_scope'],'matched_export')
        self.assertEqual(self.context()['project']['verification'],'needs_review')
        other=self.client.post('/api/projects',json={'title':'Other simulation','simulation':True}).json()
        response=submit([timeline],[eid],pid=other['id'])
        self.assertEqual(response.status_code,422,response.text)
        before=self.context()['project'];original=self.original.read_bytes()
        try:
            self.original.write_bytes(original+b'changed bytes')
            response=submit([timeline],[eid],request_id='changed-publish-video')
            self.assertEqual(response.status_code,422,response.text)
            self.assertTrue(any(e['code']=='changed_export' for e in response.json()['errors']))
            self.assertEqual(self.context()['project'],before)
        finally:self.original.write_bytes(original)


if __name__=='__main__':unittest.main()
