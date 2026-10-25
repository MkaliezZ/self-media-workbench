"""Actual industry recipe compilation and FFmpeg output; synthetic teaching fixtures."""
import copy
import json
import subprocess
import unittest
import test_visual_editing as fixtures
from editing_templates import catalog,digest,CompileTemplate,compile_plan


class EditingTemplateTests(unittest.TestCase):
    setUp=fixtures.VisualEditingTests.setUp
    tearDown=fixtures.VisualEditingTests.tearDown
    context=fixtures.VisualEditingTests.context
    export=fixtures.VisualEditingTests.export
    save=fixtures.VisualEditingTests.save

    def request(self,t):
        # Hand-aligned synthetic narration: no measured recognition or actual business evidence.
        review={**self.review,'words':[
            {'id':0,'text':'先看问题','start':.2,'end':.7},
            {'id':1,'text':'看这个细节','start':1.2,'end':1.7},
            {'id':2,'text':'还要看条件','start':2.3,'end':3.3}],
            'caption_groups':[[0],[1],[2]],'candidates':[]}
        fixtures.w.write(self.out/'review.json',review)
        image={k:v for k,v in self.body['images'][0].items() if k in ('path','sha256','nature','source_note','usage_scope','highlight')}
        beats=[{'role':role['id'],'word_ids':[i],'reason':role['purpose'],
            'material_note':'Self-generated colour footage/diagram; synthetic test, not actual industry evidence',
            'visual_mode':'image' if i==1 else 'source','image':image if i==1 else None}
            for i,role in enumerate(t['roles'])]
        return {'request_id':'template-'+t['id'],'project_revision':self.context()['project']['revision'],
            'review_revision':0,'asr_run':'run1','source_sha256':self.media['sha256'],
            'template_id':t['id'],'template_version':t['version'],
            'selection_reason':'Exercise recipe contract on explicitly synthetic source',
            'frame_inspection_note':'Generated blue frame: no people or important UI; safe area inspected',
            'protected_regions':[],'beats':beats}

    def compile(self,body):
        return self.client.post(self.url+'/visual-template/compile',json=body)

    def test_all_catalog_recipes_real_render_and_frozen_definitions(self):
        placements=[];colour=set()
        for t in catalog():
            with self.subTest(industry=t['id']):
                body=self.request(t);before=self.context()['project']['revision']
                response=self.compile(body);self.assertEqual(response.status_code,200,response.text)
                draft=response.json();self.assertEqual(draft['status'],'draft_not_saved')
                self.assertEqual(self.context()['project']['revision'],before)
                plan=draft['visual_plan'];saved=self.save(plan)
                self.assertEqual(saved.status_code,200,saved.text)
                record=saved.json();self.assertEqual(digest(record['template_definition']),t['definition_sha256'])
                dest=self.export(record)
                timeline=fixtures.w.read(dest/'visual-timeline.json')
                placements.append(timeline['events'][0]['placed_rect'])
                colour.add(record['request']['captions']['emphasis_colour'])
                expected=[r['id'] for r in t['roles']]
                self.assertEqual([b['role'] for b in record['request']['template']['beats']],expected)
                self.assertEqual([c['text'] for c in timeline['captions']],['先看问题','看这个细节','还要看条件'])
                self.assertEqual(len(timeline['captions']),3)
                self.assertEqual(self.context()['visual_plans'][-1]['stale'],False)
        self.assertGreaterEqual(len({json.dumps(p,sort_keys=True) for p in placements}),5)
        self.assertGreaterEqual(len(colour),7)

    def test_reject_missing_roles_assets_coverage_occlusion_and_modified_compilation(self):
        t=catalog()[1];body=self.request(t)
        cases=[]
        missing=copy.deepcopy(body);missing['beats'].pop();cases.append(missing)
        order=copy.deepcopy(body);order['beats'].reverse();cases.append(order)
        image=copy.deepcopy(body);image['beats'][1]['image']=None;cases.append(image)
        omitted=copy.deepcopy(body);omitted['beats'][2]['word_ids']=[1];cases.append(omitted)
        covered=copy.deepcopy(body);covered['protected_regions']=[{'x':0.,'y':0.,'width':1.,'height':1.}];cases.append(covered)
        notes=copy.deepcopy(body);notes['beats'][1]['material_note']=' ';cases.append(notes)
        old=copy.deepcopy(body);old['template_version']='old';cases.append(old)
        for invalid in cases:
            response=self.compile(invalid);self.assertEqual(response.status_code,422,response.text)
        stale={**body,'project_revision':999}
        self.assertEqual(self.compile(stale).status_code,409)
        good=self.compile(body);self.assertEqual(good.status_code,200,good.text)
        plan=good.json()['visual_plan'];plan['images'][0]['slot']['x']=0.
        response=self.save(plan);self.assertEqual(response.status_code,422,response.text)
        attempts=list((self.path/'media'/self.mid/'template-attempts').glob('*.json'))
        self.assertEqual(len(attempts),9)
        self.assertFalse(self.context()['visual_plans'])

    def test_portrait_actual_video_and_safe_slot_override(self):
        source=self.path/self.media['relative_path'];portrait=self.data/'竖屏样片.mp4'
        subprocess.run(['ffmpeg','-v','error','-i',str(source),'-vf','scale=240:320,setsar=1','-c:v','libx264',
            '-pix_fmt','yuv420p','-c:a','copy',str(portrait)],check=True,capture_output=True)
        # Isolated synthetic fixture replacement; this is not a user-project edit operation.
        source.write_bytes(portrait.read_bytes());self.media['sha256']=fixtures.sha(source)
        project=fixtures.w.read(self.path/'project.json');project['media'][0]['sha256']=self.media['sha256']
        fixtures.w.write(self.path/'project.json',project);self.review['source_sha256']=self.media['sha256']
        t=catalog()[0];body=self.request(t)
        # Known protected lower-right region; Agent chooses a top-left override.
        body['protected_regions']=[{'x':.6,'y':.6,'width':.4,'height':.4}]
        body['beats'][1]['slot_override']={'x':.05,'y':.05,'width':.4,'height':.3}
        response=self.compile(body);self.assertEqual(response.status_code,200,response.text)
        saved=self.save(response.json()['visual_plan']);self.assertEqual(saved.status_code,200,saved.text)
        dest=self.export(saved.json())
        self.assertEqual(saved.json()['video_width'],240);self.assertEqual(saved.json()['video_height'],320)
        timeline=fixtures.w.read(dest/'visual-timeline.json');rect=timeline['events'][0]['placed_rect']
        self.assertLess(rect['x']+rect['width'],120);self.assertLess(rect['y']+rect['height'],130)

    def test_discovery_routing_and_stale_restore(self):
        response=self.client.get('/api/visual/templates');self.assertEqual(len(response.json()['templates']),len(catalog()))
        caps=self.client.get('/api/agent/v1/capabilities').json()
        self.assertIn('editing-template',caps['schemas'])
        task=self.client.post('/api/agent/v1/tasks',json={'task':'按餐饮探店行业模板剪辑','project':self.pid})
        self.assertEqual(task.status_code,200,task.text)
        self.assertEqual(task.json()['editing_templates']['candidates'][0]['id'],'food')
        body=self.request(catalog()[0]);compiled=self.compile(body)
        self.assertEqual(compiled.status_code,200,compiled.text)
        saved=self.save(compiled.json()['visual_plan']);self.assertEqual(saved.status_code,200,saved.text)
        change=self.client.put(self.url+'/review',json={'revision':0,'asr_run':'run1',
            'source_sha256':self.media['sha256'],'selected_ids':[]})
        self.assertEqual(change.status_code,200,change.text)
        self.assertTrue(self.context()['visual_plans'][0]['stale'])
        self.assertEqual(self.compile(body).status_code,409)

    def custom(self):
        t=catalog()[0]
        return {'id':'custom_travel_diary','name':'旅行中的一次意外：有旁白的单源日记','version':'1.0',
            'industry':'旅行','video_type':'经历叙事 Vlog','viewer_goal':'理解发生了什么以及当事人的取舍',
            'execution_mode':'narrated_single_source_2d','roles':[
                {'id':'departure','purpose':'说明出发时的目标','shot_logic':'保留原片交代环境的画面',
                 'pacing_logic':'观众理解地点后再推进','audio_logic':'保留同步旁白及原声'},
                {'id':'encounter','purpose':'呈现真实遭遇与选择','shot_logic':'原片动作和必要细节，配图仅作示意',
                 'pacing_logic':'不删掉关键动作或反应的观看时间','audio_logic':'保留原片音轨，不新增音乐'},
                {'id':'reflection','purpose':'回望感受及适用条件','shot_logic':'回到人物或原片收束画面',
                 'pacing_logic':'感受收束后留必要停顿','audio_logic':'保留原片的语句结尾'}],
            'required_materials':['已组织好的真实经历视频与旁白'],
            'avoid':['不虚构到访','不删掉理解事件所需的停留'],
            'slots':t['slots'],'emphasis_roles':['reflection'],'captions':t['captions']}

    def test_generated_custom_recipe_validation_compilation_render_and_snapshot(self):
        definition=self.custom()
        validation=self.client.post('/api/visual/recipes/validate',json=definition)
        self.assertEqual(validation.status_code,200,validation.text)
        self.assertEqual(validation.json()['semantic_verdict'],'not_verified')
        synthetic={**catalog()[0],'roles':definition['roles']}
        body=self.request(synthetic);body.update(template_id=definition['id'],template_version='1.0',
            custom_definition=definition,request_id='custom-travel')
        response=self.compile(body);self.assertEqual(response.status_code,200,response.text)
        saved=self.save(response.json()['visual_plan']);self.assertEqual(saved.status_code,200,saved.text)
        record=saved.json();output=self.export(record)
        self.assertEqual(record['template_definition']['industry'],'旅行')
        self.assertEqual(record['request']['template']['id'],definition['id'])
        self.assertEqual(sum(c['emphasized'] for c in fixtures.w.read(output/'visual-timeline.json')['captions']),1)
        # An old export retains its own definition even when the next recipe changes.
        definition['version']='1.1';definition['viewer_goal']='比较路线选择的代价'
        self.assertEqual(fixtures.w.read(output/'visual-plan.json')['template_definition']['version'],'1.0')
        path=self.path/'media'/self.mid/'visual-plans'/record['id']/'plan.json'
        altered=fixtures.w.read(path);altered['template_definition']['viewer_goal']='tampered'
        fixtures.w.write(path,altered)
        result=self.client.post(self.url+'/export',json={'revision':0,'asr_run':'run1',
            'source_sha256':self.media['sha256'],'visual_plan_id':record['id']})
        self.assertEqual(result.status_code,409,result.text)

    def test_music_montage_recipe_is_plan_only_and_invalid_logic_is_rejected(self):
        definition=self.custom();definition.update(execution_mode='planning_only',
            missing_capabilities=['independent visual-time anchors','multi-source timeline','music-beat editing'])
        valid=self.client.post('/api/visual/recipes/validate',json=definition)
        self.assertEqual(valid.status_code,200,valid.text)
        self.assertEqual(valid.json()['execution_mode'],'planning_only')
        body=self.request({**catalog()[0],'roles':definition['roles']})
        body.update(template_id=definition['id'],template_version='1.0',custom_definition=definition)
        response=self.compile(body);self.assertEqual(response.status_code,422,response.text)
        self.assertIn('planning only',response.text)
        self.assertFalse(self.context()['visual_plans'])
        for change in [{'emphasis_roles':['not_a_role']},{'missing_capabilities':[]},
                       {'roles':[definition['roles'][0],definition['roles'][0]]}]:
            bad={**definition,**change}
            self.assertEqual(self.client.post('/api/visual/recipes/validate',json=bad).status_code,422)


if __name__=='__main__':unittest.main()
