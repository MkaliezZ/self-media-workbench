"""Deterministic RGBA motion compositor driven by saved source-bound plans."""
import json,math,subprocess
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter,ImageChops,ImageOps
from timeline_fx import alpha_field


def clamp(v):return max(0.,min(1.,v))
def ease(v,kind='smoothstep'):
    v=clamp(v);return 1-(1-v)**3 if kind=='ease_out_cubic' else v*v*(3-2*v)
def box(r,w,h):return (round(r['x']*w),round(r['y']*h),round((r['x']+r['width'])*w),round((r['y']+r['height'])*h))
def interpolate(a,b,p):return {k:a[k]+(b[k]-a[k])*p for k in a}
def quad_rect(r,w,h):
    x,y,x2,y2=box(r,w,h);return np.array([[x,y],[x2,y],[x2,y2],[x,y2]],float)
def homography(a,b):
    rows=[];values=[]
    for (x,y),(u,v) in zip(a,b):
        rows.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]]);values.extend([u,v])
    return np.append(np.linalg.solve(np.array(rows,float),np.array(values,float)),1).reshape(3,3)
def mapped(points,h):
    p=np.c_[points,np.ones(len(points))]@h.T;return p[:,:2]/p[:,2:]
def warp(image,quad,canvas,shadow=0.):
    w,h=canvas.size;lo=np.floor(quad.min(axis=0)).astype(int);hi=np.ceil(quad.max(axis=0)).astype(int)
    x,y=max(0,lo[0]),max(0,lo[1]);x2,y2=min(w,hi[0]),min(h,hi[1])
    if x>=x2 or y>=y2:return
    if shadow:
        layer=Image.new('RGBA',(w,h));d=ImageDraw.Draw(layer);d.polygon([tuple(p+[5,9]) for p in quad],fill=(0,0,0,round(80*shadow)))
        canvas.alpha_composite(layer.filter(ImageFilter.GaussianBlur(9)))
    local=quad-[x,y];iw,ih=image.size;inverse=homography(local,np.array([[0,0],[iw,0],[iw,ih],[0,ih]],float))
    piece=image.transform((x2-x,y2-y),Image.Transform.PERSPECTIVE,tuple(inverse.flat)[:8],Image.Resampling.BICUBIC)
    canvas.alpha_composite(piece,(x,y))
def dim(canvas,amount):
    if amount:canvas.alpha_composite(Image.new('RGBA',canvas.size,(0,0,0,round(255*clamp(amount)))))
def colour(s):return tuple(bytes.fromhex(s))
def fit_rect(image,slot,w,h):
    x,y,x2,y2=box(slot,w,h);scale=min((x2-x)/image.width,(y2-y)/image.height);iw=image.width*scale;ih=image.height*scale
    return np.array([[x+(x2-x-iw)/2,y+(y2-y-ih)/2],[x+(x2-x+iw)/2,y+(y2-y-ih)/2],
        [x+(x2-x+iw)/2,y+(y2-y+ih)/2],[x+(x2-x-iw)/2,y+(y2-y+ih)/2]],float)


def validate_effects(body,resolved,total):
    effects=body.get('effects',[]);used=set();w,h=body['width'],body['height']
    if effects and (total>300 or w*h>1920*1920):raise ValueError('Motion compositor limit: 300 seconds and canvas area at most 1920x1920')
    for cue in effects:
        duration=cue['end']-cue['start']
        if duration<=0 or cue['end']>total+1e-6 or not cue['reason'].strip():raise ValueError('Invalid motion interval/reason')
        kind=cue['kind']
        if kind in ('document_extract','motion_layer','track_matte'):
            id=cue['source_id'];s=resolved.get(id)
            if not s or not s['info']['has_video']:raise ValueError('Motion needs an actual registered image/video source')
            info=s['info'];used.add(id);crop=cue['source_rect'] if kind=='document_extract' else cue['crop']
            x,y,x2,y2=box(crop,info['width'],info['height'])
            if min(x2-x,y2-y)<2:raise ValueError('Motion source region is smaller than two pixels')
            if kind=='document_extract':
                if info['kind']!='image':raise ValueError('Document extraction needs a registered still image')
                if duration<sum(cue[k] for k in ['reveal_seconds','highlight_seconds','lift_seconds','return_seconds'])+.1:raise ValueError('Document stages leave no readable hold')
                q=np.array([[p['x'],p['y']] for p in cue['page_quad']]);edges=np.roll(q,-1,axis=0)-q
                crosses=np.array([np.linalg.det(np.array([edges[i],edges[(i+1)%4]])) for i in range(4)])
                ordered=q[0,0]<q[1,0] and q[3,0]<q[2,0] and q[0,1]<q[3,1] and q[1,1]<q[2,1]
                if not np.all(crosses>1e-5) or not ordered:raise ValueError('Page quad must be convex and ordered upright TL/TR/BR/BL, without mirrored or inverted corners')
                for r in cue['highlights']:
                    if r['x']<crop['x']-1e-6 or r['y']<crop['y']-1e-6 or r['x']+r['width']>crop['x']+crop['width']+1e-6 or r['y']+r['height']>crop['y']+crop['height']+1e-6:raise ValueError('Highlight must lie inside the selected source region')
            else:
                if duration<cue['enter_seconds']+cue['exit_seconds']+.1:raise ValueError('Layer animation leaves no hold')
                if info['kind']=='image' and cue['source_in']!=0:raise ValueError('Still motion source_in must be zero')
                if info['kind']!='image' and cue['source_in']+duration>info['video_duration']+.0001:raise ValueError('Motion exceeds actual source duration')
                if cue['feather']>min(cue[k][d]*size for k in ('from_rect','to_rect') for d,size in [('width',w),('height',h)])/2:raise ValueError('Motion feather exceeds the smallest destination half-size')
                if kind=='track_matte':
                    matte=resolved.get(cue['matte_id'])
                    if not matte or matte['info']['kind']!='image':raise ValueError('Track matte needs an actual registered still image')
                    used.add(cue['matte_id'])
                    with Image.open(matte['path']) as image:
                        if cue['matte_mode']=='alpha' and 'A' not in image.getbands() and 'transparency' not in image.info:raise ValueError('Alpha matte image has no alpha channel; use an alpha PNG or explicit luma mode')
        elif kind=='motion_text':
            if cue['accent'] and cue['accent'] not in cue['text']:raise ValueError('Text accent must appear in the actual text')
            if duration<cue['enter_seconds']+cue['exit_seconds']+.1:raise ValueError('Text animation leaves no hold')
        elif cue['fade_seconds']*2>duration:raise ValueError('Spotlight fades exceed interval')
    return used


class Video:
    def __init__(self,source,cue,fps,dest,index):
        info=source['info'];scale=min(1.,1280/max(info['width'],info['height']));self.w=max(2,round(info['width']*scale)//2*2);self.h=max(2,round(info['height']*scale)//2*2)
        self.log=(dest/f'motion-source-{index:02}.stderr').open('wb');self.report=dest/f'motion-source-{index:02}.process.json';self.frames=0
        count=math.ceil(cue['end']*fps-1e-7)-math.ceil(cue['start']*fps-1e-7)
        args=['ffmpeg','-v','error','-nostdin','-ss',str(cue['source_in']),'-i',str(source['path']),'-t',str(cue['end']-cue['start']+1/fps),
              '-vf',f'fps={fps},scale={self.w}:{self.h},setsar=1','-frames:v',str(count),'-pix_fmt','rgba','-f','rawvideo','pipe:1']
        self.process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=self.log);self.args=args
    def next(self):
        needed=self.w*self.h*4;parts=[];length=0
        while length<needed:
            part=self.process.stdout.read(needed-length)
            if not part:raise RuntimeError('Motion video source ended before the approved interval')
            parts.append(part);length+=len(part)
        self.frames+=1;return Image.frombytes('RGBA',(self.w,self.h),b''.join(parts))
    def close(self):
        self.process.stdout.close()
        try:self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait()
        self.log.close()
        self.report.write_text(json.dumps({'command':self.args,'decoded_frames':self.frames,'returncode':self.process.returncode},indent=2),'utf-8')


def highlighted(page,cue,progress):
    result=page.copy();count=len(cue['highlights'])
    for i,r in enumerate(cue['highlights']):
        amount=clamp(progress*count-i)
        if amount<=0:continue
        x,y,x2,y2=box(r,*page.size);x2=x+max(1,round((x2-x)*amount));area=page.crop((x,y,x2,y2));rgb=ImageChops.multiply(area.convert('RGB'),Image.new('RGB',area.size,colour(cue['colour'])))
        rgb.putalpha(area.getchannel('A'));result.paste(rgb,(x,y))
    return result


def text_layer(cue,w,h,font_path):
    x,y,x2,y2=box(cue['slot'],w,h);im=Image.new('RGBA',(x2-x,y2-y));d=ImageDraw.Draw(im);f=ImageFont.truetype(str(font_path),round(cue['font_height']*h));lines=cue['text'].split('\n');line_h=round(cue['font_height']*h*1.35);top=(im.height-line_h*len(lines))/2
    bounds=[d.textbbox((0,top+row*line_h),line,font=f) for row,line in enumerate(lines) if line]
    if bounds and (min(b[1] for b in bounds)<0 or max(b[3] for b in bounds)>im.height):raise ValueError('Motion text exceeds its slot vertically; enlarge the slot, split the cue or reduce font height')
    accent_at=cue['text'].find(cue['accent']) if cue['accent'] else -1;offset=0
    for row,line in enumerate(lines):
        if d.textlength(line,font=f)>im.width:raise ValueError('Motion text exceeds its slot; split lines or reduce font height')
        left=(im.width-d.textlength(line,font=f))/2
        for j,ch in enumerate(line):
            c=cue['accent_colour'] if accent_at>=0 and accent_at<=offset+j<accent_at+len(cue['accent']) else cue['colour'];d.text((left,top+row*line_h),ch,font=f,fill=colour(c)+(255,));left+=d.textlength(ch,font=f)
        offset+=len(line)+1
    return im


def preflight_text(body,font_path):
    for cue in body.get('effects',[]):
        if cue['kind']=='motion_text':text_layer(cue,body['width'],body['height'],font_path)


def render_layer(body,sources,dest,font_path=None):
    w,h,fps=body['width'],body['height'],body['fps']
    # The saved map, rather than a fresh float-duration sum, defines this clock.
    frames=body['_motion_frames'];effects=body.get('effects',[]);cache={};readers={};events=[]
    for i,cue in enumerate(effects):
        k=cue['kind'];entry={'kind':k,'start_frame':math.ceil(cue['start']*fps-1e-7),'end_frame':math.ceil(cue['end']*fps-1e-7),'request':cue}
        if k in ('document_extract','motion_layer','track_matte'):
            source=sources[cue['source_id']]
            if source['info']['kind']=='image':cache[i]=Image.open(source['path']).convert('RGBA')
        if k=='track_matte':
            image=Image.open(sources[cue['matte_id']]['path']).convert('RGBA')
            mask=image.getchannel('A') if cue['matte_mode']=='alpha' else ImageChops.multiply(image.convert('L'),image.getchannel('A'))
            cache[('matte',i)]=ImageChops.invert(mask) if cue['invert'] else mask
        if k=='document_extract':
            page=cache[i];hi=highlighted(page,cue,1.);q=np.array([[p['x']*w,p['y']*h] for p in cue['page_quad']]);crop=hi.crop(box(cue['source_rect'],*hi.size))
            source_h=homography(np.array([[0,0],[page.width,0],[page.width,page.height],[0,page.height]],float),q)
            selected=mapped(quad_rect(cue['source_rect'],*page.size),source_h);target=fit_rect(crop,cue['target_rect'],w,h)
            cache[('doc',i)]=(page,hi,crop,q,selected,target);crop.save(dest/f'document-crop-{i:02}.png')
            entry.update(source_quad=selected.tolist(),target_quad=target.tolist(),quote_verification='caller-reviewed text; actual selected pixels preserved, no OCR claim')
        if k=='motion_text':
            cache[i]=text_layer(cue,w,h,font_path)
        events.append(entry)
    write={'clock':'authored output frames; no automatic OCR, tracking or acoustic character alignment','events':events,'frames':frames,'fps':fps}
    (dest/'motion-events.json').write_text(json.dumps(write,ensure_ascii=False,indent=2),'utf-8')
    args=['ffmpeg','-v','error','-nostdin','-n','-f','rawvideo','-pix_fmt','rgba','-s',f'{w}x{h}','-r',str(fps),'-i','pipe:0','-an','-c:v','qtrle','-pix_fmt','argb','motion-layer.mov']
    error=(dest/'motion-render.stderr').open('wb');encoder=subprocess.Popen(args,cwd=dest,stdin=subprocess.PIPE,stderr=error)
    try:
        for n in range(frames):
            t=n/fps;canvas=Image.new('RGBA',(w,h))
            for i,cue in enumerate(effects):
                if not cue['start']<=t<cue['end']:
                    if t>=cue['end'] and i in readers:readers.pop(i).close()
                    continue
                a=t-cue['start'];duration=cue['end']-cue['start'];k=cue['kind']
                if k=='document_extract':
                    page,hi,crop,q,selected,target=cache[('doc',i)];hp=clamp((a-cue['reveal_seconds'])/cue['highlight_seconds'])
                    shown=page if hp==0 else hi if hp==1 else highlighted(page,cue,hp);warp(shown,q,canvas)
                    lifted=cue['reveal_seconds']+cue['highlight_seconds'];back=duration-cue['return_seconds']
                    p=ease((a-lifted)/cue['lift_seconds']) if a<back else 1-ease((a-back)/cue['return_seconds'])
                    if p>0:dim(canvas,cue['dim']*p);warp(crop,selected+(target-selected)*p,canvas,p)
                elif k=='spotlight':
                    p=ease(a/duration);r=interpolate(cue['from_rect'],cue['to_rect'],p);gate=min(clamp(a/cue['fade_seconds']),clamp((duration-a)/cue['fade_seconds']))
                    mask=Image.new('L',(w,h),255);d=ImageDraw.Draw(mask);d.ellipse(box(r,w,h),fill=0) if cue['shape']=='ellipse' else d.rounded_rectangle(box(r,w,h),radius=12,fill=0)
                    if cue['feather']:mask=mask.filter(ImageFilter.GaussianBlur(cue['feather']))
                    mask=mask.point(lambda v:round(v*cue['dim']*gate));layer=Image.new('RGBA',(w,h));layer.putalpha(mask);canvas.alpha_composite(layer)
                    ImageDraw.Draw(canvas).rectangle(box(r,w,h),outline=colour(cue['colour'])+(round(210*gate),),width=2)
                else:
                    enter=cue['enter_seconds'];exit=cue['exit_seconds'];p=ease(a/enter,cue.get('easing','smoothstep'));opacity=min(clamp(a/enter),clamp((duration-a)/exit) if exit else 1.)
                    if k=='motion_text':
                        im=cache[i];r=cue['slot'];x,y,x2,y2=box(r,w,h)
                        if cue['animation']=='slide_up':y+=round((1-p)*h*.10)
                        elif cue['animation']=='pop':
                            scale=.65+.35*p;im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS);x+=(x2-x-im.width)//2;y+=(y2-y-im.height)//2
                        im=im.copy();im.putalpha(im.getchannel('A').point(lambda v:round(v*opacity)));canvas.alpha_composite(im,(x,y));continue
                    source=sources[cue['source_id']]
                    if i not in cache:
                        if i not in readers:readers[i]=Video(source,cue,fps,dest,i)
                        im=readers[i].next()
                    else:im=cache[i]
                    im=im.crop(box(cue['crop'],*im.size));r=interpolate(cue['from_rect'],cue['to_rect'],p);x,y,x2,y2=box(r,w,h)
                    if cue['animation']=='pop':
                        scale=.65+.35*p;cx=(x+x2)/2;cy=(y+y2)/2;half_w=(x2-x)*scale/2;half_h=(y2-y)*scale/2
                        x,y,x2,y2=round(cx-half_w),round(cy-half_h),round(cx+half_w),round(cy+half_h)
                    iw=max(2,x2-x);ih=max(2,y2-y)
                    im=ImageOps.fit(im,(iw,ih),method=Image.Resampling.LANCZOS) if k=='track_matte' else im.resize((iw,ih),Image.Resampling.LANCZOS)
                    alpha=Image.fromarray(alpha_field(iw,ih,cue['shape'],cue['feather'],cue['opacity']*opacity))
                    if k=='track_matte':
                        matte=cache[('matte',i)].resize((iw,ih),Image.Resampling.LANCZOS)
                        if cue['feather']:matte=matte.filter(ImageFilter.GaussianBlur(cue['feather']))
                        alpha=ImageChops.multiply(alpha,matte)
                    if cue['animation'].startswith('reveal_'):
                        reveal=Image.new('L',(iw,ih));rd=ImageDraw.Draw(reveal)
                        rd.rectangle((0,0,round(iw*p) if cue['animation']=='reveal_left' else iw,round(ih*p) if cue['animation']=='reveal_up' else ih),fill=255);alpha=ImageChops.multiply(alpha,reveal)
                    im.putalpha(ImageChops.multiply(im.getchannel('A'),alpha));angle=cue['from_angle']+(cue['to_angle']-cue['from_angle'])*p
                    if angle:im=im.rotate(angle,Image.Resampling.BICUBIC,expand=True)
                    dim(canvas,cue['dim']*opacity)
                    if cue['shadow']:
                        shadow=Image.new('RGBA',im.size,(0,0,0,0));shadow.putalpha(im.getchannel('A').point(lambda v:round(v*.25)));canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(8)),(x+6,y+9))
                    canvas.alpha_composite(im,(x-(im.width-iw)//2,y-(im.height-ih)//2))
            encoder.stdin.write(canvas.tobytes())
        encoder.stdin.close();code=encoder.wait(timeout=120)
        if code:raise RuntimeError('Motion layer encoder failed; inspect motion-render.stderr')
    except Exception:
        if encoder.poll() is None:encoder.terminate();encoder.wait(timeout=10)
        raise
    finally:
        for reader in readers.values():reader.close()
        error.close();(dest/'motion-render-process.json').write_text(json.dumps({'command':args,'returncode':encoder.returncode},indent=2),'utf-8')


def add_effects(body,mapping,sources,dest,font,args,graph,last,next_input):
    if not body.get('effects'):return args,graph,last,next_input
    render_layer({**body,'_motion_frames':mapping['frames']},sources,dest,font)
    args+=['-i','motion-layer.mov'];graph.append(f'[{last}][{next_input}:v]overlay=shortest=1:eof_action=pass:repeatlast=0[motioned]')
    return args,graph,'motioned',next_input+1
