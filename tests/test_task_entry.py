"""Task selection, continuation, ambiguity and preservation of existing work."""
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
import app as w
from task_api import infer_intent


class TaskEntryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        self.patch=patch.object(w,'DATA',self.path/'projects');self.patch.start()
        w.DATA.mkdir();self.client=TestClient(w.app,base_url='http://localhost')

    def tearDown(self):self.client.close();self.patch.stop();self.temp.cleanup()

    def task(self,text,**kw):
        return self.client.post('/api/agent/v1/tasks',json={'task':text,'simulation':True,**kw})

    def test_focus_negation_and_media_routing(self):
        self.assertEqual(infer_intent('不需要剪辑，只写脚本'),'script')
        self.assertEqual(infer_intent('不要配图，不要字幕，只写脚本'),'script')
        self.assertEqual(infer_intent('继续加一个羽化蒙版和转场'),'edit')
        self.assertEqual(infer_intent('不要蒙版，不做转场，只写脚本'),'script')
        self.assertEqual(infer_intent('把文章标黄后做段落抽离，再加移动聚光灯'),'edit')
        self.assertEqual(infer_intent('不要动效，不要特效，只写脚本'),'script')
        self.assertEqual(infer_intent('不要复盘，帮我选题'),'topics')
        self.assertEqual(infer_intent('整理这个视频',True),'edit')
        r=self.task('只写一条脚本').json()
        self.assertEqual(r['start_at'],'script');self.assertTrue(r['standalone_reason_required'])
        self.assertEqual(r['context']['heads'],{})
        self.assertEqual(len(r['context']['tasks']),1)

    def test_resume_session_and_explicit_project_across_sessions(self):
        a=self.task('诊断一个新项目',title='修理店教学',session_key='chat-a').json()
        b=self.task('继续做选题',session_key='chat-a').json()
        self.assertEqual(a['project_id'],b['project_id']);self.assertFalse(b['project_created'])
        c=self.task('继续写脚本',project='修理店教学',session_key='chat-b').json()
        self.assertEqual(a['project_id'],c['project_id'])
        self.assertEqual(c['start_at'],'script')

    def test_ambiguity_requires_selection_and_no_silent_project(self):
        for i in range(2):self.task('选题',title=f'候选账号{i}',new_project=True,session_key=f'c{i}')
        response=self.task('继续',session_key='unknown')
        self.assertEqual(response.status_code,409)
        self.assertEqual(response.json()['detail']['code'],'ambiguous_project')
        self.assertEqual(len(w.projects()),2)

    def test_source_dedup_and_task_retry(self):
        p=self.path/'输入 空格.txt';p.write_text('模拟素材，无后台数据。',encoding='utf-8')
        rid=uuid.uuid4().hex
        body={'task':'写脚本','input_paths':[str(p)],'request_id':rid}
        a=self.task(**{'text':body.pop('task')},**body).json()
        b=self.task('写脚本',input_paths=[str(p)],request_id=rid).json()
        self.assertTrue(b['idempotent_replay']);self.assertEqual(a['project_id'],b['project_id'])
        c=self.task('继续修改脚本',input_paths=[str(p)]).json()
        self.assertEqual(a['project_id'],c['project_id'])
        self.assertEqual(len(c['context']['sources']),1)
        bad=self.task('换个请求',input_paths=[str(p)],request_id=rid)
        self.assertEqual(bad.status_code,409)

    def test_invalid_input_has_no_partial_project(self):
        self.assertEqual(self.task('写脚本',input_paths=[str(self.path/'missing.txt')]).status_code,422)
        self.assertEqual(w.projects(),[])

    def test_full_workflow_resumes_first_missing_and_stale_stage(self):
        a=self.task('完整流程').json();pid=a['project_id'];path=w.folder(pid)
        p=w.read(path/'project.json');p['agent_heads']={'diagnose':'D'};w.write(path/'project.json',p)
        w.write(path/'agent/artifacts/D.json',{'id':'D','stage':'diagnose','input_artifact_ids':[]})
        b=self.task('继续完整流程').json();self.assertEqual(b['start_at'],'topics')
        p=w.read(path/'project.json');p['agent_heads'].update(topics='T',diagnose='D2');w.write(path/'project.json',p)
        w.write(path/'agent/artifacts/T.json',{'id':'T','stage':'topics','input_artifact_ids':['D']})
        w.write(path/'agent/artifacts/D2.json',{'id':'D2','stage':'diagnose','input_artifact_ids':[]})
        c=self.task('继续完整流程').json();self.assertEqual(c['start_at'],'topics')
        self.assertTrue(next(x for x in c['context']['artifacts'] if x['id']=='T')['dependency_stale'])


if __name__=='__main__':unittest.main()
