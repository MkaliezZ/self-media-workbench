"""State/revision and destructive-edit boundaries, isolated from user projects."""
import json
import hashlib
import sys
import wave
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
import app as workbench
from local_asr import transcribe
from fixture_tools import fixture_path


class LocalApiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='workbench-api-')
        self.data=Path(self.temp.name)
        self.patch=patch.object(workbench,'DATA',self.data)
        self.patch.start()
        self.client=TestClient(workbench.app,base_url='http://localhost')
        self.project=self.client.post('/api/projects',json={'title':'隔离技术测试','simulation':True}).json()
        self.url='/api/projects/'+self.project['id']

    def tearDown(self):
        self.client.close();self.patch.stop();self.temp.cleanup()

    def test_document_versions_and_conflicts(self):
        a=self.client.put(self.url+'/documents/script',json={'content':'版本一','revision':1})
        self.assertEqual(a.status_code,200)
        b=self.client.put(self.url+'/documents/script',json={'content':'过期修改','revision':1})
        self.assertEqual(b.status_code,409)
        p=self.client.get(self.url).json()
        self.assertEqual(p['documents']['script']['content'],'版本一')
        self.assertEqual(p['verification'],'needs_review')
        self.assertTrue((self.data/p['id']/'versions/000001.json').exists())

    def test_origins_and_empty_title(self):
        response=self.client.post('/api/projects',json={'title':'foreign'},headers={'Origin':'https://example.com'})
        self.assertEqual(response.status_code,403)
        self.assertEqual(self.client.post('/api/projects',json={'title':' '}).status_code,422)

    def test_media_declaration_versions_and_task_pack(self):
        imported = self.client.post(self.url+'/media', json={
            'path':str(fixture_path())})
        self.assertEqual(imported.status_code, 200)
        item = imported.json()['media']
        self.assertEqual(item['media_nature'], 'unknown')
        route = self.url+'/media/'+item['id']+'/metadata'
        update = {'revision':2, 'media_nature':'generated',
                  'source_note':'SAPI合成音频与纯色视频，非真人拍摄',
                  'usage_scope':'只用于本机技术验收，未真实发布'}
        response = self.client.put(route, json=update)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['media']['source_note'], update['source_note'])
        self.assertEqual(self.client.put(route, json=update).status_code, 409)
        folder = self.data/self.project['id']
        prior = workbench.read(folder/'versions/000002.json')
        self.assertEqual(prior['media'][0]['media_nature'], 'unknown')
        with (folder/item['relative_path']).open('rb') as stream:
            self.assertEqual(hashlib.file_digest(stream,'sha256').hexdigest(),item['sha256'])
        task = self.client.get(self.url+'/agent-pack').text
        self.assertIn('"media_nature": "generated"',task)
        self.assertIn(update['usage_scope'],task)
        self.assertIn('未独立核验',task)
        invalid = self.client.put(route,json={'revision':3,'media_nature':'verified_real'})
        self.assertEqual(invalid.status_code,422)
        self.assertEqual(self.client.put(route,json=[]).status_code,422)

    def test_structured_document_keeps_fields_and_original_version(self):
        first=self.client.put(self.url+'/documents/topics',json={'content':'原始未结构化笔记','revision':1})
        self.assertEqual(first.status_code,200)
        structured={'schema_version':1,'fields':{'selected':'纸样只记录位置','limits':'没有尺寸测量数据'},
                    'rows':[],'notes':'原始未结构化笔记'}
        saved=self.client.put(self.url+'/documents/topics',json={'content':'选题记录与边界','revision':2,'structured':structured})
        self.assertEqual(saved.status_code,200)
        loaded=self.client.get(self.url).json()
        self.assertEqual(loaded['documents']['topics']['structured'],structured)
        self.assertEqual(loaded['verification'],'needs_review')
        prior=workbench.read(self.data/loaded['id']/'versions/000002.json')
        self.assertEqual(prior['documents']['topics']['content'],'原始未结构化笔记')
        invalid=self.client.put(self.url+'/documents/topics',json={'content':'不可存','revision':3,'structured':['bad']})
        self.assertEqual(invalid.status_code,422)

    def test_review_correction_does_not_change_alignment(self):
        path=self.data/self.project['id']
        p=workbench.read(path/'project.json')
        p['media']=[{'id':'fixture','relative_path':'fixture.mp4'}]
        workbench.write(path/'project.json',p)
        workbench.write(path/'media/fixture/current-asr.json',{'run_id':'test'})
        review={'duration':3,'words':[{'id':0,'text':'限定条件','start':.2,'end':1.1}],
                'candidates':[{'id':'safe','start':1.5,'end':2.5}]}
        out=path/'media/fixture/asr/test'
        workbench.write(out/'review.json',review)
        workbench.write(out/'transcript.original.json',review)
        route=self.url+'/media/fixture/review'
        response=self.client.put(route,json={'revision':0,'corrections':{'0':'修订的限定条件'},'selected_ids':['safe']})
        self.assertEqual(response.status_code,200)
        saved=response.json()['review']
        self.assertEqual(saved['words'][0]['start'],.2)
        self.assertEqual(saved['words'][0]['end'],1.1)
        self.assertEqual(workbench.read(out/'transcript.original.json'),review)
        self.assertEqual(self.client.put(route,json={'revision':0,'selected_ids':[]}).status_code,409)
        self.assertEqual(self.client.put(route,json={'revision':1,'corrections':{'0':''},'selected_ids':[]}).status_code,422)
        restored=self.client.put(route,json={'revision':1,'selected_ids':[]}).json()
        self.assertEqual(restored['plan']['output_duration'],3)

    def test_original_asr_cannot_be_overwritten(self):
        out=self.data/'existing';out.mkdir()
        (out/'transcript.original.json').write_text('{}',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'已有原始转录'):
            transcribe(ROOT/'evidence/asr-smoke/source.mp4',out)

    def test_corrupt_import_has_no_orphan_or_state_change(self):
        project_dir=self.data/self.project['id']
        before=self.client.get(self.url).json()
        for suffix in ('.mp4','.wav'):
            source=self.data/('truncated'+suffix)
            source.write_bytes(b'not a valid audio/video stream')
            before_hash=hashlib.sha256(source.read_bytes()).hexdigest()
            response=self.client.post(self.url+'/media',json={'path':str(source)})
            self.assertEqual(response.status_code,422,response.text)
            self.assertEqual(self.client.get(self.url).json(),before)
            self.assertEqual(list((project_dir/'media').iterdir()),[])
            self.assertEqual(list((project_dir/'jobs').glob('*.json')),[])
            self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),before_hash)
        wav_source=self.data/'header-valid-but-truncated.wav'
        with wave.open(str(wav_source),'wb') as stream:
            stream.setparams((1,2,16000,0,'NONE','not compressed'))
            stream.writeframes(b'\x00\x01'*16000)
        original_wav=wav_source.read_bytes();wav_source.write_bytes(original_wav[:4096])
        response=self.client.post(self.url+'/media',json={'path':str(wav_source)})
        self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(self.client.get(self.url).json(),before)
        self.assertEqual(list((project_dir/'media').iterdir()),[])
        self.assertEqual(wav_source.read_bytes(),original_wav[:4096])
        response=self.client.post(self.url+'/media',json={'path':str(fixture_path())})
        self.assertEqual(response.status_code,200,response.text)
        self.assertGreater(response.json()['media']['video_duration'],0)


if __name__=='__main__':
    unittest.main(verbosity=2)
