"""Agent-authored talking-head scenes compiled to the existing native timeline."""
import copy,hashlib,json,uuid
from typing import Literal
from fastapi import HTTPException
from pydantic import Field,model_validator
from visual_models import Strict,Rect
from motion_models import Effect
from timeline_models import TimelinePlan,SourceRef,Shot,AudioBed,Title,MaskCue

PROFILES={
 'ordinary_talking_head':{'id':'ordinary_talking_head','name':'普通口播','version':'1.0',
   'workflow':['核对原件与ASR','审阅删音与字幕分组','必要的重点或本地配图','导出与检查'],
   'runtime':'ASR review + visual-plan; optional clean native scenes',
   'rule':'清晰的人声和原意优先；不自动升级为多层包装'},
 'advanced_talking_head':{'id':'advanced_talking_head','name':'高级口播','version':'1.0',
   'workflow':['按语义拆成镜头任务','选择原件/比喻/证据/关系图/对照/收束','为每层制定进退、透视与焦点','口播与画面分时编排','核对阅读停留、人声和原件','冻结并导出原生时间轴'],
   'runtime':'talking-profile compile -> native timeline -> actual export',
   'rule':'镜头回答具体问题；多层合成与素材生产分开；保留干净讲述段落和阅读停留',
   'grammar':['关键词匹配剪辑','前中后景遮挡与视差','多阶段纸页透视和拉正','局部清晰与边缘失焦','节制的网点/颗粒/彩边/暗角','文案分批出现','关系图逐步推进','成对类比与对照','证据原像素抽离'],
   'limits':['No automatic OCR, segmentation or subject tracking','No 3D modeling, rigging or physically correct depth of field','No native speech/music generation','Authored output timing is not automatic acoustic alignment']}}


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def catalog():return [{**copy.deepcopy(p),'definition_sha256':digest(p)} for p in PROFILES.values()]


def validate_binding(body):
    b=body['production_profile'];p=b.get('profile',{});known=PROFILES.get(p.get('id'))
    if known!=p or b.get('definition_sha256')!=digest(p):raise ValueError('Invalid frozen talking profile definition')
    if len(b.get('scenes',[]))!=len(body['shots']):raise ValueError('Profile scene count differs from shots')
    frame=0
    for scene,shot in zip(b['scenes'],body['shots']):
        frames=round((shot['source_out']-shot['source_in'])*body['fps'])
        if scene.get('shot_id')!=shot['id'] or scene.get('mode')!=shot['role'] or scene.get('purpose')!=shot['reason']:raise ValueError('Profile scene differs from its shot')
        if abs(scene.get('output_start',-1)-frame/body['fps'])>1e-6 or abs(scene.get('output_end',-1)-(frame+frames)/body['fps'])>1e-6:raise ValueError('Profile scene clock changed; recompile')
        frame+=frames
    if body.get('transitions') or body.get('music_grid'):raise ValueError('Recompile talking scenes before changing their clock; overlapping transitions/music grids are not in profile compiler v1')


def hints(task):
    text=task.casefold()
    advanced=any(k in text for k in ['高级口播','advanced talking','高级解说'])
    ordinary=any(k in text for k in ['普通口播','ordinary talking','基础口播'])
    return {'selected':None if advanced==ordinary else 'advanced_talking_head' if advanced else 'ordinary_talking_head',
        'candidates':[v['id'] for v in catalog()], 'catalog':'/api/visual/talking-profiles',
        'selection_scope':'Conservative hint; calling Agent respects exclusions, actual materials and project state',
        'reference':'references/advanced-talking.md'}


class Scene(Strict):
    shot: Shot
    mode: Literal['anchor','hook','metaphor','evidence','diagram','comparison','bridge','takeaway']
    spoken_text: str=Field(min_length=1,max_length=4000,description='Caller-reviewed speech for this interval; not ASR certification')
    purpose: str=Field(min_length=1,max_length=1000)
    material_note: str=Field(min_length=1,max_length=2000)
    claim_kind: Literal['evidence','illustration','opinion']
    evidence_source_id: str | None=None
    headline: str=Field(default='',max_length=60,description='Optional succinct overlay, not a second full subtitle track')
    headline_slot: Rect=Field(default_factory=lambda:Rect(x=.08,y=.15,width=.84,height=.32))
    effects: list[Effect]=Field(default_factory=list,max_length=16,description='Native effects in scene-relative output seconds')

    @model_validator(mode='after')
    def meaningful(self):
        if any(not getattr(self,k).strip() for k in ('spoken_text','purpose','material_note')):raise ValueError('Review the speech, purpose and actual material')
        if self.claim_kind=='evidence' and not self.evidence_source_id:raise ValueError('Evidence scenes need an actual source binding')
        if self.claim_kind!='evidence' and self.evidence_source_id:raise ValueError('Illustration/opinion must not silently claim evidence')
        return self


class TalkingCompile(Strict):
    profile_id: Literal['ordinary_talking_head','advanced_talking_head']
    profile_version: str
    profile_sha256: str=Field(pattern=r'^[a-f0-9]{64}$')
    request_id: str=Field(pattern=r'^[A-Za-z0-9_-]{1,80}$')
    project_revision: int=Field(ge=1)
    supersedes: str | None=None
    revision_reason: str=Field(min_length=1,max_length=2000)
    intent: str=Field(min_length=1,max_length=2000)
    width: int=Field(default=1280,ge=160,le=1920)
    height: int=Field(default=720,ge=160,le=1920)
    fps: int=Field(default=25,ge=15,le=60)
    sources: list[SourceRef]=Field(min_length=1,max_length=128)
    scenes: list[Scene]=Field(min_length=1,max_length=32)
    audio: list[AudioBed]=Field(default_factory=list,max_length=16)
    titles: list[Title]=Field(default_factory=list,max_length=64)
    masks: list[MaskCue]=Field(default_factory=list,max_length=16)
    font_path: str | None=None


def compile_plan(request):
    p=PROFILES[request['profile_id']]
    if request['profile_version']!=p['version'] or request['profile_sha256']!=digest(p):raise ValueError('Talking profile changed; inspect the catalog before compiling')
    body={k:copy.deepcopy(request[k]) for k in ['request_id','project_revision','supersedes','revision_reason','intent','width','height','fps','sources','audio','titles','masks','font_path']}
    body.update(logic_id='advanced_talking_head' if p['id']=='advanced_talking_head' else None,shots=[],effects=[])
    frame=0;manifest=[];fps=body['fps'];source_ids={s['id'] for s in body['sources']}
    for scene in request['scenes']:
        shot=copy.deepcopy(scene['shot']);duration=round((shot['source_out']-shot['source_in'])*fps)/fps;start=frame/fps
        if duration<=0:raise ValueError('Scene must span at least one output frame')
        if scene['evidence_source_id'] and scene['evidence_source_id'] not in source_ids:raise ValueError('Unknown evidence source')
        used={shot['source_id']}|{e['source_id'] for e in scene['effects'] if 'source_id' in e}
        if scene['claim_kind']=='evidence' and scene['evidence_source_id'] not in used:raise ValueError('Evidence source must actually be displayed in its own scene')
        if p['id']=='ordinary_talking_head' and scene['effects']:raise ValueError('Ordinary native scenes stay clean; use visual-plan for ASR captions or explicitly choose advanced')
        shot['role']=scene['mode'];shot['reason']=scene['purpose'];body['shots'].append(shot)
        for cue in scene['effects']:
            if cue['start']>=cue['end'] or cue['end']>duration+1e-7:raise ValueError('Effect crosses its scene; use scene-relative seconds')
            cue=copy.deepcopy(cue);cue['start']+=start;cue['end']+=start;body['effects'].append(cue)
        if scene['headline'].strip():
            if duration<1.3:raise ValueError('Headline has no readable hold')
            body['effects'].append({'kind':'motion_text','text':scene['headline'],'slot':scene['headline_slot'],
                'font_height':.065,'start':start+.1,'end':start+duration-.1,'enter_seconds':.4,'exit_seconds':.25,
                'animation':'slide_up','reason':'A succinct scene headline; inspect contrast and safe areas'})
        manifest.append({k:copy.deepcopy(scene[k]) for k in ['mode','spoken_text','purpose','material_note','claim_kind','evidence_source_id']})
        manifest[-1].update(shot_id=shot['id'],output_start=start,output_end=start+duration)
        frame+=round(duration*fps)
    if p['id']=='advanced_talking_head' and not any(s['effects'] for s in request['scenes']):raise ValueError('Advanced template needs actual authored composition, not only a renamed title')
    binding={'profile':copy.deepcopy(p),'definition_sha256':digest(p),'scenes':manifest,
        'verification':'needs_review','scope':'Frozen editing decisions and displayed source bindings, not proof of facts, material rights or perceptual quality'}
    body['production_profile']=binding
    return TimelinePlan.model_validate(body).model_dump(),binding


def register(w):
    @w.app.get('/api/visual/talking-profiles')
    def profiles():return {'profiles':catalog(),'compiler_version':'1.0','primary_client':'calling Agent'}

    @w.app.post('/api/projects/{pid}/talking-profile/compile')
    def compile_api(pid:str,request:TalkingCompile):
        from timeline_tools import resolve_sources,timeline_map
        from motion_tools import preflight_text
        from visual_tools import font_file
        path=w.folder(pid);attempt=path/'talking-attempts'/(uuid.uuid4().hex+'.json');raw=request.model_dump()
        with w.LOCK:
            try:
                project=w.read(path/'project.json')
                if raw['project_revision']!=project['revision'] or raw['supersedes']!=project.get('timeline_head'):raise HTTPException(409,'Project/head changed; inspect context')
                plan,binding=compile_plan(raw);resolved=resolve_sources(w,path,plan);mapping=timeline_map(plan,resolved)
                if plan['effects']:preflight_text(plan,font_file(plan['font_path']))
                result={'timeline_plan':plan,'talking_profile':binding,'map':mapping,'status':'draft_not_saved',
                    'audio_scope':'Actual selected intervals decode above the near-silence floor; this does not certify speech, transcript accuracy or listening quality',
                    'next_action':'Inspect and save timeline_plan unchanged through timeline-plans; poll export to a terminal state. Retain this profile manifest with the draft.'}
                w.write(attempt,{'accepted':True,'at':w.now(),'request':raw,'result':result});return result
            except (ValueError,OSError,HTTPException) as exc:
                error=exc if isinstance(exc,HTTPException) else HTTPException(422,str(exc))
                w.write(attempt,{'accepted':False,'at':w.now(),'request':raw,'detail':error.detail});raise error
