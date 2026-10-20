"""Controlled unit/API cases; generated ASR/FFmpeg execution is a separate check."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
import app as w


class SpeechEditTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='speech-edits-')
        self.patch=patch.object(w,'DATA',Path(self.temp.name)); self.patch.start()
        self.client=TestClient(w.app,base_url='http://localhost')
        self.project=self.client.post('/api/projects',json={'title':'明确标注的隔离测试','simulation':True}).json()
        self.path=Path(self.temp.name)/self.project['id']
        p=w.read(self.path/'project.json')
        p['media']=[{'id':'fixture','relative_path':'fixture.mp4','has_video':True,'sha256':'a'*64}]
        w.write(self.path/'project.json',p)
        self.out=self.path/'media/fixture/asr/run1'
        self.review={'duration':6,'source_sha256':'a'*64,'words':[
            {'id':0,'text':'口误','start':.2,'end':.7},
            {'id':1,'text':'重复','start':.8,'end':1.2},
            {'id':2,'text':'不是','start':2.,'end':2.5},
            {'id':3,'text':'保证','start':2.6,'end':3.2}],
            'candidates':[{'id':'pause','start':1.4,'end':1.7}]}
        w.write(self.out/'review.json',self.review)
        w.write(self.out/'transcript.original.json',self.review)
        w.write(self.path/'media/fixture/current-asr.json',{'run_id':'run1'})
        self.url='/api/projects/'+p['id']+'/media/fixture'
        self.cut={'id':'repeat-1','kind':'repetition','word_ids':[0,1],'reason':'明确标注的测试重复起句'}

    def tearDown(self):
        self.client.close();self.patch.stop();self.temp.cleanup()

    def submit(self,revision=0,**changes):
        data={'revision':revision,'asr_run':'run1','source_sha256':'a'*64,'speech_cuts':[self.cut]}
        data.update(changes)
        return self.client.put(self.url+'/review',json=data)

    def test_display_correction_keeps_english_token_separator(self):
        self.review['words'][0]['text']='A checklist.'
        self.review['words'][1]['text']=' generated '
        w.write(self.out/'review.json',self.review)
        response=self.submit(speech_cuts=[],corrections={'1':'Generated'})
        self.assertEqual(response.status_code,200,response.text)
        review=self.client.get(self.url+'/review').json()
        self.assertIn('checklist. Generated ',review['text'])
        self.assertEqual(w.read(self.out/'transcript.original.json')['words'][1]['text'],'重复')

    def test_initial_review_exposes_revision_for_discovered_write_contract(self):
        original=w.read(self.out/'transcript.original.json')
        current=self.client.get(self.url+'/review').json()
        self.assertIn('revision',current)
        self.assertEqual(current['revision'],0)
        saved=self.submit(revision=current['revision'],speech_cuts=[],selected_ids=[])
        self.assertEqual(saved.status_code,200,saved.text)
        updated=self.client.get(self.url+'/review').json()
        self.assertEqual(updated['revision'],1)
        self.assertEqual(w.read(self.out/'transcript.original.json'),original)

    def test_caption_groups_preserve_audio_and_require_complete_retained_order(self):
        automatic=self.submit(speech_cuts=[],selected_ids=[])
        self.assertEqual(automatic.status_code,200,automatic.text)
        groups=[[0,1],[2,3]]
        grouped=self.submit(revision=1,speech_cuts=[],selected_ids=[],caption_groups=groups)
        self.assertEqual(grouped.status_code,200,grouped.text)
        self.assertEqual(grouped.json()['plan'],automatic.json()['plan'])
        self.assertEqual(grouped.json()['review']['caption_groups'],groups)
        for invalid in [[[0,1],[2]],[[0,1],[1,2,3]],[[0,1],[3,2]],[[0,1],[],[2,3]]]:
            self.assertEqual(self.submit(revision=2,speech_cuts=[],caption_groups=invalid).status_code,422)
        # Deleting words cannot silently reuse a stale grouping.
        self.assertEqual(self.submit(revision=2).status_code,422)
        revised=self.submit(revision=2,caption_groups=[[2,3]])
        self.assertEqual(revised.status_code,200,revised.text)
        self.assertEqual(revised.json()['plan']['deleted_word_ids'],[0,1])
        reset=self.submit(revision=3,speech_cuts=[],caption_groups=[])
        self.assertEqual(reset.status_code,200,reset.text)
        self.assertEqual(reset.json()['review']['caption_groups'],[])
        self.assertEqual(w.read(self.out/'transcript.original.json'),self.review)

    def test_spoken_cut_omission_and_restore_are_independent_from_pause(self):
        response=self.submit(selected_ids=['pause'])
        self.assertEqual(response.status_code,200,response.text)
        plan=response.json()['plan']
        self.assertEqual(plan['deleted_word_ids'],[0,1])
        self.assertAlmostEqual(plan['output_duration'],4.7)
        self.assertEqual(plan['decisions'][1]['review_text'],'口误重复')
        # A pause-only caller cannot silently restore spoken words by omission.
        pause=self.client.put(self.url+'/review',json={'revision':1,'selected_ids':[]})
        self.assertEqual(pause.status_code,200,pause.text)
        self.assertEqual(pause.json()['plan']['deleted_word_ids'],[0,1])
        restored=self.submit(revision=2,speech_cuts=[])
        self.assertEqual(restored.status_code,200,restored.text)
        self.assertEqual(restored.json()['plan']['keeps'],[{'start':0.,'end':6.,'outputOffset':0.}])
        self.assertEqual(w.read(self.out/'transcript.original.json'),self.review)
        self.assertEqual(len(list((self.out/'versions').glob('*.json'))),3)

    def test_reject_partial_group_or_unselected_qualifier_and_keep_failures(self):
        for extra in [{'start':.3,'end':1.2},{'start':.2,'end':2.2}]:
            response=self.submit(speech_cuts=[{**self.cut,**extra}])
            self.assertEqual(response.status_code,422,response.text)
        self.assertEqual(self.submit(speech_cuts=[{**self.cut,'word_ids':[0,3]}]).status_code,422)
        self.assertEqual(self.submit(speech_cuts=[{**self.cut,'word_ids':[99]}]).status_code,422)
        self.assertEqual(self.submit(speech_cuts=[{**self.cut,'word_ids':[True]}]).status_code,422)
        self.assertEqual(w.read(self.out/'review.json'),self.review)
        attempts=[w.read(p) for p in (self.path/'media/fixture/review-attempts').glob('*.json')]
        self.assertEqual(len(attempts),5)
        self.assertTrue(all(not a['accepted'] for a in attempts))

    def test_run_source_and_revision_bindings_reject_stale_edit_and_export(self):
        self.assertEqual(self.submit(asr_run='old-run').status_code,409)
        self.assertEqual(self.submit(source_sha256='b'*64).status_code,409)
        self.assertEqual(self.submit(revision=9).status_code,409)
        self.assertEqual(self.client.put(self.url+'/review',json={'revision':0,'speech_cuts':[]}).status_code,422)
        self.assertEqual(self.client.post(self.url+'/export',json={
            'revision':0,'asr_run':'old-run','source_sha256':'a'*64}).status_code,409)
        # Same revision number on a fresh ASR run must not accept old groups.
        w.write(self.path/'media/fixture/asr/run2/review.json',self.review)
        w.write(self.path/'media/fixture/current-asr.json',{'run_id':'run2'})
        self.assertEqual(self.submit().status_code,409)

    def test_schema_discovery_and_correction_alignment(self):
        for name in ['media-review','media-export']:
            response=self.client.get('/api/agent/v1/schemas/'+name)
            self.assertEqual(response.status_code,200)
            self.assertIn('asr_run',response.json()['properties'])
        saved=self.submit(corrections={'2':'不构成'},selected_ids=[])
        self.assertEqual(saved.status_code,200,saved.text)
        words=saved.json()['review']['words']
        self.assertEqual((words[2]['start'],words[2]['end']),(2.,2.5))
        self.assertEqual(words[2]['text'],'不构成')
        self.assertEqual(saved.json()['plan']['deleted_word_ids'],[0,1])
        self.assertEqual(self.client.get(self.url+'/review').json()['asr_run'],'run1')


if __name__=='__main__':unittest.main(verbosity=2)
