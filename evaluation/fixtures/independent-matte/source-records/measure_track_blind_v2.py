"""Inverse-composite measurements from actual independent source/output pixels."""
from pathlib import Path
import json,sys,subprocess,importlib.util,math,hashlib
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent/'product-clone'
sp=importlib.util.spec_from_file_location('previous_own_decoder',REPO/'evaluation'/'independent_fx'/'check_fx.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
def source(t,size):
    p=ROOT/'materials'/'deep_rover_960x600_25fps.mp4';raw=subprocess.check_output(['ffmpeg','-v','error','-ss',f'{t:.8f}','-i',str(p),'-frames:v','1','-vf',f'crop=600:600:180:0,scale={size}:{size}','-pix_fmt','rgb24','-f','rawvideo','pipe:1']);return np.frombuffer(raw,dtype=np.uint8).reshape((size,size,3)).astype(float)
def core_alpha(c,b,f):
    d=f-b;den=(d*d).sum(axis=2);return ((c-b)*d).sum(axis=2)/np.maximum(den,1),den>25**2
def main():
    out=ROOT/'attempts'/'001-5dcad35';i=json.loads((out/'exports-index.json').read_text(encoding='utf-8'));ev=out/'decoded-evidence-v2';ev.mkdir(exist_ok=True);indices={0,30,60,120,180,240,300,360,420,480,495,510,525,540,555,570,585,588,597,599};f,n=m.frames(Path(i['full']),indices);control,cn=m.frames(Path(i['control']),{540,588});bg=np.asarray(Image.open(ROOT/'materials'/'deep_background.png').convert('RGB')).astype(float);checks=[]
    def add(name,passed,**values):checks.append({'check':name,'pass':bool(passed),**values})
    for name in ['full','control','restored']:
        p=m.probe(Path(i[name]));(ev/(name+'-ffprobe.json')).write_text(json.dumps(p,indent=2),encoding='utf-8');v=next(z for z in p['streams'] if z['codec_type']=='video');a=next(z for z in p['streams'] if z['codec_type']=='audio');add(name+'-clock',v['nb_read_frames']=='600' and v['width']==1280 and v['height']==720 and v['avg_frame_rate']=='30/1' and abs(float(v['duration'])-20)<1e-5 and abs(float(p['format']['duration'])-20)<=1/30,frames=v['nb_read_frames'],video_duration=v['duration'],audio_duration=a['duration'],container_duration=p['format']['duration'])
    points=[(64,32),(192,32),(320,32),(448,32),(64,96),(448,96),(256,256)]
    for t,mode,invert in [(2,'alpha',False),(6,'alpha',True),(10,'luma',False),(14,'luma',True)]:
        frame=round(t*30);got=f[frame][104:616,384:896].astype(float);background=bg[104:616,384:896];matte=np.asarray(Image.open(ROOT/'materials'/f'independent_{mode}_bands.png').convert('RGBA'))
        expected=(matte[:,:,3].astype(float) if mode=='alpha' else matte[:,:,0].astype(float))/255
        if invert:expected=1-expected
        candidates=[]
        for st in [t-.04,t,t+.04]:
            fg=source(st,512);pred=background+(fg-background)*expected[:,:,None];candidates.append((m.rmse(got,pred),st,fg))
        err,st,fg=min(candidates,key=lambda z:z[0]);a,valid=core_alpha(got,background,fg);observed=[]
        for x,y in points:
            # The hole probe is alpha-only. In the opaque luma mask x256 is
            # exactly a grey-step boundary, contrary to the task's stable-ROI rule.
            if mode=='luma' and (x,y)==(256,256):continue
            roi=a[y-4:y+5,x-4:x+5];vv=valid[y-4:y+5,x-4:x+5];obs=float(np.median(roi[vv]));target=float(expected[y,x]);observed.append({'point':[x,y],'expected':target,'actual_alpha':obs,'absolute_error':abs(obs-target)})
        add(f'{mode}-invert-{invert}-alpha',all(z['absolute_error']<=.04 for z in observed),samples=observed)
        add(f'{mode}-invert-{invert}-source-clock',err<8,nearest_source_seconds=st,reference_frame_rmse=err)
        Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(ev/f'{mode}-invert-{invert}-measured-alpha.png')
    # Stable hold: isolate circle alpha from the layer's separate entry fade.
    t=19.6;got=f[588][120:440,800:1120].astype(float);background=bg[120:440,800:1120];fg=source(t,320);a,valid=core_alpha(got,background,fg);yy,xx=np.mgrid[:320,:320];core=((xx-160)**2+(yy-160)**2<60**2)&valid;corners=((xx<25)&(yy<25)|(xx>294)&(yy<25)|(xx<25)&(yy>294)|(xx>294)&(yy>294))&valid
    center=float(np.median(a[core]));corner_samples=[]
    # Median ROIs, as predeclared, rather than a pooled high percentile over
    # high-frequency background text. The lower-right footer is low contrast;
    # sample the same outside-corner quadrant above the source footer boundary.
    for px,py in [(12,12),(307,12),(12,307),(300,288)]:
        roi=a[py-4:py+5,px-4:px+5];v=valid[py-4:py+5,px-4:px+5]
        if not v.any():raise RuntimeError('Ill-conditioned outside-alpha probe')
        corner_samples.append({'point':[px,py],'median_absolute_alpha':float(np.median(abs(roi[v]))),'valid_pixels':int(v.sum())})
    outside=max(z['median_absolute_alpha'] for z in corner_samples)
    add('circle-core',center>=.95,median_alpha=center);add('circle-outside',outside<=.03,maximum_roi_median_absolute_alpha=outside,corner_samples=corner_samples)
    profile=a[160,:49];inter=(profile>=.15)&(profile<=.85)&valid[160,:49];run=longest=0
    for z in inter:run=run+1 if z else 0;longest=max(longest,run)
    levels=len(np.unique(np.round(profile[inter]*50)));add('circle-feather',longest>=8 and levels>=5,contiguous_intermediate_pixels=longest,intermediate_levels=levels,profile=profile.tolist());Image.fromarray(np.uint8(np.clip(a,0,1)*255)).save(ev/'circle-measured-alpha.png')
    # Pixel-based centre fitting at t17: PNG foreground is still fully faded out.
    t=17;p=(t-16)/3.5;e=3*p*p-2*p*p*p;left=round(100+700*e);top=round(280-160*e);roi=(left-14,top-14,left+334,top+334);x0,y0,x1,y1=roi;actual=f[510][y0:y1,x0:x1].astype(float);background=bg[y0:y1,x0:x1];fg=source(t,320);mask=np.asarray(Image.open(ROOT/'materials'/'independent_feather_circle.png').getchannel('A').resize((320,320)),dtype=float)/255;best=None
    for dx in range(-10,11,2):
        for dy in range(-10,11,2):
            delta=np.zeros_like(background);x,y=14+dx,14+dy;delta[y:y+320,x:x+320]=(fg-background[y:y+320,x:x+320])*mask[:,:,None];opacity=float(np.sum((actual-background)*delta)/max(np.sum(delta*delta),1));opacity=np.clip(opacity,0,1);err=m.rmse(actual,background+opacity*delta)
            if best is None or err<best['rmse']:best={'dx':dx,'dy':dy,'fitted_entry_opacity':float(opacity),'rmse':err}
    add('moving-circle-position',abs(best['dx'])<=8 and abs(best['dy'])<=8,authored_top_left=[left,top],fit=best)
    # Foreground order at18s: transparent hole must expose the same content,
    # whereas the opaque cross must genuinely change the occlusion result.
    samples=[]
    for name,x,y in [('hole',610,310),('beam',640,340)]:
        ca=f[540][y-3:y+4,x-3:x+4].astype(float);cb=control[540][y-3:y+4,x-3:x+4].astype(float);err=m.rmse(ca,cb);samples.append({'point':name,'pixel':[x,y],'full_rgb':np.median(ca.reshape(-1,3),axis=0).tolist(),'control_rgb':np.median(cb.reshape(-1,3),axis=0).tolist(),'order_difference_rmse':err});add('foreground-'+name,err<5 if name=='hole' else err>15,**samples[-1])
    region=f[540][160:520,460:820];magenta=(region[:,:,0]>200)&(region[:,:,1]<70)&(region[:,:,2]>180);count=int(magenta.sum());add('transparent-magenta-does-not-leak',count==0,visible_magenta_pixels=count)
    audio=m.pcm(Path(i['full']));music=m.pcm(ROOT/'materials'/'deep_original_clock.wav')
    for start in [2,6,10,14,18]:
        at=round(start*8000);x=audio[at:at+8000];lags=list(range(-270,271));cc=[m.corr(x,music[at+k:at+k+8000]) for k in lags];best=int(np.argmax(cc));offset=lags[best]/8000;add('audio-'+str(start),abs(offset)<=1/30 and cc[best]>=.96,lag_seconds=offset,correlation=cc[best])
    # Bit-identical MP4 implies identical decoded frames and PCM. If metadata
    # differs, hash each decoded stream explicitly instead of excusing content.
    def rawhash(path,args):
        process=subprocess.Popen(['ffmpeg','-v','error','-i',str(path),*args,'-'],stdout=subprocess.PIPE);h=hashlib.sha256()
        while chunk:=process.stdout.read(1024*1024):h.update(chunk)
        if process.wait():raise RuntimeError('Decoded hash failed')
        return h.hexdigest()
    for name,args in [('video',['-an','-pix_fmt','rgb24','-f','rawvideo']),('pcm',['-vn','-ac','2','-ar','48000','-f','s16le'])]:
        h1=rawhash(i['full'],args);h2=rawhash(i['restored'],args);add('restored-'+name,h1==h2,first_decoded_sha256=h1,restored_decoded_sha256=h2)
    ids=[60,180,300,420,495,510,525,540,555,588];sheet=Image.new('RGB',(1280,390*math.ceil(len(ids)/2)),'#dce6e9')
    for k,frame in enumerate(ids):
        im=Image.fromarray(f[frame]);im.thumbnail((640,360));x,y=(k%2)*640,(k//2)*390;sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text((x+10,y+368),f'ACTUAL frame{frame} / {frame/30:.3f}s',fill='#17364b')
    sheet.save(ev/'actual-track-matte-contact-sheet.jpg',quality=95);Image.fromarray(control[540]).save(ev/'actual-order-control-frame0540.png')
    result={'all_checks_pass':all(z['pass'] for z in checks),'checks':checks,'note':'Real decoded source/matte/output comparison, not creative or real-observation validation.'};(ev/'measurements.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
