"""Finite native transitions and alpha-composited source regions."""
import struct
import zlib
import numpy as np


def transition_frames(body):
    shots=body['shots'];result=[0]*(len(shots)-1);seen=set()
    if body.get('transitions') and len(shots)>32:raise ValueError('Transition timelines support at most 32 shots')
    for cue in body.get('transitions',[]):
        ids=[s['id'] for s in shots[:-1]];id=cue['after_shot_id']
        if id not in ids or id in seen or not cue['reason'].strip():raise ValueError('Transition needs a unique non-final shot and selection reason')
        n=round(cue['duration']*body['fps'])
        if n<2:raise ValueError('Transition needs at least two output frames')
        result[ids.index(id)]=n;seen.add(id)
    # Three simultaneously overlapping shots would require a different composition model.
    lengths=[round((s['source_out']-s['source_in'])*body['fps']) for s in shots]
    for i in range(1,len(shots)-1):
        if result[i-1]+result[i]>=lengths[i]:raise ValueError('Adjacent transitions must leave a non-overlapped interval in the middle shot')
    return result


def pixels(rect,width,height):
    return round(rect['x']*width),round(rect['y']*height),round(rect['width']*width),round(rect['height']*height)


def validate_masks(body,resolved,total):
    for cue in body.get('masks',[]):
        source=resolved.get(cue['source_id'])
        if not source or not source['info']['has_video']:raise ValueError('Mask needs a registered video/image source')
        info=source['info'];duration=cue['end']-cue['start']
        if duration<=0 or cue['end']>total+.0001 or not cue['reason'].strip():raise ValueError('Invalid mask output interval or missing reason')
        if info['kind']=='image' and cue['source_in']!=0:raise ValueError('Still mask source_in must be zero')
        if info['kind']!='image' and cue['source_in']+duration>info['video_duration']+.0001:raise ValueError('Mask exceeds source video duration')
        crop=pixels(cue['crop'],info['width'],info['height']);slot=pixels(cue['slot'],body['width'],body['height'])
        if min(*crop[2:],*slot[2:])<2:raise ValueError('Mask crop and destination must be at least two pixels')
        if cue['feather']>min(slot[2:])/2:raise ValueError('Feather exceeds half the mask size')


def base_graph(body,mapping):
    args=['ffmpeg','-hide_banner','-v','error','-nostdin','-n','-filter_complex_threads','1']
    if not body.get('transitions'):return args+['-f','concat','-safe','1','-i','segments.txt'],[],'0:v:0','0:a:0',1
    graph=[];fps=body['fps'];overlap=transition_frames(body)
    for i in range(len(body['shots'])):
        args+=['-i',f'segment-{i:04}.mkv']
        graph.extend([f'[{i}:v]fps={fps},settb=AVTB,setpts=PTS-STARTPTS,format=yuv444p[v{i}]',f'[{i}:a]asetpts=PTS-STARTPTS[a{i}]'])
    video,audio='v0','a0';cues={c['after_shot_id']:c for c in body['transitions']}
    for i in range(1,len(body['shots'])):
        n=overlap[i-1];v,a=f'joinedv{i}',f'joineda{i}'
        if n:
            cue=cues[body['shots'][i-1]['id']];offset=mapping['shots'][i]['output_start']
            graph.append(f'[{video}][v{i}]xfade=transition={cue["kind"]}:duration={n/fps:.8f}:offset={offset:.8f},settb=AVTB[{v}]')
            graph.append(f'[{audio}][a{i}]acrossfade=d={n/fps:.8f}:c1=tri:c2=tri[{a}]')
        else:
            graph.append(f'[{video}][v{i}]concat=n=2:v=1:a=0,settb=AVTB[{v}]')
            graph.append(f'[{audio}][a{i}]concat=n=2:v=0:a=1[{a}]')
        video,audio=v,a
    return args,graph,video,audio,len(body['shots'])


def alpha_field(width,height,shape,feather,opacity):
    y,x=np.mgrid[:height,:width];x=x+.5;y=y+.5
    if shape=='ellipse':distance=(1-np.sqrt(((x-width/2)/(width/2))**2+((y-height/2)/(height/2))**2))*min(width,height)/2
    else:distance=np.minimum.reduce([x,y,width-x,height-y])
    alpha=np.clip(distance/feather,0,1) if feather else (distance>0).astype(float)
    return np.round(alpha*opacity*255).astype('uint8')


def gray_png(path,array):
    height,width=array.shape
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,0,0,0,0))+
        chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in array)))+chunk(b'IEND',b''))


def add_masks(body,sources,dest,args,graph,last,next_input):
    fps=body['fps']
    for i,cue in enumerate(body.get('masks',[])):
        source=sources[cue['source_id']];info=source['info'];duration=cue['end']-cue['start']
        x,y,width,height=pixels(cue['slot'],body['width'],body['height']);cx,cy,cw,ch=pixels(cue['crop'],info['width'],info['height'])
        alpha=dest/f'mask-alpha-{i:04}.png';gray_png(alpha,alpha_field(width,height,cue['shape'],cue['feather'],cue['opacity']))
        source_input=next_input;mask_input=next_input+1;next_input+=2
        if info['kind']=='image':args+=['-loop','1']
        args+=['-i',str(source['path']),'-loop','1','-framerate',str(fps),'-i',alpha.name]
        graph.append(f'[{source_input}:v]trim=start={cue["source_in"]:.8f}:duration={duration:.8f},setpts=PTS-STARTPTS,crop={cw}:{ch}:{cx}:{cy},setsar=1,scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},fps={fps},format=rgba,split=2[mc{i}][ma{i}]')
        graph.append(f'[ma{i}]alphaextract[existing{i}]')
        graph.append(f'[{mask_input}:v]trim=duration={duration:.8f},setpts=PTS-STARTPTS,format=gray[shape{i}]')
        graph.append(f"[existing{i}][shape{i}]blend=all_expr='A*B/255':shortest=1[alpha{i}]")
        graph.append(f'[mc{i}][alpha{i}]alphamerge=shortest=1,setpts=PTS+{cue["start"]:.8f}/TB[masked{i}]')
        label=f'overlaymask{i}'
        graph.append(f"[{last}][masked{i}]overlay=x={x}:y={y}:eof_action=pass:repeatlast=0:enable='gte(t,{cue['start']})*lt(t,{cue['end']})'[{label}]")
        last=label
    return args,graph,last,next_input
