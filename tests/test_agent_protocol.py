"""Agent handoffs, failed submissions, simulation and state drift boundaries."""
import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
import app as w

P='/api/agent/v1'


class AgentTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='agent-protocol-')
        self.data=Path(self.temp.name)
        self.patch=patch.object(w,'DATA',self.data);self.patch.start()
        self.client=TestClient(w.app,base_url='http://localhost')
        self.project=self.client.post('/api/projects',json={'title':'Agent协议隔离测试','simulation':True}).json()
        self.url=P+'/projects/'+self.project['id']
        result=self.client.post(self.url+'/sources',json={
            'revision':1,'label':'原始记录','nature':'simulation',
            'origin':'test fixture','content':'模拟：只展示文件哈希；没有真实发布数据。'}).json()
        self.sid=result['source']['id']

    def tearDown(self):
        if os.environ.get('AGENT_TEST_EVIDENCE'):
            destination=Path(os.environ['AGENT_TEST_EVIDENCE'])/self.id()
            shutil.copytree(self.data,destination)
        self.client.close();self.patch.stop();self.temp.cleanup()

    def context(self):return self.client.get(self.url+'/context').json()

    def claim(self):
        return {'id':'C1','text':'这次只展示文件一致性，没有发布数据。','kind':'observation',
                'evidence':[{'source_id':self.sid,'quote':'只展示文件哈希；没有真实发布数据'}],
                'limitation':'模拟测试不证明运营效果'}

    def payload(self,stage,upstream=None):
        claim=self.claim()
        if stage=='diagnose':
            return {'objective':'帮助整理素材','audience':'初次整理文件者','account_scope':'模拟内容审阅，无账号运营数据',
                    'claims':[claim],'priority_action':'拍一次内容相同但名字不同的文件对比'}
        if stage=='topics':
            return {'claims':[claim],'candidates':[{'id':'T1','question':'名字不同就不是重复文件吗？',
                    'angle':'哈希一致性演示','objective':'解释文件一致性','claim_ids':['C1']}],
                    'selected_id':'T1','selection_reason':'有可复现的本地材料'}
        if stage=='script':
            return {'topic_artifact_id':upstream,'topic_id':'T1','claims':[claim],
                    'segments':[{'id':'S1','start':0.0,'end':8.0,'spoken':'文件名不同，也可能是同一份内容。这里只做演示。',
                                 'visual':'显示文件列表和实际哈希','subtitle':'演示数据','claim_ids':['C1']}],
                    'cta':'先备份再检查，不要直接删除。','production_limits':['待实际录屏']}
        if stage=='publish':
            return {'script_artifact_id':upstream,'title':'名字不一样，内容就不同吗','caption':'模拟技术演练，未真实发布',
                    'disclosure':'本地测试素材','assets':[],
                    'checklist':[{'item':'已真实发布','state':'missing','evidence':[]}]}
        return {'publish_artifact_id':upstream,'observation_type':'planned','claims':[claim],
                'metrics':[{'name':'收藏/播放','numerator':None,'denominator':None,'value':None,'unit':'ratio',
                            'window':'发布后24小时（计划）','collected_at':None,'evidence':[]}],
                'hypotheses':['演示前置可能减少理解成本，尚未验证'],
                'next_experiment':{'variable':'开头','change':'先显示对比结果','metric':'收藏/播放',
                                   'stop_rule':'未拿到同口径快照前不判断胜负'}}

    def body(self,stage,upstream=None):
        state=self.context()
        return {'request_id':uuid.uuid4().hex,'revision':state['project']['revision'],
                'context_id':state['context_id'],'stage':stage,
                'input_artifact_ids':[upstream] if upstream else [],
                'standalone_reason':None,'payload':self.payload(stage,upstream),
                'declared_status':'needs_review','unresolved':['尚无真实发布'],
                'supersedes':None,'revision_reason':None}

    def submit(self,body):return self.client.post(self.url+'/artifacts',json=body)

    def chain(self):
        ids=[]
        for stage in ('diagnose','topics','script','publish','review'):
            response=self.submit(self.body(stage,ids[-1] if ids else None))
            self.assertEqual(response.status_code,200,response.text)
            ids.append(response.json()['artifact']['id'])
        return ids

    def test_complete_handoff_and_no_automatic_verification(self):
        self.chain()
        state=self.context()
        self.assertEqual(len(state['heads']),5)
        self.assertTrue(all(a['scope']=='simulation' for a in state['artifacts']))
        self.assertTrue(all(not a['dependency_stale'] for a in state['artifacts']))
        self.assertEqual(state['project']['verification'],'needs_review')
        review=next(a for a in state['artifacts'] if a['stage']=='review')
        frozen=w.read(Path(review['context_snapshot_path']))
        self.assertEqual(frozen['context_id'],review['context_id'])
        self.assertNotIn('review',frozen['heads'])
        self.assertIn('bundle_sha256',frozen['skill'])
        self.assertTrue(review['validation']['computed']['metrics'][0]['missing'])

    def test_complete_continuation_is_noop_but_explicit_new_topic_runs(self):
        self.chain();before=self.context()
        result=self.client.post(P+'/tasks',json={'task':'继续这个项目，告诉我现在到哪一步、下一步做什么。',
            'project':self.project['id'],'session_key':'complete-case'}).json()
        self.assertEqual(result['workflow_status'],'complete')
        self.assertIsNone(result['start_at']);self.assertEqual(result['plan'],[])
        self.assertEqual(self.context()['heads'],before['heads'])
        self.assertEqual(self.context()['project']['revision'],before['project']['revision'])
        explicit=self.client.post(P+'/tasks',json={'task':'继续做下一轮选题','project':self.project['id']}).json()
        self.assertEqual(explicit['start_at'],'topics')

    def test_missing_metrics_need_no_fake_time_or_evidence_but_numeric_ones_do(self):
        ids=self.chain();body=self.body('review',ids[3])
        body.update(supersedes=ids[4],revision_reason='记录未取得的指标，不虚构时间或出处')
        body['payload']['observation_type']='simulated'
        accepted=self.submit(body)
        self.assertEqual(accepted.status_code,200,accepted.text)
        head=accepted.json()['artifact']['id']
        for kind in ('planned','simulated'):
            body=self.body('review',ids[3]);body.update(supersedes=head,revision_reason='检查数值仍须证据')
            body['payload']['observation_type']=kind;body['payload']['metrics'][0]['value']=.12
            rejected=self.submit(body)
            self.assertIn('missing_metric_evidence',[e['code'] for e in rejected.json()['errors']])

    def test_failure_preserved_repair_and_idempotent_retry(self):
        invalid=self.body('diagnose');invalid['payload']['claims'][0]['evidence'][0]['quote']='不存在的原文'
        rejected=self.submit(invalid)
        self.assertEqual(rejected.status_code,422)
        self.assertEqual(self.context()['project']['revision'],2)
        valid=self.body('diagnose');accepted=self.submit(valid).json()
        retry=self.submit(valid).json()
        self.assertTrue(retry['idempotent_replay'])
        self.assertEqual(accepted['artifact']['id'],retry['artifact']['id'])
        changed=json.loads(json.dumps(valid));changed['payload']['priority_action']='改变内容'
        self.assertEqual(self.submit(changed).status_code,409)
        attempts=self.client.get(self.url+'/attempts').json()
        self.assertEqual(len(attempts),3)
        self.assertTrue(any(a['request']==invalid for a in attempts))

    def test_invalid_root_does_not_poison_later_requests(self):
        self.assertEqual(self.submit([]).status_code,422)
        self.assertEqual(self.submit(self.body('diagnose')).status_code,200)

    def test_context_change_without_project_revision_and_source_integrity(self):
        body=self.body('diagnose')
        source=self.context()['sources'][0]
        (self.data/self.project['id']/source['relative_path']).write_text('被外部改写',encoding='utf-8')
        response=self.submit(body)
        self.assertEqual(response.status_code,409)
        self.assertIn('source_integrity',[e['code'] for e in response.json()['errors']])
        self.assertFalse(self.context()['sources'][0]['integrity'])

    def test_recursive_dependency_staleness(self):
        ids=self.chain()
        new=self.body('diagnose');new.update(supersedes=ids[0],revision_reason='收窄材料审阅范围')
        self.assertEqual(self.submit(new).status_code,200)
        state=self.context()
        self.assertTrue(next(a for a in state['artifacts'] if a['id']==ids[2])['dependency_stale'])
        response=self.submit(self.body('script',ids[1]))
        self.assertEqual(response.status_code,422)
        self.assertIn('stale_dependency',[e['code'] for e in response.json()['errors']])

    def test_topic_and_timeline_binding(self):
        d=self.submit(self.body('diagnose')).json()['artifact']['id']
        t=self.submit(self.body('topics',d)).json()['artifact']['id']
        body=self.body('script',t);body['payload']['topic_id']='other'
        body['payload']['segments'][0]['end']=0.0
        self.assertEqual(self.submit(body).status_code,422)
        body=self.body('script',t);body['payload']['segments'][0]['end']=body['payload']['segments'][0]['start']+2
        body['payload']['segments'].append({**body['payload']['segments'][0],'id':'S2','start':1.0,'end':3.0})
        self.assertIn('invalid_timeline',[e['code'] for e in self.submit(body).json()['errors']])

    def test_no_fake_real_publication_and_metric_math(self):
        ids=self.chain()
        body=self.body('review',ids[3]);body.update(supersedes=ids[4],revision_reason='测试边界')
        body['payload']['observation_type']='published'
        m=body['payload']['metrics'][0]
        m.update(numerator=10.0,denominator=100.0,value=90.0,collected_at='2026-10-20T10:00:00Z',
                 evidence=[{'source_id':self.sid,'quote':'没有真实发布数据'}])
        response=self.submit(body)
        codes=[e['code'] for e in response.json()['errors']]
        self.assertIn('metric_mismatch',codes);self.assertIn('simulation_as_publication',codes)
        m.update(denominator=0.0,value=None)
        self.assertIn('zero_denominator',[e['code'] for e in self.submit(body).json()['errors']])

    def test_schemas_and_missing_handoff_are_discoverable(self):
        self.assertEqual(self.client.get(P+'/capabilities').json()['primary_client'],'ai_agent')
        for name in ('submission','source','diagnose','topics','script','publish','review','media-import','media-transcribe'):
            self.assertEqual(self.client.get(P+'/schemas/'+name).status_code,200)
        media_schema=self.client.get(P+'/schemas/media-import').json()
        self.assertEqual(media_schema['required'],['path'])
        self.assertIn('media_nature',media_schema['properties'])
        self.assertEqual(self.client.get(P+'/schemas/media-transcribe').json()['type'],'null')
        import_route=self.client.get('/openapi.json').json()['paths']['/api/projects/{pid}/media']['post']
        self.assertIn('requestBody',import_route)
        self.assertEqual(self.client.post('/api/projects/'+self.project['id']+'/media',json={'source':'not-the-discovered-field'}).status_code,422)
        self.assertEqual(self.submit(self.body('topics')).status_code,422)
        body=self.body('topics');body['standalone_reason']='仅选题，本任务没有账号诊断'
        self.assertEqual(self.submit(body).status_code,200)


if __name__=='__main__':unittest.main(verbosity=2)
