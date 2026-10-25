"""Unified task intake: resolve state and prerequisites, leave reasoning to Agent."""
import hashlib
import json
import re
import shutil
import uuid
from pathlib import Path
from typing import Literal
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

STAGES = ['diagnose','topics','script','publish','review']
MEDIA = {'.mp4','.mov','.mkv','.webm','.wav','.mp3','.m4a'}


class TaskRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    task: str = Field(min_length=1, max_length=10000)
    intent: Literal['auto','full','diagnose','topics','script','edit','publish','review'] = 'auto'
    project: str | None = None
    new_project: bool = False
    title: str | None = Field(default=None, min_length=1, max_length=120)
    input_paths: list[str] = Field(default_factory=list)
    source_nature: Literal['provided','observed','simulation','reference'] = 'provided'
    media_nature: Literal['unknown','recorded','generated','restored','mixed'] = 'unknown'
    source_note: str = Field(default='', max_length=2000)
    usage_scope: str = Field(default='', max_length=2000)
    simulation: bool = False
    session_key: str = Field(default='default', min_length=1, max_length=200)
    request_id: str = Field(default_factory=lambda:uuid.uuid4().hex, pattern=r'^[A-Za-z0-9_-]{1,80}$')


def infer_intent(task, has_media=False):
    text = task.casefold()
    # Explicit exclusions are removed from this routing hint, never from source materials.
    hint = re.sub(r'(?:不要|不用|不做|无需|不需要|不|no |do not )(?:再)?(?:剪辑|行业模板|剪视频|配图|画面高亮|重点文案|字幕|转场|蒙版|遮罩|时间轴|音乐卡点|特效|动效|段落抽离|文章标黄|聚光灯|画中画|transition|mask|visual edit|edit|复盘|发布|诊断|选题)', '', text)
    if any(k in hint for k in ['完整流程','全流程','从头到尾','full workflow','end to end']):return 'full'
    pairs = [('review',['复盘','发布数据','数据分析','review performance']),
             ('edit',['剪辑','行业模板','剪口播','剪气口','转录','字幕','配图','画面高亮','重点文案','转场','蒙版','遮罩','时间轴','音乐卡点','特效','动效','段落抽离','文章标黄','聚光灯','画中画','transition','mask','edit video','transcribe','visual edit']),
             ('publish',['发布准备','发布包','准备发布','publish preparation']),
             ('script',['脚本','逐字稿','口播稿','改稿','script']),
             ('topics',['选题','选个题','想几个题','topic']),
             ('diagnose',['诊断','对标','账号分析','diagnose','benchmark'])]
    hits = [name for name,keys in pairs if any(k in hint for k in keys)]
    if len(hits) > 1:return 'full'
    if hits:return hits[0]
    return 'edit' if has_media else 'full'


def register_tasks(w, context):
    @w.app.post('/api/agent/v1/tasks')
    async def task_entry(body:TaskRequest):
        if not body.task.strip():raise HTTPException(422,'Task must not be blank')
        if body.new_project and body.project:raise HTTPException(422,'Choose a project or request a new one, not both')
        # Validate all supplied inputs before creating or changing a project.
        inputs = []
        for raw in body.input_paths:
            p = Path(raw).expanduser()
            if not p.is_absolute() or not p.is_file() or raw.startswith(('\\\\','//')):
                raise HTTPException(422,f'Input must be an existing local absolute path: {raw}')
            p = p.resolve()
            if p.suffix.lower() in MEDIA:inputs.append((p,'media',None))
            elif p.suffix.lower() in ('.png','.jpg','.jpeg'):
                from visual_tools import inspect_image
                try:inputs.append((p,'image',inspect_image(p)))
                except (ValueError,OSError) as exc:raise HTTPException(422,str(exc))
            elif p.suffix.lower() in ('.txt','.md','.json','.csv'):
                try:
                    if p.stat().st_size > 1000000:raise ValueError('over one million bytes')
                    content = p.read_text('utf-8-sig')
                    if not content.strip():raise ValueError('empty file')
                except (ValueError,UnicodeError) as exc:raise HTTPException(422,f'Invalid UTF-8 source: {p.name}: {exc}')
                inputs.append((p,'text',content))
            else:raise HTTPException(422,f'Unsupported input type: {p.suffix}; provide UTF-8 text, audio/video or PNG/JPEG')
        signature = hashlib.sha256(body.model_dump_json().encode()).hexdigest()
        registry = w.DATA.parent / 'task-requests' / f'{body.request_id}.json'
        with w.LOCK:
            if registry.exists():
                old = w.read(registry)
                if old['signature'] != signature:raise HTTPException(409,'Task request_id reused with different input')
                return {**old['result'],'idempotent_replay':True}
            session_file = w.DATA.parent/'sessions'/(hashlib.sha256(body.session_key.encode()).hexdigest()+'.json')
            projects = w.projects()
            new_requested = body.new_project or (not body.project and any(k in body.task.casefold() for k in ['新建项目','新项目','另开项目','new project']))
            continue_requested = any(k in body.task.casefold() for k in ['继续','接着','上次','这个项目','该项目','resume','continue'])
            matches = []
            if not new_requested:
                if body.project:
                    matches = [p for p in projects if p['id']==body.project or p['title']==body.project]
                    if not matches:raise HTTPException(404,'Requested project not found')
                else:
                    matches = [p for p in projects if len(p['title']) >= 4 and p['title'] in body.task]
                    if not matches and continue_requested:
                        active = w.read(session_file).get('project_id') if session_file.exists() else None
                        matches = [p for p in projects if p['id']==active] if active else projects
                        if not matches:raise HTTPException(409,{'code':'no_project_to_resume','message':'No matching current project; provide a project name or begin a new task'})
                if len(matches) > 1:
                    raise HTTPException(409,{'code':'ambiguous_project','candidates':[{'id':p['id'],'title':p['title']} for p in matches]})
            if matches:
                project = matches[0]
                if body.simulation and not project['simulation']:
                    raise HTTPException(409,'Do not change a real project into a simulation by resuming; create a simulation project')
                created = False
            else:
                project = {'id':uuid.uuid4().hex,'title':body.title or body.task[:120],
                           'created_at':w.now(),'documents':{},'media':[],
                           'verification':'needs_review','simulation':body.simulation}
                path = w.DATA/project['id'];path.mkdir(parents=True)
                w.snapshot(path,project);w.event(path,'create',{'simulation':body.simulation});created=True
            pid = project['id'];path = w.folder(pid)
        registered = []
        for p,kind,content in inputs:
            if kind == 'image':
                with w.LOCK:
                    project=w.read(path/'project.json')
                    existing=next((a for a in project.get('image_assets',[]) if a['sha256']==content['sha256']),None)
                    if not existing:
                        local=path/'agent/assets'/(content['sha256']+p.suffix.lower());local.parent.mkdir(parents=True,exist_ok=True)
                        if not local.exists():shutil.copy2(p,local)
                        if w.file_sha256(local)!=content['sha256']:raise HTTPException(409,'Image changed during task intake')
                        existing={**content,'id':uuid.uuid4().hex,'path':str(local),'label':p.name,
                            'source_note':body.source_note,'usage_scope':body.usage_scope,'declaration_only':True}
                        project.setdefault('image_assets',[]).append(existing);w.snapshot(path,project)
                        w.event(path,'image_asset_registered',existing)
                    registered.append({'kind':'image',**existing})
            elif kind == 'media':
                project = w.read(path/'project.json')
                digest = w.file_sha256(p)
                existing = next((m for m in project['media'] if m['sha256']==digest),None)
                item = existing or (await w.import_media(pid,w.MediaImport(path=str(p),media_nature=body.media_nature,
                    source_note=body.source_note,usage_scope=body.usage_scope)))['media']
                registered.append({'kind':'media','id':item['id'],'reused':existing is not None})
            else:
                digest = hashlib.sha256(content.encode('utf-8')).hexdigest()
                with w.LOCK:
                    project = w.read(path/'project.json')
                    nature = 'simulation' if project['simulation'] else body.source_nature
                    item = next((e for e in project.get('agent_sources',[]) if e['sha256']==digest and e['nature']==nature),None)
                    existed = item is not None
                    if not item:
                        sid = 'E'+uuid.uuid4().hex;file=path/'agent/sources'/f'{sid}.txt';file.parent.mkdir(parents=True,exist_ok=True)
                        file.write_bytes(content.encode('utf-8'))
                        item = {'id':sid,'label':p.name,'nature':nature,'origin':str(p),
                                'relative_path':file.relative_to(path).as_posix(),'sha256':digest,'created_at':w.now(),'declaration_only':True}
                        project.setdefault('agent_sources',[]).append(item);w.snapshot(path,project);w.event(path,'agent_source_registered',item)
                    registered.append({'kind':'source','id':item['id'],'reused':existed})
        state = context(pid)
        intent = body.intent if body.intent != 'auto' else infer_intent(body.task, bool(state['media']))
        current = {a['stage']:a for a in state['artifacts'] if state['heads'].get(a['stage'])==a['id'] and not a['dependency_stale']}
        start = next((stage for stage in STAGES if stage not in current),None) if intent == 'full' else intent
        plan = (STAGES[STAGES.index(start):] if start else []) if intent=='full' else [start]
        parent = {'topics':'diagnose','script':'topics','publish':'script','review':'publish'}.get(start)
        with w.LOCK:
            w.write(session_file,{'project_id':pid,'updated_at':w.now()})
            task_id = uuid.uuid4().hex
            w.write(path/'agent/tasks'/f'{task_id}.json',{'at':w.now(),'request':body.model_dump(),
                     'intent':intent,'start':start,'input_context_id':state['context_id']})
            state = context(pid)
            result = {'task_id':task_id,'task':body.task,'project_id':pid,'project_created':created,
                      'intent':intent,'start_at':start,'plan':plan,'registered':registered,
                      'workflow_status':'complete' if start is None else 'action_required',
                      'routing_scope':'state-aware routing hint; calling Agent must confirm semantic fit to the user task',
                      'standalone_reason_required':bool(parent and parent not in current),
                      'context_url':f'/api/agent/v1/projects/{pid}/context','context':state,
                      'instructions':('All stages have current artifacts. Report the saved state and unresolved limits; do not start another cycle unless the user requests one.' if start is None else 'Read AGENTS.md and the task-specific skill reference. The calling Agent creates and submits artifacts; this response is an intake plan, not generated content. Re-read context after each mutation. For edit, discover media-review/export/job schemas; do not auto-delete candidates.'),
                      'external_publication':False}
            if intent=='edit':
                from editing_templates import hints
                result['editing_templates']=hints(body.task)
            from talking_profiles import hints as talking_hints
            result['talking_profiles']=talking_hints(body.task)
            w.write(registry,{'signature':signature,'result':result})
            w.event(path,'task_routed',{'task_id':task_id,'intent':intent,'start':start})
        return result
