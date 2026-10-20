"""Local workbench server. Bind to loopback; all media stays on disk.

Document editing is explicit: this server does not silently call a cloud LLM or
pretend template text is an AI diagnosis. Agent task packs carry source evidence.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from local_asr import DEFAULT_MODEL, transcribe
from review_edits import plan_keeps, corrected_text
from media_models import MediaImport, ReviewEdit, ExportReview
from settings import DATA, SKILL, LIBRARY, ASR_BACKEND, DEVICE, MLX_MODEL,CPP_EXECUTABLE,CPP_MODEL,CPP_GPU_INDEX,REQUIRE_GPU
from media_render import render

ROOT = Path(__file__).resolve().parents[1]
DATA.mkdir(parents=True, exist_ok=True)
if not (SKILL / 'SKILL.md').is_file():
    raise RuntimeError(f'Configured self-media skill entry is missing: {SKILL / "SKILL.md"}')
POOL = ThreadPoolExecutor(max_workers=1)
LOCK = threading.RLock()
app = FastAPI(title='自媒体工作台 · 本地开发版')


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(path.read_text('utf-8'))


def file_sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.' + uuid.uuid4().hex + '.tmp')
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    os.replace(temp, path)


def folder(pid):
    if len(pid) != 32 or any(c not in '0123456789abcdef' for c in pid):
        raise HTTPException(404, '项目不存在')
    path = DATA / pid
    if not (path/'project.json').is_file():
        raise HTTPException(404, '项目不存在')
    return path


def event(path, action, detail):
    with LOCK:
        with (path/'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'at':now(), 'action':action, 'detail':detail}, ensure_ascii=False)+'\n')


def snapshot(path, project):
    project['updated_at'] = now()
    project['revision'] = project.get('revision', 0)+1
    write(path/'versions'/f"{project['revision']:06d}.json", project)
    write(path/'project.json', project)


# Jobs left running by a previous shutdown are visible as interrupted, not forever running.
for job_path in DATA.glob('*/jobs/*.json'):
    job = read(job_path)
    if job.get('status') in ('queued', 'running'):
        job.update(status='interrupted', error='服务曾中断；原件与已完成版本保留，可重新运行')
        write(job_path, job)


@app.middleware('http')
async def local_only(request: Request, call_next):
    host = request.headers.get('host', '').split(':')[0]
    if host not in ('localhost', '127.0.0.1', '[::1]'):
        return JSONResponse({'detail':'仅本机访问'}, status_code=403)
    origin = request.headers.get('origin')
    if request.method not in ('GET','HEAD') and origin and origin != str(request.base_url).rstrip('/'):
        return JSONResponse({'detail':'跨来源写入被拒绝'}, status_code=403)
    return await call_next(request)


@app.get('/api/status')
def status():
    progress = LIBRARY/'阅读记录/当前阅读进度.json' if LIBRARY else None
    return {'stage':'development', 'root':str(ROOT), 'model':str(DEFAULT_MODEL),
            'model_present':(DEFAULT_MODEL/'model.bin').is_file(),
            'asr_configuration':{'backend':ASR_BACKEND,'device':DEVICE,'mlx_model':str(MLX_MODEL),
                'cpp_executable':str(CPP_EXECUTABLE),'cpp_model':str(CPP_MODEL),'cpp_gpu_index':CPP_GPU_INDEX,'require_gpu':REQUIRE_GPU},
            'library_progress':read(progress) if progress and progress.exists() else None,
            'generation':'calling AI agent reasons; local tools persist, validate and execute',
            'agent_capabilities':'/api/agent/v1/capabilities',
            'skill':str(SKILL)}


@app.get('/api/projects')
def projects():
    return sorted([read(p) for p in DATA.glob('*/project.json')], key=lambda x:x['updated_at'], reverse=True)


@app.post('/api/projects')
async def create(request: Request):
    body = await request.json()
    title = str(body.get('title','')).strip()
    if not title or len(title)>120:
        raise HTTPException(422,'请输入1—120字项目名')
    pid = uuid.uuid4().hex
    path = DATA/pid
    path.mkdir()
    project = {'id':pid, 'title':title, 'created_at':now(), 'documents':{}, 'media':[],
               'verification':'needs_review', 'simulation':bool(body.get('simulation',False))}
    snapshot(path, project)
    event(path,'create',{'simulation':project['simulation']})
    return project


@app.get('/api/projects/{pid}')
def get_project(pid: str):
    return read(folder(pid)/'project.json')


@app.put('/api/projects/{pid}/documents/{stage}')
async def save_document(pid: str, stage: str, request: Request):
    if stage not in ('evidence','diagnose','topics','script','publish','review'):
        raise HTTPException(404,'未知环节')
    body = await request.json()
    content = body.get('content')
    if not isinstance(content, str) or len(content)>1000000:
        raise HTTPException(422,'内容须为文本，最多100万字符')
    structured=body.get('structured')
    if structured is not None and (not isinstance(structured,dict) or len(json.dumps(structured,ensure_ascii=False))>1000000):
        raise HTTPException(422,'表单数据须为对象，最多100万字符')
    path = folder(pid)
    with LOCK:
        project = read(path/'project.json')
        if body.get('revision') != project['revision']:
            raise HTTPException(409,'版本已更新；请先重新载入，避免覆盖其他修改')
        project['documents'][stage] = {'content':content,'updated_at':now(),'origin':'explicit_edit_or_import'}
        if structured is not None:
            project['documents'][stage]['structured']=structured
        # Editing text cannot promote an evidence level automatically.
        snapshot(path, project)
        event(path,'save_document',{'stage':stage,'revision':project['revision']})
    return project


def media_provenance(body):
    if not isinstance(body, dict):
        raise HTTPException(422, '素材说明须为对象')
    nature = body.get('media_nature', 'unknown')
    if nature not in ('unknown', 'recorded', 'generated', 'restored', 'mixed'):
        raise HTTPException(422, '请选择未知、实拍/实录、生成、修复/增强或混合素材')
    result = {'media_nature': nature}
    for key in ('source_note', 'usage_scope'):
        value = body.get(key, '')
        if not isinstance(value, str) or len(value) > 2000:
            raise HTTPException(422, '素材说明须为文本，每项最多2000字')
        result[key] = value
    return result


@app.post('/api/projects/{pid}/media')
async def import_media(pid: str, body: MediaImport):
    provenance = media_provenance(body.model_dump())
    raw = body.path
    source = Path(raw)
    if raw.startswith(('\\\\','//')) or not source.is_absolute() or not source.is_file():
        raise HTTPException(422,'请输入本机已存在的绝对文件路径')
    if source.suffix.lower() not in ('.mp4','.mov','.mkv','.webm','.wav','.mp3','.m4a'):
        raise HTTPException(422,'支持常见音视频文件')
    path = folder(pid)
    mid = uuid.uuid4().hex
    dest = path/'media'/mid/('original'+source.suffix.lower())
    dest.parent.mkdir(parents=True)
    await __import__('asyncio').to_thread(shutil.copy2, source, dest)
    digest = await __import__('asyncio').to_thread(file_sha256, dest)
    metadata = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(dest)]))
    item = {'id':mid,'name':source.name,'imported_from':str(source),'relative_path':dest.relative_to(path).as_posix(),
            'sha256':digest,'duration':float(metadata['format']['duration']),
            'has_video':any(s['codec_type']=='video' for s in metadata['streams']), 'imported_at':now()}
    item.update(provenance)
    if not any(s['codec_type']=='audio' for s in metadata['streams']):
        raise HTTPException(422,'素材没有音轨，不能识别口播')
    with LOCK:
        project = read(path/'project.json')
        project['media'].append(item)
        snapshot(path,project)
        event(path,'import_media',item)
    return {'project':project,'media':item}


def media(path, mid):
    for item in read(path/'project.json')['media']:
        if item['id']==mid:
            return item
    raise HTTPException(404,'素材不存在')


@app.put('/api/projects/{pid}/media/{mid}/metadata')
async def save_media_metadata(pid: str, mid: str, request: Request):
    body = await request.json()
    provenance = media_provenance(body)
    path = folder(pid)
    with LOCK:
        project = read(path/'project.json')
        if body.get('revision') != project['revision']:
            raise HTTPException(409, '版本已更新；请先重新载入')
        item = next((m for m in project['media'] if m['id'] == mid), None)
        if item is None:
            raise HTTPException(404, '素材不存在')
        item.update(provenance)
        snapshot(path, project)
        event(path, 'media_metadata_save', {'media_id':mid, 'revision':project['revision'], **provenance})
    return {'project':project, 'media':item}


def launch(path, mid, kind, task):
    jid = uuid.uuid4().hex
    state = {'id':jid,'media_id':mid,'kind':kind,'status':'queued','created_at':now()}
    job_path = path/'jobs'/f'{jid}.json'
    write(job_path,state)
    def run():
        state.update(status='running', started_at=now())
        write(job_path,state)
        try:
            state['result']=task()
            state['status']='done'
        except Exception as exc:
            state.update(status='failed',error=str(exc))
        state['finished_at']=now()
        write(job_path,state)
        event(path,'job_finished',state)
    POOL.submit(run)
    return state


@app.post('/api/projects/{pid}/media/{mid}/transcribe')
def asr(pid: str, mid: str):
    path = folder(pid)
    item = media(path,mid)
    # Each run gets its own directory; never replace a corrected transcript.
    runid = uuid.uuid4().hex
    out = path/'media'/mid/'asr'/runid
    def run():
        result = transcribe(path/item['relative_path'], out)
        with LOCK:
            write(path/'media'/mid/'current-asr.json', {'run_id':runid})
        return {'run_id':runid,'device':result['device'],'backend':result['backend'],
                'execution':result['execution'],'words':len(result['words']),
                'candidates':len(result['candidates']),'fallback_errors':result['fallback_errors']}
    return launch(path,mid,'asr',run)


def current_review(path,mid):
    media(path,mid)
    marker = path/'media'/mid/'current-asr.json'
    if not marker.exists():
        raise HTTPException(404,'尚未完成识别')
    return path/'media'/mid/'asr'/read(marker)['run_id']


@app.get('/api/projects/{pid}/media/{mid}/review')
def get_review(pid: str,mid: str):
    out = current_review(folder(pid),mid)
    review = read(out/'review.json')
    return {**review, 'revision':review.get('revision',0), 'asr_run':out.name}


@app.put('/api/projects/{pid}/media/{mid}/review')
async def save_review(pid: str, mid: str, request: Request):
    payload = await request.json()
    path = folder(pid)
    media(path,mid)
    attempt_file = path/'media'/mid/'review-attempts'/(uuid.uuid4().hex+'.json')
    with LOCK:
        try:
            try:
                body = ReviewEdit.model_validate(payload).model_dump()
            except ValidationError as exc:
                raise HTTPException(422,exc.errors(include_url=False,include_context=False,include_input=False))
            out = current_review(path,mid)
            review = read(out/'review.json')
            if body['asr_run'] is not None and body['asr_run'] != out.name:
                raise HTTPException(409,'ASR运行已变化，请重新读取当前转录')
            if body['source_sha256'] is not None and body['source_sha256'] != review.get('source_sha256'):
                raise HTTPException(409,'转录来源哈希不匹配')
            if body['revision'] != review.get('revision',0):
                raise HTTPException(409,'转录审阅已更新，请重新载入')
            corrections = body['corrections']
            for key, text in corrections.items():
                if not key.isdigit() or int(key)>=len(review['words']) or not text.strip() or len(text)>200:
                    raise HTTPException(422,'改字须对应现有词组，不能清空或伪造时间戳')
                word=review['words'][int(key)]
                word['text']=corrected_text(word['text'],text)
            selected = review.get('selected_ids',[]) if body['selected_ids'] is None else body['selected_ids']
            speech = review.get('speech_cuts',[]) if body['speech_cuts'] is None else body['speech_cuts']
            try:
                plan = plan_keeps(review,selected,speech)
            except (ValueError,TypeError) as exc:
                raise HTTPException(422,str(exc))
            caption_groups = review.get('caption_groups',[]) if body['caption_groups'] is None else body['caption_groups']
            if caption_groups:
                expected = [w['id'] for w in review['words'] if w['id'] not in plan['deleted_word_ids']]
                flat = [wid for group in caption_groups for wid in group]
                if any(not group for group in caption_groups) or flat != expected:
                    raise HTTPException(422,'字幕分组须按原顺序完整覆盖全部保留词组，各ID恰好一次；删区变化后须重新分组或显式[]回自动')
            review.update(selected_ids=selected,speech_cuts=speech,
                          caption_groups=caption_groups,
                          revision=review.get('revision',0)+1,asr_run=out.name)
            review['text']=''.join(w['text'] for w in review['words'])
            write(out/'versions'/f"{review['revision']:06d}.json",review)
            write(out/'review.json',review)
            write(out/'edit-decision.json',plan)
            write(attempt_file,{'at':now(),'accepted':True,'request':payload,'asr_run':out.name,
                                'review_revision':review['revision']})
            event(path,'review_save',{'media_id':mid,'revision':review['revision'],
                                      'selected_ids':selected,'corrections':corrections,'speech_cuts':speech})
        except HTTPException as exc:
            write(attempt_file,{'at':now(),'accepted':False,'request':payload,
                                'http_status':exc.status_code,'detail':exc.detail})
            raise
    return {'review':review,'plan':plan}


@app.post('/api/projects/{pid}/media/{mid}/export')
def export(pid: str,mid: str,body: ExportReview | None=None):
    path = folder(pid)
    with LOCK:
        out = current_review(path,mid)
        item = media(path,mid)
        review = read(out/'review.json')
        if body is not None and (body.asr_run != out.name or body.revision != review.get('revision',0)
                                 or body.source_sha256 != review.get('source_sha256')):
            raise HTTPException(409,'导出所绑定的识别/审阅/原件已变化，请重新核对')
        source_metadata = {**media_provenance(item), 'declaration_only':True}
        project_revision = read(path/'project.json')['revision']
        plan = plan_keeps(review, review.get('selected_ids',[]))
        if not item['has_video']:
            raise HTTPException(422,'当前导出需要视频；音频识别可用，音频成品导出尚未实现')
        export_id = uuid.uuid4().hex
        dest = path/'exports'/export_id
        write(dest/'review.snapshot.json',review)
        write(dest/'plan.json',plan)
    def run():
        source=path/item['relative_path']
        with source.open('rb') as stream:
            current_hash=hashlib.file_digest(stream,'sha256').hexdigest()
        if current_hash!=item['sha256'] or review['source_sha256']!=item['sha256']:
            raise RuntimeError('原件或转录来源哈希不匹配；停止导出，先重新核对素材')
        render(source, review, plan, dest)
        write(dest/'provenance.json',{'source_sha256':item['sha256'],'source_media_id':mid,
                                     'source_media_metadata':source_metadata,
                                     'project_revision_at_export':project_revision,
                                     'asr_run':out.name,'review_revision':review.get('revision',0),
                                     'created_at':now(),'external_publication':False})
        return {'export_id':export_id,'files':['reviewed_cut.mp4','reviewed_cut.srt',
                                             'reviewed_cut.words.json','edit-decision.json','provenance.json']}
    return launch(path,mid,'export',run)


@app.get('/api/projects/{pid}/jobs/{jid}')
def get_job(pid: str,jid: str):
    path=folder(pid)/'jobs'/(jid+'.json')
    if not path.is_file() or path.parent != folder(pid)/'jobs':
        raise HTTPException(404,'任务不存在')
    return read(path)


@app.get('/api/projects/{pid}/jobs')
def list_jobs(pid: str):
    return sorted([read(p) for p in (folder(pid)/'jobs').glob('*.json')],
                  key=lambda item:item['created_at'],reverse=True)


@app.get('/api/projects/{pid}/media/{mid}/original')
def original(pid:str,mid:str):
    path=folder(pid)
    return FileResponse(path/media(path,mid)['relative_path'])


@app.get('/api/projects/{pid}/exports/{eid}/{name}')
def artifact(pid:str,eid:str,name:str):
    path=folder(pid)
    allowed={'reviewed_cut.mp4','reviewed_cut.srt','reviewed_cut.words.json','edit-decision.json','provenance.json'}
    if len(eid)!=32 or any(c not in '0123456789abcdef' for c in eid) or name not in allowed:
        raise HTTPException(404,'文件不存在')
    file=path/'exports'/eid/name
    if not file.is_file():
        raise HTTPException(404,'文件尚未生成')
    return FileResponse(file,filename=name)


@app.get('/api/projects/{pid}/agent-pack')
def agent_pack(pid:str):
    path=folder(pid)
    project=read(path/'project.json')
    text = '# Codex自媒体任务交接\n\n项目：'+project['title']+'\n\n'
    text += ('模拟验收数据，未真实发布。\n\n' if project['simulation'] else '未标记为模拟；素材性质与事实仍须按来源核对，缺失信息不得虚构。\n\n')
    text += '请按 self-media-workflow 读取所需阶段；保留来源、初稿、修订原因、实际计算和待核实项。\n'
    text += '当前skill：'+str(SKILL/'SKILL.md')+'\n本项目：'+str(path)+'\n\n'
    for stage, doc in project['documents'].items():
        text+='## '+stage+'\n\n'+doc['content']+'\n\n'
    text += '## 素材说明（用户填写，未独立核验）\n\n'
    text += '原件哈希证明文件一致，不证明实拍、权利或效果；生成/修复细节不能充当原始记录。\n\n'
    for item in project['media']:
        record = {key:item.get(key) for key in ('id','name','relative_path','sha256')}
        record.update(media_provenance(item))
        text += '```json\n'+json.dumps(record, ensure_ascii=False, indent=2)+'\n```\n\n'
    file=path/'agent-task.md'
    file.write_text(text,encoding='utf-8')
    return FileResponse(file,filename='agent-task.md')


@app.post('/api/projects/{pid}/calculate/{kind}')
async def calculate(pid:str,kind:str,request:Request):
    if kind not in ('metrics','script_check'):
        raise HTTPException(404,'未知校验')
    body=await request.json()
    path=folder(pid)/'calculations'/uuid.uuid4().hex
    write(path/'input.json',body)
    proc=subprocess.run([sys.executable,'-B','-X','utf8',str(SKILL/'scripts'/(kind+'.py')),
                         str(path/'input.json'),'--out',str(path/'result.json')],
                        capture_output=True,text=True,encoding='utf-8')
    if proc.returncode:
        write(path/'failure.json',{'exit_code':proc.returncode,'stderr':proc.stderr,'stdout':proc.stdout})
        raise HTTPException(422,(proc.stderr or proc.stdout)[-3000:])
    return read(path/'result.json')


from agent_api import register as register_agent_api
register_agent_api(sys.modules[__name__])

@app.get('/')
def agent_entry():
    return {'primary_client':'ai_agent', 'entry':'AGENTS.md', 'capabilities':'/api/agent/v1/capabilities',
            'task_entry':'/api/agent/v1/tasks', 'external_publication':False}


if __name__=='__main__':
    import uvicorn
    uvicorn.run(app,host='127.0.0.1',port=8765)
