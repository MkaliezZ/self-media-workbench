"""Deterministic multi-source video, independent audio and reviewed music timing."""
import copy
import hashlib
import json
import math
import shutil
import subprocess
import uuid
from pathlib import Path
from fastapi import HTTPException
from timeline_models import TimelinePlan,TimelineExport,OnsetRequest
from visual_tools import probe,sha,font_file,wrapped,inspect_image


def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def run(command,directory,log,timeout=1800):
    try:
        result=subprocess.run(command,cwd=directory,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
        record={'command':command,'returncode':result.returncode,'stderr':result.stderr}
    except subprocess.TimeoutExpired:
        (directory/log).write_text(json.dumps({'command':command,'timed_out':True},indent=2),'utf-8')
        raise RuntimeError('Timeline operation timed out; partial outputs retained')
    (directory/log).write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
    if result.returncode:raise RuntimeError(result.stderr[-3000:])


def source_info(path,kind):
    if kind=='image':return {**inspect_image(Path(path).resolve()),'kind':'image','has_video':True,'has_audio':False}
    meta=probe(path);video=next((s for s in meta['streams'] if s['codec_type']=='video'),None)
    audio=next((s for s in meta['streams'] if s['codec_type']=='audio'),None)
    def duration(stream):
        try:
            value=float(stream.get('duration') or meta['format']['duration'])
            if not math.isfinite(value) or value<=0:raise ValueError('Invalid duration')
            return value
        except (ValueError,KeyError):raise ValueError('Cannot establish finite source duration')
    info={'kind':'media','has_video':video is not None,'has_audio':audio is not None}
    if video:info.update(video_duration=duration(video),width=video['width'],height=video['height'])
    if audio:info['audio_duration']=duration(audio)
    if not video and not audio:raise ValueError('No usable media stream')
    return info


def resolve_sources(w,path,body):
    project=w.read(path/'project.json');resolved={}
    for ref in body['sources']:
        if ref['kind']=='media':
            item=w.media(path,ref['asset_id']);file=path/item['relative_path']
        else:
            item=next((a for a in project.get('image_assets',[]) if a['id']==ref['asset_id']),None)
            if not item:raise ValueError('Unknown registered image asset')
            file=Path(item['path'])
        if not file.resolve().is_relative_to(path.resolve()):raise ValueError('Asset must belong to this project')
        if ref['sha256']!=item['sha256'] or sha(file)!=ref['sha256']:raise HTTPException(409,'Timeline source changed; inspect the original')
        resolved[ref['id']]={'path':file,'item':copy.deepcopy(item),'info':source_info(file,ref['kind'])}
    return resolved


def timeline_map(body,resolved,check_grid=True):
    entries=[];frame=0;fps=body['fps'];sources=set()
    from timeline_fx import transition_frames,validate_masks
    overlap=transition_frames(body)
    for index,shot in enumerate(body['shots']):
        source=resolved.get(shot['source_id'])
        if not source or not source['info']['has_video']:raise ValueError('Each shot requires a registered video/image source')
        info=source['info'];a,b=shot['source_in'],shot['source_out']
        if a>=b or not shot['reason'].strip() or not shot['role'].strip():raise ValueError('Invalid shot interval or missing selection reason')
        if info['kind']=='image' and a!=0:raise ValueError('Still-image source_in must be zero')
        if info['kind']!='image' and b>info['video_duration']+.0001:raise ValueError('Shot exceeds actual source video duration')
        frames=round((b-a)*fps)
        if frames<1:raise ValueError('Shot is shorter than one output frame')
        frame-=overlap[index-1] if index else 0
        entries.append({**shot,'output_start':frame/fps,'output_end':(frame+frames)/fps,
            'start_frame':frame,'end_frame':frame+frames,'frames':frames,
            'quantization_seconds':frames/fps-(b-a),'generated_silence':not info['has_audio']})
        frame+=frames;sources.add(shot['source_id'])
    total=frame/fps
    if total>3600:raise ValueError('Timeline v1 is limited to one hour')
    for bed in body['audio']:
        source=resolved.get(bed['source_id'])
        if not source or not source['info']['has_audio']:raise ValueError('Audio bed requires a source with an actual audio stream')
        if bed['source_in']+bed['duration']>source['info']['audio_duration']+.0001:raise ValueError('Audio bed exceeds source audio duration')
        if bed['start']+bed['duration']>total+.0001:raise ValueError('Audio bed exceeds output duration')
        if bed['fade_in']+bed['fade_out']>bed['duration'] or not bed['reason'].strip():raise ValueError('Invalid audio fade or missing reason')
        sources.add(bed['source_id'])
    for title in body['titles']:
        if title['start']>=title['end'] or title['end']>total+.0001 or not title['text'].strip():raise ValueError('Invalid title interval/text')
    for cue in body.get('masks',[]):sources.add(cue['source_id'])
    validate_masks(body,resolved,total)
    if body.get('effects'):
        from motion_tools import validate_effects
        sources.update(validate_effects(body,resolved,total))
    if sources!=set(resolved):raise ValueError('Unused registered source in timeline; remove it or describe an actual use')
    for i,n in enumerate(overlap):
        if n and (n>=entries[i]['frames'] or n>=entries[i+1]['frames']):raise ValueError('Transition must be shorter than both adjacent shots')
    errors=[];grid=body['music_grid']
    if grid:
        times=grid['source_times']
        if len(times)!=len(entries)+1 or any(not math.isfinite(t) or t<0 for t in times) or any(b<=a for a,b in zip(times,times[1:])):
            raise ValueError('Reviewed music grid must give increasing source times for every shot edge')
        beds=[b for b in body['audio'] if b['source_id']==grid['source_id'] and b['role']=='music']
        if len(beds)!=1 or not grid['reason'].strip():raise ValueError('Music grid requires exactly one matching music bed and a review reason')
        bed=beds[0]
        if times[0]<bed['source_in']-.0001 or times[-1]>bed['source_in']+bed['duration']+.0001:
            raise ValueError('Grid lies outside the selected music interval')
        actual=[0.]+[(e['end_frame']-(overlap[i]/2 if i<len(overlap) else 0))/fps for i,e in enumerate(entries)]
        for edge,(t,observed) in enumerate(zip(times,actual)):
            target=bed['start']+t-bed['source_in'];error=observed-target
            errors.append({'edge':edge,'source_time':t,'target':target,'actual':observed,'error_seconds':error})
            if check_grid and abs(error)>grid['max_error_frames']/fps+1e-6:raise ValueError('Shot edges miss the reviewed music grid; align the draft first')
    result={'shots':entries,'duration':total,'frames':frame,'fps':fps,'audio':body['audio'],
        'titles':body['titles'],'beat_alignment':errors,'timing_scope':'source seconds mapped to output frames; no ASR or invented spoken alignment'}
    if body.get('transitions'):
        result['transitions']=[{**t,'frames':round(t['duration']*fps),
            'output_start':entries[next(i for i,s in enumerate(entries) if s['id']==t['after_shot_id'])]['output_end']-round(t['duration']*fps)/fps,
            'output_end':entries[next(i for i,s in enumerate(entries) if s['id']==t['after_shot_id'])]['output_end']} for t in body['transitions']]
    if body.get('masks'):result['masks']=body['masks']
    if body.get('effects'):result['effects']=body['effects']
    return result


def align(body,resolved):
    result=copy.deepcopy(body);grid=result['music_grid']
    if not grid:raise ValueError('Alignment requires a reviewed music grid')
    times=grid['source_times']
    if len(times)!=len(body['shots'])+1 or any(not math.isfinite(t) for t in times):raise ValueError('One grid time is required per shot edge')
    beds=[b for b in body['audio'] if b['source_id']==grid['source_id'] and b['role']=='music']
    if len(beds)!=1:raise ValueError('Select exactly one matching music bed')
    bed=beds[0];targets=[round((bed['start']+t-bed['source_in'])*body['fps']) for t in times]
    if targets[0]!=0 or any(b<=a for a,b in zip(targets,targets[1:])):raise ValueError('Music grid must start the timeline and have increasing frame edges')
    changes=[]
    from timeline_fx import transition_frames
    overlap=transition_frames(body);start_frame=0
    for i,shot in enumerate(result['shots']):
        end_frame=round(targets[i+1]+(overlap[i]/2 if i<len(overlap) else 0))
        end=shot['source_in']+(end_frame-start_frame)/body['fps']
        if end>shot['source_out']+1e-6:raise ValueError('Alignment needs footage outside the approved shot window; select a longer source interval')
        changes.append({'shot_id':shot['id'],'old_source_out':shot['source_out'],'new_source_out':end})
        shot['source_out']=end
        start_frame=end_frame-(overlap[i] if i<len(overlap) else 0)
    result=TimelinePlan.model_validate(result).model_dump()
    return {'plan':result,'changes':changes,'map':timeline_map(result,resolved),'status':'draft_not_saved'}


def integrity(record,directory):
    body=TimelinePlan.model_validate(record['request']).model_dump()
    if digest(record['request'])!=record['request_sha256']:raise ValueError('Timeline request integrity mismatch')
    sources={}
    for source in record['sources']:
        file=directory/source['relative_path']
        if not file.resolve().is_relative_to(directory.resolve()) or sha(file)!=source['sha256']:raise ValueError('Frozen timeline source integrity mismatch')
        sources[source['id']]={'path':file,'info':source['info'],'item':source['metadata']}
    expected={r['id']:r['sha256'] for r in body['sources']}
    if expected!={s['id']:s['sha256'] for s in record['sources']}:raise ValueError('Frozen source manifest mismatch')
    if digest(timeline_map(body,sources))!=digest(record['map']):raise ValueError('Timeline mapping integrity mismatch')
    if (body['titles'] or any(c['kind']=='motion_text' for c in body.get('effects',[]))) and sha(directory/record['font']['relative_path'])!=record['font']['sha256']:raise ValueError('Timeline font integrity mismatch')
    if any(c['kind']=='motion_text' for c in body.get('effects',[])):
        from motion_tools import preflight_text
        preflight_text(body,directory/record['font']['relative_path'])
    return sources


def render(record,plan_dir,dest):
    sources=integrity(record,plan_dir);body=record['request'];mapping=record['map'];width,height,fps=body['width'],body['height'],body['fps']
    dest.mkdir(parents=True,exist_ok=True)
    for i,shot in enumerate(mapping['shots']):
        source=sources[shot['source_id']];duration=shot['frames']/fps
        args=['ffmpeg','-hide_banner','-v','error','-nostdin','-n']
        if source['info']['kind']=='image':args+=['-loop','1']
        args+=['-i',str(source['path'])]
        if not source['info']['has_audio']:args+=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
        fit=(f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x16181A'
             if shot['fit']=='contain' else f'scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}')
        graph=[f"[0:v]trim=start={shot['source_in']:.8f}:end={shot['source_out']:.8f},setpts=PTS-STARTPTS,scale=trunc(iw*sar/2)*2:ih,setsar=1,{fit},setsar=1,fps={fps},tpad=stop_mode=clone:stop_duration=1,trim=end_frame={shot['frames']},setpts=N/({fps}*TB),format=yuv420p[v]"]
        audio='0:a:0' if source['info']['has_audio'] else '1:a:0'
        start=shot['source_in'] if source['info']['has_audio'] else 0
        graph.append(f'[{audio}]atrim=start={start:.8f}:duration={duration:.8f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={shot["source_audio_gain"]},apad,atrim=duration={duration:.8f},asetpts=N/SR/TB[a]')
        script=dest/f'segment-{i:04}.filters';script.write_text(';\n'.join(graph),'utf-8')
        args+=['-/filter_complex',script.name,'-map','[v]','-map','[a]',
            '-r',str(fps),'-fps_mode','cfr','-enc_time_base:v',f'1:{fps}',
            '-c:v','libx264','-preset','fast','-crf','18','-bf','0','-pix_fmt','yuv420p','-c:a','pcm_s16le',f'segment-{i:04}.mkv']
        run(args,dest,f'segment-{i:04}.process.json')
    (dest/'segments.txt').write_text('\n'.join(f"file 'segment-{i:04}.mkv'\nduration {shot['frames']/fps:.8f}" for i,shot in enumerate(mapping['shots'])),'utf-8')
    from timeline_fx import base_graph,add_masks
    args,graph,base_video,base_audio,next_input=base_graph(body,mapping)
    graph.append(f"[{base_audio}]apad,atrim=duration={mapping['duration']:.8f},asetpts=N/SR/TB[original]")
    audio_labels=['[original]']
    for i,bed in enumerate(body['audio'],1):
        args+=['-i',str(sources[bed['source_id']]['path'])]
        input_index=next_input;next_input+=1
        expr=f"[{input_index}:a:0]atrim=start={bed['source_in']:.8f}:duration={bed['duration']:.8f},asetpts=PTS-STARTPTS,aresample=48000,aformat=channel_layouts=stereo,volume={bed['gain']}"
        if bed['fade_in']:expr+=f",afade=t=in:st=0:d={bed['fade_in']}"
        if bed['fade_out']:expr+=f",afade=t=out:st={bed['duration']-bed['fade_out']}:d={bed['fade_out']}"
        expr+=f",adelay={round(bed['start']*1000)}:all=1[b{i}]";graph.append(expr);audio_labels.append(f'[b{i}]')
    graph.append(''.join(audio_labels)+f"amix=inputs={len(audio_labels)}:duration=first:normalize=0:dropout_transition=0,alimiter=limit=0.95:level=0:latency=1,atrim=duration={mapping['duration']:.8f}[aout]")
    graph.append(f"[{base_video}]fps={fps},tpad=stop_mode=clone:stop_duration=1,trim=end_frame={mapping['frames']},setpts=N/({fps}*TB)[clocked]")
    last='clocked'
    args,graph,last,next_input=add_masks(body,sources,dest,args,graph,last,next_input)
    from motion_tools import add_effects
    motion_font=plan_dir/record['font']['relative_path'] if record.get('font') else None
    args,graph,last,next_input=add_effects(body,mapping,sources,dest,motion_font,args,graph,last,next_input)
    if body['titles']:
        font=plan_dir/record['font']['relative_path'];local='title-font'+font.suffix;shutil.copyfile(font,dest/local)
        for i,cue in enumerate(body['titles']):
            size=max(12,round(height*cue['font_height']));file=f'title-{i:04}.txt'
            (dest/file).write_text(wrapped(cue['text'],max(4,int(width*.88/size)*2)),'utf-8')
            label=f'title{i}'
            first=math.ceil(cue['start']*fps-1e-7);end=math.ceil(cue['end']*fps-1e-7)
            graph.append(f"[{last}]drawtext=fontfile={local}:textfile={file}:expansion=none:fontsize={size}:fontcolor=0x{cue['colour']}:box=1:boxcolor=black@0.5:boxborderw=4:x=(w-text_w)/2:y=h-text_h-{round(height*cue['bottom_margin'])}:enable='gte(n,{first})*lt(n,{end})'[{label}]");last=label
    script=dest/'timeline.filters';script.write_text(';\n'.join(graph),'utf-8')
    args+=['-/filter_complex',script.name,'-map',f'[{last}]','-map','[aout]',
        '-r',str(fps),'-fps_mode','cfr','-enc_time_base:v',f'1:{fps}',
        '-c:v','libx264','-preset','medium','-crf','18',
        '-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart','timeline.mp4']
    run(args,dest,'timeline-render-process.json')
    actual=probe(dest/'timeline.mp4',count_frames=True)
    video=next(s for s in actual['streams'] if s['codec_type']=='video')
    audio=next(s for s in actual['streams'] if s['codec_type']=='audio')
    verification={'expected_frames':mapping['frames'],'actual_frames':int(video.get('nb_read_frames',0)),
        'expected_duration':mapping['duration'],'actual_video_duration':float(video['duration']),
        'actual_audio_duration':float(audio['duration']),'actual_width':video['width'],'actual_height':video['height']}
    (dest/'timeline-verification.json').write_text(json.dumps(verification,indent=2),'utf-8')
    if (verification['actual_frames']!=mapping['frames'] or video['width']!=width or video['height']!=height
        or abs(verification['actual_video_duration']-mapping['duration'])>1/fps+.001
        or abs(verification['actual_audio_duration']-mapping['duration'])>1/fps+.025):
        raise RuntimeError('Actual timeline frames/duration differ from the saved map: '+json.dumps(verification))
    return {'primary_video':'timeline.mp4','files':['timeline.mp4','timeline-plan.json','timeline-map.json','timeline-verification.json','provenance.json']+(['motion-events.json'] if body.get('effects') else [])}


def onsets(file,start,end):
    import numpy as np
    command=['ffmpeg','-v','error','-nostdin','-ss',str(start),'-i',str(file),'-t',str(end-start),'-vn','-ac','1','-ar','11025','-f','f32le','-']
    result=subprocess.run(command,capture_output=True,timeout=120)
    if result.returncode:raise ValueError('Audio analysis decode failed')
    audio=np.frombuffer(result.stdout,dtype='<f4');window=512;hop=128
    if len(audio)<window:return []
    frames=np.lib.stride_tricks.sliding_window_view(audio,window)[::hop]
    spectrum=np.abs(np.fft.rfft(frames*np.hanning(window),axis=1));flux=np.maximum(np.diff(spectrum,axis=0),0).sum(axis=1)
    if not len(flux) or flux.max()<1e-5:return []
    threshold=max(float(np.median(flux)+3*np.median(np.abs(flux-np.median(flux)))),float(flux.max()*.08))
    candidates=[]
    for i in range(1,len(flux)-1):
        if flux[i]>threshold and flux[i]>=flux[i-1] and flux[i]>flux[i+1]:
            t=start+((i+1)*hop+window/2)/11025
            if not candidates or t-candidates[-1]['source_time']>.12:
                candidates.append({'source_time':round(t,6),'relative_strength':round(float(flux[i]/flux.max()),4)})
    return candidates


def register(w):
    @w.app.post('/api/projects/{pid}/timeline/align')
    def align_api(pid:str,request:TimelinePlan):
        try:
            body=request.model_dump();return align(body,resolve_sources(w,w.folder(pid),body))
        except (ValueError,OSError) as exc:raise HTTPException(422,str(exc))

    @w.app.post('/api/projects/{pid}/music-onsets')
    def onset_api(pid:str,request:OnsetRequest):
        path=w.folder(pid);item=w.media(path,request.media_id);file=path/item['relative_path']
        try:
            if sha(file)!=request.source_sha256 or item['sha256']!=request.source_sha256:raise HTTPException(409,'Audio source changed')
            info=source_info(file,'media')
            if not info['has_audio'] or request.source_in>=request.source_out or request.source_out>info['audio_duration']+.0001 or request.source_out-request.source_in>300:
                raise ValueError('Analyze an existing audio interval of at most 300 seconds')
            result={'id':uuid.uuid4().hex,'request':request.model_dump(),'candidates':onsets(file,request.source_in,request.source_out),
                'scope':'spectral-flux onset candidates; not verified musical beats or BPM. Calling Agent reviews selection.'}
            w.write(path/'audio-analysis'/result['id']/'result.json',result);return result
        except (ValueError,OSError,subprocess.SubprocessError) as exc:raise HTTPException(422,str(exc))

    @w.app.get('/api/projects/{pid}/timeline-plans')
    def list_plans(pid:str):return [w.read(p) for p in sorted((w.folder(pid)/'timeline-plans').glob('*/plan.json'))]

    @w.app.post('/api/projects/{pid}/timeline-plans')
    def save(pid:str,request:TimelinePlan):
        path=w.folder(pid);body=request.model_dump();attempt=path/'timeline-attempts'/(uuid.uuid4().hex+'.json')
        with w.LOCK:
            try:
                receipt=path/'timeline-requests'/(body['request_id']+'.json');signature=digest(body)
                if receipt.exists():
                    old=w.read(receipt)
                    saved=w.read(path/'timeline-plans'/old['id']/'plan.json')
                    if digest(saved['request'])!=saved['request_sha256']:raise HTTPException(409,'Timeline saved request integrity mismatch')
                    if old['signature']!=signature and TimelinePlan.model_validate(saved['request']).model_dump()!=body:
                        raise HTTPException(409,'Timeline request_id reused with changed content')
                    return {**saved,'idempotent_replay':True}
                project=w.read(path/'project.json')
                if body['project_revision']!=project['revision'] or body['supersedes']!=project.get('timeline_head'):
                    raise HTTPException(409,'Project/head changed; refresh context and reconsider')
                from editing_logics import LOGICS
                if body['recipe'] and body['logic_id'] not in (None,body['recipe']['id']):raise ValueError('Custom recipe and logic_id must describe the same recipe')
                if body['logic_id'] and not body['recipe'] and body['logic_id'] not in {v['id'] for v in LOGICS}:raise ValueError('Unknown logic_id; discover editing_logics or supply a custom native recipe')
                resolved=resolve_sources(w,path,body);mapping=timeline_map(body,resolved)
                id=uuid.uuid4().hex;dest=path/'timeline-plans'/id;dest.mkdir(parents=True)
                record={'id':id,'created_at':w.now(),'request':body,'request_sha256':signature,'map':mapping,'sources':[],
                    'scope':'Agent-selected visual/audio source intervals; no claim of ASR alignment or semantic verification'}
                for i,ref in enumerate(body['sources']):
                    source=resolved[ref['id']];local=f'source-{i:03}{source["path"].suffix.lower()}'
                    shutil.copyfile(source['path'],dest/local)
                    if sha(dest/local)!=ref['sha256']:raise ValueError('Source changed while freezing timeline')
                    record['sources'].append({**ref,'relative_path':local,'info':source['info'],'metadata':source['item']})
                if body['titles'] or any(c['kind']=='motion_text' for c in body.get('effects',[])):
                    font=font_file(body['font_path']);local='font'+font.suffix.lower();shutil.copyfile(font,dest/local)
                    record['font']={'relative_path':local,'sha256':sha(dest/local)}
                    from motion_tools import preflight_text
                    preflight_text(body,dest/local)
                w.write(dest/'plan.json',record)
                project.setdefault('timeline_plans',[]).append({'id':id,'relative_path':str((dest/'plan.json').relative_to(path))})
                project['timeline_head']=id;w.snapshot(path,project)
                w.write(receipt,{'id':id,'signature':signature});w.write(attempt,{'accepted':True,'request':body,'plan_id':id,'at':w.now()})
                w.event(path,'timeline_plan_save',{'plan_id':id});return record
            except (ValueError,OSError,HTTPException,subprocess.SubprocessError) as exc:
                error=exc if isinstance(exc,HTTPException) else HTTPException(422,str(exc))
                w.write(attempt,{'accepted':False,'request':body,'detail':error.detail,'at':w.now()});raise error

    @w.app.post('/api/projects/{pid}/timeline/export')
    def export(pid:str,request:TimelineExport):
        path=w.folder(pid);plan_dir=path/'timeline-plans'/request.plan_id
        if not (plan_dir/'plan.json').is_file():raise HTTPException(404,'Timeline plan not found')
        record=w.read(plan_dir/'plan.json')
        try:integrity(record,plan_dir)
        except (ValueError,OSError,KeyError) as exc:raise HTTPException(409,str(exc))
        eid=uuid.uuid4().hex;dest=path/'exports'/eid
        w.write(dest/'timeline-plan.json',record);w.write(dest/'timeline-map.json',record['map'])
        def worker():
            result=render(record,plan_dir,dest)
            w.write(dest/'provenance.json',{'timeline_plan_id':record['id'],'created_at':w.now(),'external_publication':False,
                'sources':[{'id':s['id'],'sha256':s['sha256'],'metadata':s['metadata']} for s in record['sources']],
                'timing_scope':record['map']['timing_scope']})
            return {'export_id':eid,'timeline_plan_id':record['id'],**result}
        return w.launch(path,None,'timeline_export',worker)
