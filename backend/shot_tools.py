"""Optional parameterized shots: frozen render -> generated media -> existing timeline."""
import asyncio
import copy
import hashlib
import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path

from fastapi import HTTPException
from PIL import ImageFont
from shot_models import ShotRender
from visual_tools import font_file

ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT/'shot_renderer'
VENDOR = ROOT/'third_party/video-shotcraft'


def digest(body):
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()).hexdigest()


def source_files():
    return [RENDERER/'package.json', RENDERER/'package-lock.json', RENDERER/'render.mjs',
            *sorted((RENDERER/'src').rglob('*.tsx')), VENDOR/'catalog.json', VENDOR/'LICENSE']


def runtime_status():
    node = os.environ.get('SELF_MEDIA_SHOT_NODE') or shutil.which('node')
    browser = os.environ.get('SELF_MEDIA_SHOT_BROWSER')
    chrome_mode = 'chrome-for-testing' if browser else 'headless-shell'
    marker = RENDERER/'.runtime/browser.json'
    if not browser and marker.is_file():
        try:
            saved=json.loads(marker.read_text('utf-8'));browser=saved.get('path')
            chrome_mode=saved.get('chrome_mode','headless-shell')
        except (OSError, ValueError): pass
    dependencies = (RENDERER/'node_modules/@remotion/renderer/package.json').is_file()
    versions={}
    try:
        required=json.loads((RENDERER/'package.json').read_text('utf-8'))['dependencies']
        for name,expected in required.items():
            version=json.loads((RENDERER/'node_modules'/name/'package.json').read_text('utf-8'))['version']
            versions[name]=version
            if version!=expected:dependencies=False
    except (OSError,ValueError,KeyError):dependencies=False
    return {'available':bool(node and Path(node).is_file() and dependencies and browser and Path(browser).is_file()),
            'node':node, 'dependencies_installed':dependencies, 'versions':versions,'browser':browser,
            'chrome_mode':chrome_mode,
            'browser_present':bool(browser and Path(browser).is_file()),
            'setup_helper':str(ROOT/'scripts/setup_shots.py'),
            'reference':str(ROOT/'skills/self-media-workflow/references/shots.md'),
            'render_mode':'local headless; no workbench frontend; no automatic dependency download',
            'license':'Remotion has separate terms; third-party shot sources are Apache-2.0'}


def catalog(query='', status=None):
    data=json.loads((VENDOR/'catalog.json').read_text('utf-8'))
    q=query.casefold().strip()
    cards=[c for c in data['cards'] if (not status or c['status']==status)
           and (not q or q in json.dumps(c,ensure_ascii=False).casefold())]
    return {**{k:v for k,v in data.items() if k!='cards'}, 'cards':cards,
            'matched':len(cards), 'runtime':runtime_status(),
            'scope':'124 reference cards; only named adaptations have executable bounded parameters; no claim of exact demo reproduction'}


def images_in(shot):
    if shot['kind']=='before-after':
        return [('before',shot['before']),('after',shot['after'])]
    return [(f'item-{i}',item['image']) for i,item in enumerate(shot.get('items',[])) if item.get('image')]


def resolve_images(w,path,project,shot):
    sources=[]
    for key,ref in images_in(shot):
        item=next((i for i in project.get('image_assets',[]) if i['id']==ref['asset_id']),None)
        if not item: raise ValueError('Unknown project image: '+ref['asset_id'])
        source=Path(item['path']).resolve()
        if not source.is_relative_to(path.resolve()): raise ValueError('Image must belong to this project')
        if item['sha256']!=ref['sha256'] or w.file_sha256(source)!=ref['sha256']:
            raise HTTPException(409,'Image changed; refresh context and review')
        if source.suffix.lower() not in ('.png','.jpg','.jpeg','.webp'):
            raise ValueError('Shot images must be PNG/JPEG/WebP')
        sources.append({'key':key,'path':source,'ref':ref,'metadata':copy.deepcopy(item)})
    return sources


def text_layout(body,font):
    """Preflight the final text as well as the animated initial states."""
    shot=body['shot']; W=1920 if body['width']>=body['height'] else 1080
    H=W*body['height']/body['width']; portrait=H>W; margin=78 if portrait else 110; content=W-2*margin
    def fit(texts,width,height,largest,smallest=26,line_height=1.3):
        for size in range(largest,smallest-1,-1):
            face=ImageFont.truetype(str(font),size)
            valid=True
            for text in texts:
                lines=str(text).split('\n'); count=0
                for line in lines:
                    # Browser wraps anywhere; sum advances conservatively, then test hard lines.
                    count+=max(1,__import__('math').ceil(face.getlength(line)/max(1,width-size)))
                if count*size*line_height>height or any(face.getlength(ch)>width for ch in text):valid=False;break
            if valid:return size
        raise ValueError('Text exceeds readable safe area; shorten text, split the shot, or reduce item count')
    layout={'title':fit([shot['title']],content,130,78),
            'subtitle':fit([shot.get('subtitle','')],content,100,34),
            'body':40,'detail':28,'hero':100,'tick':28}
    kind=shot['kind'];items=shot.get('items',[]);bodyY=410 if portrait else 310;bottom=H-125
    if kind=='typewriter-rewrite':
        layout['hero']=fit([shot['initial'],shot['replacement']],content-100,H*.27,120,40)
    elif kind in ('marker-title','outline-title'):
        layout['hero']=fit([shot['title']],content,H*.25,150,40)
    elif kind=='digit-roll':
        layout['hero']=fit([shot['value']],content-100,H*.2,160,40)
    elif kind=='list-reveal':
        row=min(170 if portrait else 95,(bottom-bodyY)/len(items)-18)
        layout['body']=fit([f'{i+1:02}  '+it['label'] for i,it in enumerate(items)],content-60,row*.55,42,26,1.2)
        layout['detail']=fit([it['detail'] for it in items],content-60,row*.36,28,18,1.2)
    elif items:
        if kind=='card-stack': cw=content*(.88 if portrait else .62)
        else: cw=(content-24)/2 if not portrait else content
        layout['body']=fit([it['label'] for it in items],cw-68,110,44)
        layout['detail']=fit([it['detail'] for it in items],cw-68,108,28,20)
        if kind=='card-stack':
            layout['detail']=min(layout['detail'],fit(['  /  '.join(it['label'] for it in items)],content,80,28,20))
    elif kind=='before-after':
        layout['body']=fit([shot['before_label'],shot['after_label']],content*.4-16,70,38)
    elif kind=='line-chart':
        cell=(W-margin-50-(140 if portrait else 220))/(len(shot['points'])-1)
        labels=[d['label'] for d in shot['points']]+[f"{d['value']:g}"+shot['unit'] for d in shot['points']]
        layout['tick']=fit(labels,cell*.85,55,30,16,1.2)
        if any(ImageFont.truetype(str(font),layout['tick']).getlength(t)>cell*.85 for t in labels):
            raise ValueError('Chart labels overlap; shorten labels/unit or use fewer points')
    return layout


def verify_output(w,dest,props):
    command=['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(dest/'shot.mp4')]
    result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',timeout=180,check=True)
    streams=json.loads(result.stdout)['streams'];v=next(s for s in streams if s['codec_type']=='video')
    if v['width']!=props['width'] or v['height']!=props['height'] or int(v['nb_read_frames'])!=props['duration_in_frames']:
        raise ValueError('Rendered canvas/frame count differs from frozen request')
    from fractions import Fraction
    if Fraction(v['avg_frame_rate'])!=props['fps']:raise ValueError('Rendered fps differs from frozen request')
    subprocess.run(['ffmpeg','-v','error','-i',str(dest/'shot.mp4'),'-f','null','-'],
                   capture_output=True,timeout=180,check=True)
    return {'sha256':w.file_sha256(dest/'shot.mp4'),'frames':int(v['nb_read_frames']),
            'width':v['width'],'height':v['height'],'fps':props['fps'],'full_decode':True,
            'verification':'technical; visual, listening and human acceptance remain separate'}


def register(w):
    @w.app.get('/api/visual/shots')
    def library(q:str='',status:str | None=None):
        if status not in (None,'adapted_subset','reference_only'):raise HTTPException(422,'Unknown catalog status')
        return catalog(q,status)

    @w.app.get('/api/visual/shots/status')
    def status():return runtime_status()

    @w.app.get('/api/projects/{pid}/shot-renders')
    def history(pid:str):return [w.read(p) for p in sorted((w.folder(pid)/'shot-renders').glob('*/request.json'))]

    @w.app.post('/api/projects/{pid}/shot-renders')
    def render(pid:str,request:ShotRender):
        path=w.folder(pid);body=request.model_dump();signature=digest(body)
        attempt=path/'shot-attempts'/(uuid.uuid4().hex+'.json')
        with w.LOCK:
            try:
                receipt=path/'shot-requests'/(body['request_id']+'.json')
                if receipt.exists():
                    previous=w.read(receipt)
                    if previous['signature']!=signature:raise HTTPException(409,'request_id reused with changed content')
                    record=w.read(path/'shot-renders'/previous['render_id']/'request.json')
                    if digest(record['request'])!=signature:raise HTTPException(409,'Frozen request integrity mismatch')
                    return {'render_id':previous['render_id'],'job':w.get_job(pid,previous['job_id']), 'idempotent_replay':True}
                project=w.read(path/'project.json')
                if project['revision']!=body['project_revision']:raise HTTPException(409,'Project changed; refresh context and reconsider')
                runtime=runtime_status()
                if not runtime['available']:raise HTTPException(503,{'message':'Optional shot renderer is not ready; Agent runs setup helper',**runtime})
                sources=resolve_images(w,path,project,body['shot']);font=font_file(body['font_path'])
                if font.suffix.lower() not in ('.ttf','.otf','.ttc'):raise ValueError('Unsupported font format')
                layout=text_layout(body,font)
                rid=uuid.uuid4().hex;dest=path/'shot-renders'/rid;public=dest/'public';public.mkdir(parents=True)
                font_name='font'+font.suffix.lower();shutil.copyfile(font,public/font_name)
                props={k:copy.deepcopy(body[k]) for k in ('width','height','fps','background','foreground','accent','secondary','shot')}
                props.update(duration_in_frames=round(body['duration']*body['fps']),font_file=font_name,layout=layout)
                frozen=[]
                for source in sources:
                    name=source['key']+source['path'].suffix.lower();shutil.copyfile(source['path'],public/name)
                    if w.file_sha256(public/name)!=source['ref']['sha256']:raise ValueError('Image changed while freezing')
                    frozen.append({'key':source['key'],'relative_path':'public/'+name,'sha256':source['ref']['sha256'],'metadata':source['metadata']})
                    if source['key'].startswith('item-'):props['shot']['items'][int(source['key'][5:])]['image_file']=name
                    else:props['shot'][source['key']+'_file']=name
                code=[]
                for source in source_files():
                    local=source.relative_to(RENDERER).as_posix() if source.is_relative_to(RENDERER) else 'upstream/'+source.name
                    target=dest/local;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
                    code.append({'relative_path':local,'sha256':w.file_sha256(target)})
                w.write(dest/'props.json',props)
                record={'id':rid,'created_at':w.now(),'request':body,'request_sha256':signature,'props_sha256':digest(props),
                    'upstream_revision':catalog()['revision'],'files':code+frozen+[
                        {'relative_path':'public/'+font_name,'sha256':w.file_sha256(public/font_name)}],
                    'runtime':runtime,'nature':'generated','fidelity':'adapted motion grammar, not exact upstream demo',
                    'external_publication':False}
                w.write(dest/'request.json',record)

                def worker():
                    def check_frozen():
                        if digest(w.read(dest/'props.json'))!=record['props_sha256']:raise ValueError('Frozen props changed')
                        for file in record['files']:
                            if w.file_sha256(dest/file['relative_path'])!=file['sha256']:raise ValueError('Frozen shot input changed')
                    check_frozen()
                    for name in ('render.mjs','package.json','package-lock.json'):
                        if w.file_sha256(RENDERER/name)!=w.file_sha256(dest/name):raise ValueError('Renderer runtime changed; submit a new render')
                    command=[runtime['node'],str(RENDERER/'render.mjs'),str(dest),runtime['browser'],runtime.get('chrome_mode','headless-shell')]
                    try:
                        with (dest/'render.log').open('w',encoding='utf-8') as stream:
                            result=subprocess.run(command,cwd=RENDERER,stdout=stream,stderr=subprocess.STDOUT,
                                timeout=1200,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                        if result.returncode:raise RuntimeError('Shot render failed; inspect '+str(dest/'render.log'))
                    except subprocess.TimeoutExpired as exc:raise RuntimeError('Shot render timed out; partial files retained') from exc
                    check_frozen()
                    verification=verify_output(w,dest,props);w.write(dest/'verification.json',verification)
                    from media_models import MediaImport
                    imported=asyncio.run(w.import_media(pid,MediaImport(path=str(dest/'shot.mp4'),media_nature='generated',
                        source_note=f"Parameterized shot {body['shot']['kind']}; render_id={rid}; upstream={record['upstream_revision']}",
                        usage_scope='Generated motion segment; data and image rights require their own review')))
                    result={'render_id':rid,'media_id':imported['media']['id'],'media':imported['media'],
                        'verification':verification,'path':str(dest/'shot.mp4'),'record_path':str(dest/'request.json'),
                        'next':'Refresh context; use this registered generated media in native timeline or an advanced talking scene',
                        'external_publication':False}
                    w.write(dest/'result.json',result);return result

                # launch writes the job while this lock is held; worker waits before recording state.
                job=w.launch(path,None,'shot_render',worker)
                project.setdefault('shot_renders',[]).append({'id':rid,'job_id':job['id'],'relative_path':str((dest/'request.json').relative_to(path))})
                w.snapshot(path,project)
                w.write(receipt,{'render_id':rid,'job_id':job['id'],'signature':signature})
                w.write(attempt,{'accepted':True,'request':body,'render_id':rid,'at':w.now()})
                w.event(path,'shot_render_queued',{'render_id':rid,'job_id':job['id']})
                return {'render_id':rid,'job':job,'idempotent_replay':False}
            except (ValueError,OSError,HTTPException) as exc:
                error=exc if isinstance(exc,HTTPException) else HTTPException(422,str(exc))
                w.write(attempt,{'accepted':False,'request':body,'detail':error.detail,'at':w.now()});raise error
