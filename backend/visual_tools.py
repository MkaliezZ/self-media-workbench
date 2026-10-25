"""Local deterministic visual composition; no remote model, asset search or shell."""
import hashlib
import json
import shutil
import subprocess
import sys
import unicodedata
import uuid
from pathlib import Path
from fastapi import HTTPException, Request
from pydantic import ValidationError
from media_render import project_words, captions
from review_edits import plan_keeps
from visual_models import VisualPlan


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def probe(path, count_frames=False):
    result=subprocess.run(['ffprobe','-v','error',*(['-count_frames'] if count_frames else []),'-show_streams','-show_format','-of','json',str(path)],
                          capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=30)
    if result.returncode:
        raise ValueError('Cannot probe visual input')
    return json.loads(result.stdout)


def inspect_image(path):
    original=Path(path)
    if not original.is_absolute() or str(path).startswith(('\\\\','//')) or not original.is_file() or original.suffix.lower() not in ('.png','.jpg','.jpeg'):
        raise ValueError('Provide a local absolute PNG/JPEG path')
    if original.stat().st_size>25_000_000:raise ValueError('Image exceeds 25 MB')
    meta=probe(original,count_frames=True);streams=meta.get('streams',[])
    frames=streams[0].get('nb_frames','N/A') if streams else 'N/A'
    if (len(streams)!=1 or streams[0].get('codec_name') not in ('png','mjpeg')
        or meta.get('format',{}).get('format_name') not in ('png_pipe','jpeg_pipe','image2')
        or streams[0].get('nb_read_frames')!='1'
        or (str(frames).isdigit() and int(frames)>1)):
        raise ValueError('Only static PNG/JPEG images are supported')
    image=streams[0]
    if image.get('tags',{}).get('rotate') not in (None,'0') or any(s.get('rotation',0)!=0 for s in image.get('side_data_list',[])):
        raise ValueError('Normalize rotated image before visual planning')
    if max(image['width'],image['height'])>12000 or image['width']*image['height']>40_000_000:
        raise ValueError('Image dimensions are too large')
    return {'width':image['width'],'height':image['height'],'sha256':sha(original)}


def inspect_video(path):
    video=next(s for s in probe(path)['streams'] if s['codec_type']=='video')
    if video.get('sample_aspect_ratio','1:1') not in ('1:1','0:1','N/A'):
        raise ValueError('Normalize non-square-pixel video before visual planning')
    if video.get('tags',{}).get('rotate') not in (None,'0') or any(s.get('rotation',0)!=0 for s in video.get('side_data_list',[])):
        raise ValueError('Normalize rotated video before visual planning')
    return video


def font_file(custom=None):
    if custom and custom.startswith(('\\\\','//')):raise ValueError('Use an installed local font')
    candidates=[custom] if custom else ([
        'C:/Windows/Fonts/msyh.ttc','C:/Windows/Fonts/simhei.ttf'] if sys.platform=='win32' else [
        '/System/Library/Fonts/PingFang.ttc','/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
        '/System/Library/Fonts/STHeiti Medium.ttc','/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'])
    for raw in candidates:
        if raw and Path(raw).is_absolute() and Path(raw).is_file() and Path(raw).suffix.lower() in ('.ttf','.ttc','.otf'):
            return Path(raw)
    raise ValueError('A local CJK font is required; supply captions.font_path to an installed TTF/TTC/OTF')


def status():
    try:
        result=subprocess.run(['ffmpeg','-hide_banner','-filters'],capture_output=True,text=True,
                              encoding='utf-8',errors='replace',timeout=15)
        available={line.split()[1] for line in result.stdout.splitlines() if len(line.split())>2}
        missing=sorted({'drawtext','drawbox','overlay','scale'}-available)
        encoders=subprocess.run(['ffmpeg','-hide_banner','-encoders'],capture_output=True,text=True,
            encoding='utf-8',errors='replace',timeout=15)
        encoder_names={line.split()[1] for line in encoders.stdout.splitlines() if len(line.split())>2}
        missing_encoders=sorted({'libx264'}-encoder_names)
        font=str(font_file())
        return {'available':not missing and not missing_encoders and bool(shutil.which('ffprobe')) and result.returncode==0 and encoders.returncode==0,
                'missing_filters':missing,'missing_encoders':missing_encoders,'ffprobe':shutil.which('ffprobe'),'font':font,
                'scope':'local 2D captions/images/static regions; calling Agent selects content; CPU composition'}
    except (OSError,ValueError,subprocess.TimeoutExpired) as exc:
        return {'available':False,'error':str(exc),'scope':'local 2D composition'}


def selections(review, keep, body):
    mapped=project_words(review,keep['keeps'])
    ids=[w['id'] for w in mapped]
    groups=review.get('caption_groups',[])
    if body['captions']['enabled'] and not groups:
        raise ValueError('Save explicit reviewed caption_groups before styled caption export')
    if body['emphasis'] and not body['captions']['enabled']:
        raise ValueError('Caption emphasis requires enabled captions')
    seen=set()
    events=[]
    for kind in ('emphasis','images','regions'):
        for index,item in enumerate(body[kind]):
            chosen=item['word_ids']
            if not item['reason'].strip() or len(set(chosen))!=len(chosen) or any(i not in ids for i in chosen):
                raise ValueError('Visual anchors must reference unique retained groups with a reason')
            positions=[ids.index(i) for i in chosen]
            if positions!=list(range(positions[0],positions[0]+len(positions))):
                raise ValueError('Visual anchors must follow consecutive retained groups')
            if kind=='emphasis':
                if chosen not in groups or seen.intersection(chosen):
                    raise ValueError('Emphasis must equal a complete reviewed caption group without duplicates')
                seen.update(chosen)
            words=[mapped[i] for i in positions]
            events.append({'kind':kind,'index':index,'word_ids':chosen,
                           'start':words[0]['start'],'end':words[-1]['end'],
                           'reason':item['reason']})
    return events


def check_binding(record, review, run, source_hash):
    if (record['asr_run']!=run or record['review_revision']!=review.get('revision',0)
        or record['source_sha256']!=source_hash or review.get('source_sha256')!=source_hash):
        raise HTTPException(409,'Visual plan is stale; inspect the current review and save a new bound plan')


def validate_record(record, directory):
    """Revalidate persisted plans and frozen inputs before queuing an export."""
    try:
        body=VisualPlan.model_validate(record['request']).model_dump()
        if any(record[key]!=body[key] for key in ('asr_run','review_revision','source_sha256')):
            raise ValueError('Plan binding integrity mismatch')
        if body.get('template'):
            from editing_templates import digest
            if digest(record['template_definition'])!=body['template']['definition_sha256']:
                raise ValueError('Frozen template definition integrity mismatch')
        if len(record['assets'])!=len(body['images']):raise ValueError('Plan asset count mismatch')
        for index,asset in enumerate(record['assets']):
            file=Path(directory)/asset['relative_path']
            if file.parent!=Path(directory) or asset['sha256']!=body['images'][index]['sha256'] or sha(file)!=asset['sha256']:
                raise ValueError('Plan image integrity mismatch')
        if body['captions']['enabled']:
            font=Path(directory)/record['font']['relative_path']
            if font.parent!=Path(directory) or sha(font)!=record['font']['sha256']:raise ValueError('Plan font integrity mismatch')
    except (KeyError,ValueError,OSError) as exc:
        raise HTTPException(409,f'Invalid saved visual plan: {exc}')


def wrapped(text, limit):
    # Presentation wrapping only. Never alters the spoken word-group boundaries.
    lines=[''];units=0
    for c in text:
        if c=='\n':
            lines.append('');units=0;continue
        if c=='\r':continue
        n=2 if unicodedata.east_asian_width(c) in ('W','F') else 1
        if units+n>limit:
            lines.append('');units=0
        lines[-1]+=c;units+=n
    if len(lines)>2:
        raise ValueError('Caption is too long for two lines; regroup by meaning or reduce font size')
    return '\n'.join(lines)


def geometry(image, slot, width, height):
    scale=min(width*slot['width']/image['width'],height*slot['height']/image['height'])
    iw=max(2,int(image['width']*scale)//2*2);ih=max(2,int(image['height']*scale)//2*2)
    return {'x':round(width*slot['x']+(width*slot['width']-iw)/2),
            'y':round(height*slot['y']+(height*slot['height']-ih)/2),'width':iw,'height':ih}


def compose(review, keeps, record, plan_dir, dest):
    dest=Path(dest);plan_dir=Path(plan_dir)
    validate_record(record,plan_dir)
    width,height=record['video_width'],record['video_height']
    events=selections(review,keeps,record['request'])
    body=record['request']; filters=[]; inputs=[]; last='0:v'; visual_events=[]
    def step(expr):
        nonlocal last
        label=f'v{len(filters)}';filters.append(f'[{last}]{expr}[{label}]');last=label
    def enabled(event):return f"enable='gte(t,{event['start']:.6f})*lt(t,{event['end']:.6f})'"
    def box(rect,event,colour):
        step(f"drawbox=x={rect['x']}:y={rect['y']}:w={rect['width']}:h={rect['height']}:color=0x{colour}@0.20:t=fill:{enabled(event)}")
        step(f"drawbox=x={rect['x']}:y={rect['y']}:w={rect['width']}:h={rect['height']}:color=0x{colour}:t={max(2,round(height*.004))}:{enabled(event)}")
    for event in events:
        item=body[event['kind']][event['index']]
        if event['kind']=='images':
            asset=record['assets'][event['index']];source=plan_dir/asset['relative_path']
            if sha(source)!=asset['sha256']:raise ValueError('Visual asset integrity mismatch')
            local=f"image-{event['index']}{source.suffix}"
            shutil.copy2(source,dest/local);inputs+=['-loop','1','-i',local]
            place=geometry(asset,item['slot'],width,height)
            label=f"img{event['index']}";index=event['index']+1
            filters.append(f'[{index}:v]scale={place["width"]}:{place["height"]},setsar=1[{label}]')
            output=f'v{len(filters)}';filters.append(f'[{last}][{label}]overlay=x={place["x"]}:y={place["y"]}:eof_action=repeat:shortest=1:{enabled(event)}[{output}]');last=output
            if item.get('highlight'):
                roi=item['highlight'];box({'x':round(place['x']+roi['x']*place['width']),
                    'y':round(place['y']+roi['y']*place['height']),
                    'width':max(1,round(roi['width']*place['width'])),
                    'height':max(1,round(roi['height']*place['height']))},event,'FFD54F')
            visual_events.append({**event,'placed_rect':place,'image_highlight':item.get('highlight')})
        elif event['kind']=='regions':
            r=item['rect'];rect={k:round(r[k]*(width if k in ('x','width') else height)) for k in r}
            box(rect,event,item['colour']);visual_events.append({**event,'placed_rect':rect})
    style=body['captions'];caption_records=[]
    if style['enabled']:
        font=plan_dir/record['font']['relative_path']
        if sha(font)!=record['font']['sha256']:raise ValueError('Font integrity mismatch')
        local_font='font'+font.suffix;shutil.copyfile(font,dest/local_font)
        mapped=project_words(review,keeps['keeps']);by_id={w['id']:w for w in mapped}
        cues=captions(review,mapped);groups=review['caption_groups']
        emphasis={tuple(e['word_ids']) for e in body['emphasis']}
        for i,(cue,group) in enumerate(zip(cues,groups)):
            marked=tuple(group) in emphasis
            size=max(12,round(height*style['font_height']*(1.08 if marked else 1)))
            shown=wrapped(cue['text'],max(4,int(width*.88/size)*2))
            filename=f'caption-{i:04d}.txt';(dest/filename).write_text(shown,'utf-8')
            colour=style['emphasis_colour'] if marked else style['colour']
            margin=round(height*style['bottom_margin'])
            step(f"drawtext=fontfile={local_font}:textfile={filename}:expansion=none:fontsize={size}:fontcolor=0x{colour}:box=1:boxcolor=black@0.55:boxborderw={max(2,round(size*.15))}:x=(w-text_w)/2:y=h-text_h-{margin}:enable='gte(t,{cue['start']:.6f})*lt(t,{cue['end']:.6f})'")
            caption_records.append({**cue,'word_ids':group,'emphasized':marked,'display_text':shown})
    if not filters:raise ValueError('Visual plan has no enabled operation; export the ordinary cut instead')
    script=dest/'visual-filters.txt';script.write_text(';\n'.join(filters),'utf-8')
    (dest/'visual-timeline.json').write_text(json.dumps({'events':visual_events,'captions':caption_records},ensure_ascii=False,indent=2),'utf-8')
    command=['ffmpeg','-hide_banner','-v','error','-nostdin','-n','-i','reviewed_cut.mp4',*inputs,
             '-/filter_complex',script.name,'-map',f'[{last}]','-map','0:a:0',
             '-c:v','libx264','-preset','medium','-crf','18',
             '-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart','visual.mp4']
    try:
        result=subprocess.run(command,cwd=dest,capture_output=True,text=True,encoding='utf-8',errors='replace',
            timeout=max(120,min(7200,300+keeps['output_duration']*20)))
    except subprocess.TimeoutExpired as exc:
        (dest/'visual-render-process.json').write_text(json.dumps({'command':command,'timed_out':True},indent=2),'utf-8')
        raise RuntimeError('Visual render timed out; partial files retained') from exc
    (dest/'visual-render-process.json').write_text(json.dumps({'command':command,'returncode':result.returncode,'stderr':result.stderr},ensure_ascii=False,indent=2),'utf-8')
    if result.returncode:raise RuntimeError(result.stderr[-3000:])
    return {'plan_id':record['id'],'operations':len(events),'primary_video':'visual.mp4',
            'files':['visual.mp4','visual-plan.json','visual-timeline.json']}


def register(w):
    @w.app.get('/api/visual/status')
    def visual_status():return status()

    @w.app.get('/api/projects/{pid}/media/{mid}/visual-plans')
    def plans(pid:str,mid:str):
        path=w.folder(pid);w.media(path,mid)
        return [w.read(p) for p in sorted((path/'media'/mid/'visual-plans').glob('*/plan.json'))]

    @w.app.post('/api/projects/{pid}/media/{mid}/visual-plans')
    async def save(pid:str,mid:str,request:Request):
        path=w.folder(pid);item=w.media(path,mid)
        try:payload=await request.json()
        except (ValueError,UnicodeError):raise HTTPException(422,'Expected a JSON visual plan')
        attempt=path/'media'/mid/'visual-attempts'/(uuid.uuid4().hex+'.json')
        with w.LOCK:
            try:
                try:body=VisualPlan.model_validate(payload).model_dump()
                except ValidationError as exc:
                    raise HTTPException(422,exc.errors(include_url=False,include_context=False,include_input=False))
                signature=hashlib.sha256(json.dumps(body,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
                receipt=path/'media'/mid/'visual-requests'/(hashlib.sha256(body['request_id'].encode()).hexdigest()+'.json')
                if receipt.exists():
                    old=w.read(receipt)
                    if old['signature']!=signature:raise HTTPException(409,'Visual request_id reused with different content')
                    return {**w.read(path/old['relative_path']),'idempotent_replay':True}
                out=w.current_review(path,mid);review=w.read(out/'review.json');project=w.read(path/'project.json')
                if body['project_revision']!=project['revision']:raise HTTPException(409,'Project changed; refresh context')
                check_binding(body,review,out.name,item['sha256'])
                keeps=plan_keeps(review,review.get('selected_ids',[]))
                selections(review,keeps,body)
                if not body['reason'].strip():raise ValueError('Visual plan requires a reason')
                if not item.get('has_video'):raise ValueError('Visual composition requires video')
                video=inspect_video(path/item['relative_path'])
                definition=None
                if body.get('template'):
                    from editing_templates import template_snapshot,compile_plan,CompileTemplate
                    binding=body['template'];definition=template_snapshot(binding)
                    candidate={k:body[k] for k in ('request_id','project_revision','review_revision','asr_run','source_sha256','captions')}
                    candidate.update({k:binding[k] for k in ('selection_reason','frame_inspection_note','protected_regions','beats')})
                    candidate.update(template_id=binding['id'],template_version=binding['version'])
                    candidate['custom_definition']=binding.get('custom_definition')
                    candidate=CompileTemplate.model_validate(candidate).model_dump()
                    if compile_plan(candidate,review,video['width'],video['height'])!=body:
                        raise ValueError('Template operations changed; recompile the actual beats before saving')
                pid_visual=uuid.uuid4().hex;dest=path/'media'/mid/'visual-plans'/pid_visual;dest.mkdir(parents=True)
                record={'id':pid_visual,'created_at':w.now(),'request':body,'asr_run':out.name,
                    'review_revision':review.get('revision',0),'source_sha256':item['sha256'],
                    'video_width':video['width'],'video_height':video['height'],'assets':[],
                    'acceptance':'Agent-selected content; declarations are not independently verified'}
                if definition:record['template_definition']=definition
                if body['captions']['enabled']:
                    font=font_file(body['captions']['font_path']);local='font'+font.suffix.lower();shutil.copyfile(font,dest/local)
                    record['font']={'relative_path':local,'sha256':sha(dest/local)}
                for i,cue in enumerate(body['images']):
                    original=Path(cue['path'])
                    image=inspect_image(original)
                    if image['sha256']!=cue['sha256']:raise ValueError('Image SHA256 mismatch')
                    if not cue['source_note'].strip() or not cue['usage_scope'].strip():raise ValueError('Image declarations must not be blank')
                    local=f'image-{i}{original.suffix.lower()}';shutil.copy2(original,dest/local)
                    if sha(dest/local)!=cue['sha256']:raise ValueError('Image changed during import')
                    record['assets'].append({'relative_path':local,'sha256':cue['sha256'],'width':image['width'],'height':image['height'],
                        'nature':cue['nature'],'source_note':cue['source_note'],'usage_scope':cue['usage_scope'],'declaration_only':True})
                if not body['captions']['enabled'] and not body['images'] and not body['regions']:raise ValueError('Empty visual plan')
                w.write(dest/'plan.json',record)
                project.setdefault('visual_plans',[]).append({'id':pid_visual,'media_id':mid,'asr_run':out.name,'review_revision':review.get('revision',0),'relative_path':str((dest/'plan.json').relative_to(path))})
                w.snapshot(path,project);record['project_revision_after']=project['revision'];w.write(dest/'plan.json',record)
                w.write(receipt,{'signature':signature,'relative_path':str((dest/'plan.json').relative_to(path))})
                w.write(attempt,{'at':w.now(),'accepted':True,'request':payload,'plan_id':pid_visual})
                w.event(path,'visual_plan_save',{'media_id':mid,'plan_id':pid_visual})
                return record
            except (HTTPException,ValueError,OSError,subprocess.SubprocessError,StopIteration) as exc:
                error=exc if isinstance(exc,HTTPException) else HTTPException(422,str(exc))
                w.write(attempt,{'at':w.now(),'accepted':False,'request':payload,'http_status':error.status_code,'detail':error.detail})
                raise error
