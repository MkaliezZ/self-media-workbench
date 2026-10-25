"""Versioned industry recipes compiled into the existing immutable visual plan."""
import copy
import hashlib
import json
import uuid
from typing import Literal
from fastapi import HTTPException
from pydantic import Field,model_validator
from visual_models import Strict, Rect, CaptionStyle, VisualPlan, WordID
from media_render import project_words
from review_edits import plan_keeps

VERSION='1.0'
COMPILER='industry-1'


def recipe(id,name,aliases,roles,materials,avoid,slots,emphasis,font,colour):
    return {'id':id,'name':name,'version':VERSION,'aliases':aliases,
        'roles':[{'id':r[0],'purpose':r[1]} for r in roles],
        'required_materials':materials,'avoid':avoid,'slots':slots,
        'emphasis_roles':emphasis,'captions':{'font_height':font,'bottom_margin':.08,
            'colour':'FFFFFF','emphasis_colour':colour},
        'scope':'single-source video, reviewed captions, local still images and static regions; Agent judges semantics'}


def slot(x,y,w,h):return {'x':x,'y':y,'width':w,'height':h}


CATALOG=[
 recipe('education','知识教学',['知识教学','教育','科普','教程'],
   [('question','明确学习者遇到的问题'),('demonstration','用真实步骤或解释展示怎么理解'),('takeaway','收束为可复用结论及条件')],
   ['完整讲述','实际步骤/结果或明确标记的解释图'],['不删除关键步骤等待','不靠装饰图替代演示'],
   {'landscape':slot(.47,.08,.49,.64),'portrait':slot(.06,.08,.88,.42)},['question','takeaway'],.052,'FFD54F'),
 recipe('finance','财经商业',['财经','金融','商业分析','财报'],
   [('question','提出具体指标或经营问题'),('data','展示实际材料及口径、单位与时间'),('boundary','保留假设、风险及不适用条件')],
   ['真实数据或明确逻辑示意','数据定义、时间与限定语'],['不造数据','不省略分母、基期和条件','图库不是具体事件证据'],
   {'landscape':slot(.45,.06,.51,.66),'portrait':slot(.06,.06,.88,.50)},['question','boundary'],.047,'8FD3FF'),
 recipe('beauty','美业服务',['美业','美妆','美容','护肤','美发'],
   [('concern','呈现具体需求和现状'),('detail','定位实际部位、手法或服务细节'),('boundary','说明个体差异及适用条件')],
   ['真实部位/过程画面或明确示意','同条件对照如有','实际适用边界'],['不遮脸部观察目标','不把示意当真实疗效','不同条件不能冒充效果对比'],
   {'landscape':slot(.66,.08,.30,.55),'portrait':slot(.64,.08,.30,.32)},['concern','boundary'],.052,'F4B8D2'),
 recipe('product','电商产品',['电商','产品测评','产品展示','带货'],
   [('use_case','建立具体使用场景'),('detail','展示实物细节、操作和可核实表现'),('fit','说明适合谁与限制')],
   ['实物与实际使用画面','关键表现所需的可核实材料'],['不掩盖关键动作','包装不能替代性能证据','不虚构购买/体验'],
   {'landscape':slot(.50,.08,.45,.64),'portrait':slot(.08,.10,.84,.46)},['use_case','fit'],.054,'FFCF75'),
 recipe('food','餐饮探店',['餐饮','探店','美食','餐厅'],
   [('scene','交代真实环境与消费场景'),('detail','呈现食物/制作/服务具体细节'),('verdict','给出有条件的体验判断')],
   ['真实场景和细节','体验或合作身份的真实说明'],['不虚构到店体验','不把生成食物当实拍','保留必要观看时间'],
   {'landscape':slot(.60,.06,.35,.48),'portrait':slot(.58,.08,.36,.32)},['verdict'],.052,'FFC093'),
 recipe('property','家居房产',['家居','房产','户型','装修'],
   [('need','说明居住需求与约束'),('space','呈现空间关系、尺寸或实际过程'),('boundary','明确条件、代价和取舍')],
   ['真实空间/户型或明确示意','尺寸和费用如有须有依据'],['不遮空间关系','不把效果图当实景','不捏造尺寸或预算'],
   {'landscape':slot(.42,.06,.54,.66),'portrait':slot(.06,.08,.88,.48)},['need','boundary'],.049,'B8D9C3'),
 recipe('travel_vlog','旅行 Vlog（有旁白）',['旅行vlog','旅行 vlog','旅行','旅游'],
   [('departure','交代地点、出行目标与期待'),('experience','按实际顺序呈现现场经历与细节'),('reflection','收束真实感受与出行条件')],
   ['已有旁白且已按顺序组织的单源视频','实际现场画面与可用的本地示意图'],
   ['保留环境与动作观看时间','不虚构到访或体验','纯音乐多源蒙太奇需额外时间轴能力'],
   {'landscape':slot(.66,.06,.29,.34),'portrait':slot(.64,.06,.30,.25)},['departure','reflection'],.043,'E4D2A8')]

# These distinct content mechanisms share the same rendering primitives.
CATALOG.extend([
 recipe('faceless_explainer','不露脸资料解说',['不露脸','资料解说'],
   [('claim','明确需要解释的命题'),('reference','资料卡或原图区域承担主要解释'),('conclusion','回到结论和限定条件')],
   ['完整讲述或旁白','与论点匹配的资料及具体区域'],['引用卡不能冒充事实核实','没有相关素材时不堆装饰图'],
   {'landscape':slot(.05,.06,.90,.66),'portrait':slot(.05,.06,.90,.56)},['claim','conclusion'],.049,'DDD2B8'),
 recipe('science_report','科普资料串联',['科普资料','资料串联'],
   [('question','明确待解释现象'),('evidence','大纲与可核实资料对应'),('explanation','解释机制与不确定条件')],
   ['资料支撑的大纲','文案与画面对应关系'],['示意与真实观测分开','先核实材料再安排画面'],
   {'landscape':slot(.40,.05,.55,.68),'portrait':slot(.06,.06,.88,.51)},['question','explanation'],.048,'B8D9E0'),
 recipe('life_story','生活场景叙事',['生活叙事','生活vlog','日常vlog'],
   [('space','先建立场景和空间'),('action','按实际前后关系展示行为'),('detail','由整体进入细节或感受')],
   ['相关场景和动作镜头','必要环境声与观看时间'],['静音不等于无用','缺动作应补拍而非制造因果'],
   {'landscape':slot(.69,.06,.25,.30),'portrait':slot(.68,.06,.26,.24)},['detail'],.043,'D7D2BC'),
 recipe('game_replay','游戏与录屏事件回看',['游戏剪辑','事件回看','录屏回看'],
   [('context','交代操作或事件前因'),('event','完整呈现关键变化'),('analysis','定位对象并解释为何重要')],
   ['实际事件和操作前后画面','重要UI与可定位目标'],['不遮关键UI','慢放和自动跟踪不因区域提示而默认具备'],
   {'landscape':slot(.72,.05,.24,.30),'portrait':slot(.68,.05,.28,.27)},['analysis'],.047,'CDD696'),
 recipe('first_person_story','第一人称经历解说',['第一人称','经历解说','影视解说'],
   [('setup','明确人物处境与叙述视角'),('event','把叙述与实际事件画面对齐'),('reflection','保留结果、感受与因果边界')],
   ['可用原片或真实经历材料','自有或获准使用的旁白'],['不克隆他人音色','不虚构原片或亲历','声音与画面可独立安排但不能伪造因果'],
   {'landscape':slot(.65,.06,.29,.38),'portrait':slot(.66,.06,.28,.30)},['setup','reflection'],.046,'D9BDAB')])


def digest(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def catalog():
    return [{**copy.deepcopy(t),'definition_sha256':digest(t)} for t in CATALOG]


def get_template(id,custom=None):
    if custom is not None:
        definition=RecipeDefinition.model_validate(custom).model_dump()
        if definition['id']!=id:raise ValueError('Custom recipe id does not match selected template')
        return {**definition,'definition_sha256':digest(definition)}
    item=next((t for t in catalog() if t['id']==id),None)
    if item is None:raise ValueError('Unknown industry template; discover the catalog')
    return item


def hints(task):
    return {'candidates':[{'id':t['id'],'name':t['name'],'version':t['version']}
        for t in CATALOG if any(a.casefold() in task.casefold() for a in t['aliases'])],
        'catalog_url':'/api/visual/templates','scope':'keyword candidates only; calling Agent selects using the complete task and actual materials'}


class Still(Strict):
    path: str
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    nature: Literal['unknown','recorded','generated','illustration','mixed']='unknown'
    source_note: str = Field(min_length=1,max_length=2000)
    usage_scope: str = Field(min_length=1,max_length=2000)
    highlight: Rect | None=None


class Beat(Strict):
    role: str = Field(min_length=1,max_length=60)
    word_ids: list[WordID] = Field(min_length=1,max_length=128)
    reason: str = Field(min_length=1,max_length=1000)
    material_note: str = Field(min_length=1,max_length=2000)
    visual_mode: Literal['source','image']='source'
    image: Still | None=None
    slot_override: Rect | None=None
    region: Rect | None=None
    emphasize: bool | None=None


class Role(Strict):
    id: str = Field(pattern=r'^[a-z_]{1,40}$')
    purpose: str = Field(min_length=1,max_length=1000)
    shot_logic: str = Field(min_length=1,max_length=2000)
    pacing_logic: str = Field(min_length=1,max_length=1000)
    audio_logic: str = Field(min_length=1,max_length=1000)


class Layouts(Strict):
    landscape: Rect
    portrait: Rect


class RecipeDefinition(Strict):
    id: str = Field(pattern=r'^custom_[a-z_]{1,50}$')
    name: str = Field(min_length=1,max_length=100)
    version: str = Field(pattern=r'^[0-9]+\.[0-9]+$')
    industry: str = Field(min_length=1,max_length=200)
    video_type: str = Field(min_length=1,max_length=200)
    viewer_goal: str = Field(min_length=1,max_length=1000)
    execution_mode: Literal['narrated_single_source_2d','native_timeline','planning_only']
    missing_capabilities: list[str] = Field(default_factory=list,max_length=20)
    roles: list[Role] = Field(min_length=2,max_length=8)
    required_materials: list[str] = Field(min_length=1,max_length=20)
    avoid: list[str] = Field(min_length=1,max_length=20)
    slots: Layouts
    emphasis_roles: list[str] = Field(default_factory=list,max_length=8)
    captions: CaptionStyle = Field(default_factory=CaptionStyle)

    @model_validator(mode='after')
    def coherence(self):
        roles=[r.id for r in self.roles]
        if len(roles)!=len(set(roles)) or any(r not in roles for r in self.emphasis_roles):
            raise ValueError('Recipe roles must be unique and emphasis must reference an existing role')
        texts=[self.name,self.industry,self.video_type,self.viewer_goal,*self.required_materials,*self.avoid,
            *self.missing_capabilities,*(s for r in self.roles for s in (r.purpose,r.shot_logic,r.pacing_logic,r.audio_logic))]
        if any(not s.strip() for s in texts):raise ValueError('Recipe fields must not be blank')
        if (self.execution_mode=='planning_only')!=bool(self.missing_capabilities):
            raise ValueError('Unsupported capability needs must use planning_only with explicit missing_capabilities')
        return self


class CompileTemplate(Strict):
    request_id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    project_revision: int = Field(ge=1)
    review_revision: int = Field(ge=0)
    asr_run: str = Field(min_length=1,max_length=80)
    source_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    template_id: str
    template_version: str
    custom_definition: RecipeDefinition | None=None
    selection_reason: str = Field(min_length=1,max_length=2000)
    frame_inspection_note: str = Field(min_length=1,max_length=2000)
    protected_regions: list[Rect] = Field(default_factory=list,max_length=32)
    captions: CaptionStyle | None=None
    beats: list[Beat] = Field(min_length=1,max_length=32)


def intersects(a,b):
    return a['x']<b['x']+b['width'] and b['x']<a['x']+a['width'] and a['y']<b['y']+b['height'] and b['y']<a['y']+a['height']


def compile_plan(body,review,width,height):
    t=get_template(body['template_id'],body.get('custom_definition'))
    if t.get('execution_mode')=='native_timeline':raise ValueError('Use timeline-plan with source seconds for this recipe, not the ASR visual compiler')
    if t.get('execution_mode')=='planning_only':raise ValueError('Recipe is planning only; missing: '+', '.join(t['missing_capabilities']))
    if body['template_version']!=t['version']:raise ValueError('Template version changed; inspect the catalog again')
    if not body['selection_reason'].strip() or not body['frame_inspection_note'].strip():raise ValueError('Inspect actual frames and explain template fit')
    mapped=project_words(review,plan_keeps(review,review.get('selected_ids',[]))['keeps'])
    kept=[w['id'] for w in mapped];groups=review.get('caption_groups',[])
    if not groups:raise ValueError('Industry templates require explicit reviewed caption_groups')
    if [i for g in groups for i in g]!=kept:raise ValueError('Reviewed caption groups must cover retained words exactly')
    roles=[r['id'] for r in t['roles']];beats=body['beats']
    actual=[b['role'] for b in beats]
    if any(r not in roles for r in actual) or set(actual)!=set(roles):raise ValueError('Missing or unsupported template roles: '+', '.join(roles))
    if [roles.index(r) for r in actual]!=sorted(roles.index(r) for r in actual):raise ValueError('Source order does not match template; do not silently reorder footage')
    if [i for b in beats for i in b['word_ids']]!=kept:raise ValueError('Beats must cover all retained groups once in original order; preserve qualifications')
    style=body['captions'] or CaptionStyle.model_validate(t['captions']).model_dump()
    plan={k:body[k] for k in ('request_id','project_revision','review_revision','asr_run','source_sha256')}
    plan.update({'reason':body['selection_reason'],'captions':style,'images':[],'regions':[],'emphasis':[],
        'template':{'id':t['id'],'version':t['version'],'definition_sha256':t['definition_sha256'],
            'compiler_version':COMPILER,'selection_reason':body['selection_reason'],'beats':beats,
            'frame_inspection_note':body['frame_inspection_note'],'protected_regions':body['protected_regions'],
            'custom_definition':body.get('custom_definition')}})
    for beat in beats:
        if not beat['reason'].strip() or not beat['material_note'].strip():raise ValueError('Each beat requires a reason and actual material inspection note')
        chosen=set(beat['word_ids']);local=[g for g in groups if chosen.intersection(g)]
        if any(not set(g)<=chosen for g in local):raise ValueError('A caption group crosses template beats; regroup explicitly first')
        anchor={'word_ids':beat['word_ids'],'reason':beat['reason']}
        if beat['visual_mode']=='image':
            if not beat['image']:raise ValueError('Image beat is missing its actual local asset')
            place=beat['slot_override'] or t['slots']['portrait' if height>width else 'landscape']
            if any(intersects(place,r) for r in body['protected_regions']):raise ValueError('Image slot overlaps a protected region; choose a safe slot or original footage')
            plan['images'].append({**anchor,**beat['image'],'slot':place})
        elif beat['image'] or beat['slot_override']:raise ValueError('Source beat cannot silently ignore an image/slot')
        if beat['region']:plan['regions'].append({**anchor,'rect':beat['region']})
        emphasize=beat['emphasize'] if beat['emphasize'] is not None else beat['role'] in t['emphasis_roles']
        if emphasize:
            plan['emphasis'] += [{'word_ids':g,'reason':beat['reason']} for g in local]
    return VisualPlan.model_validate(plan).model_dump()


def template_snapshot(binding):
    t=get_template(binding['id'],binding.get('custom_definition'))
    if binding['version']!=t['version'] or binding['definition_sha256']!=t['definition_sha256'] or binding['compiler_version']!=COMPILER:
        raise ValueError('Template definition changed; recompile and review')
    return {k:v for k,v in t.items() if k!='definition_sha256'}


def register(w):
    @w.app.get('/api/visual/templates')
    def list_templates():return {'templates':catalog(),'compiler_version':COMPILER}

    @w.app.post('/api/visual/recipes/validate')
    def validate_recipe(definition:RecipeDefinition):
        data=definition.model_dump()
        return {'definition':data,'definition_sha256':digest(data),'status':'structure_validated',
            'execution_mode':data['execution_mode'],'missing_capabilities':data['missing_capabilities'],
            'semantic_verdict':'not_verified','reasoning_executor':'calling Agent generates and reviews the recipe; service does not invoke a model'}

    @w.app.post('/api/projects/{pid}/media/{mid}/visual-template/compile')
    def compile_api(pid:str,mid:str,request:CompileTemplate):
        from visual_tools import check_binding,inspect_video,inspect_image,selections
        path=w.folder(pid);item=w.media(path,mid);body=request.model_dump()
        attempt=path/'media'/mid/'template-attempts'/(uuid.uuid4().hex+'.json')
        with w.LOCK:
            try:
                out=w.current_review(path,mid);review=w.read(out/'review.json')
                if body['project_revision']!=w.read(path/'project.json')['revision']:raise HTTPException(409,'Refresh project context')
                check_binding(body,review,out.name,item['sha256'])
                if not item.get('has_video'):raise ValueError('Template requires actual video')
                video=inspect_video(path/item['relative_path'])
                plan=compile_plan(body,review,video['width'],video['height'])
                selections(review,plan_keeps(review,review.get('selected_ids',[])),plan)
                for image in plan['images']:
                    if not image['source_note'].strip() or not image['usage_scope'].strip():raise ValueError('Image declarations must not be blank')
                    if inspect_image(image['path'])['sha256']!=image['sha256']:raise ValueError('Image hash mismatch')
                result={'visual_plan':plan,'template':get_template(body['template_id'],body.get('custom_definition')),
                    'status':'draft_not_saved','next_action':'Inspect the draft, save through visual_plan_save, then export with visual_plan_id',
                    'validation_scope':'structure, bindings, local asset checks; calling Agent must verify semantics, safety and readability'}
                w.write(attempt,{'accepted':True,'request':body,'result':result,'at':w.now()})
                return result
            except (ValueError,OSError,StopIteration,HTTPException) as exc:
                error=exc if isinstance(exc,HTTPException) else HTTPException(422,str(exc))
                w.write(attempt,{'accepted':False,'request':body,'detail':error.detail,'at':w.now()})
                raise error
