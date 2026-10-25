"""Independent decoded-pixel/audio checks for the presealed observatory task."""
from pathlib import Path
import argparse,json,subprocess,hashlib,math
import numpy as np
from PIL import Image,ImageDraw

def probe(path):return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)]))
def frames(path,indices):
    p=subprocess.Popen(['ffmpeg','-v','error','-i',str(path),'-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    found={};n=0;size=1280*720*3
    while True:
        raw=p.stdout.read(size)
        if not raw:break
        if len(raw)!=size:raise RuntimeError('Partial decoded frame')
        if n in indices:found[n]=np.frombuffer(raw,dtype=np.uint8).reshape((720,1280,3)).copy()
        n+=1
    stderr=p.stderr.read().decode();rc=p.wait()
    if rc or stderr.strip():raise RuntimeError(stderr)
    return found,n
def source(path,t,w=1280,h=720,contain=True):
    vf=f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=0x16181A' if contain else f'scale={w}:{h}'
    raw=subprocess.check_output(['ffmpeg','-v','error','-ss',f'{t:.8f}','-i',str(path),'-frames:v','1','-vf',vf,'-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
    return np.frombuffer(raw,dtype=np.uint8).reshape((h,w,3)).astype(float)
def rmse(a,b):return float(np.sqrt(np.mean((a.astype(float)-b.astype(float))**2)))
def alpha(actual,bg,fg):
    delta=fg-bg;den=(delta*delta).sum(axis=2);a=((actual-bg)*delta).sum(axis=2)/np.maximum(den,1)
    return a,den>25**2
def pcm(path):return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar','8000','-f','f32le','pipe:1']),dtype='<f4').astype(float)
def corr(x,y):
    x=x-x.mean();y=y-y.mean();return float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y)+1e-15))
def check(root,materials):
    index=json.loads((root/'exports-index.json').read_text(encoding='utf-8'));paths={k:Path(index[k]) for k in ['full','control','restored']};out=root/'independent-pixel-audio-v2';out.mkdir(exist_ok=True)
    src={s['id']:materials/s['file'] for s in json.loads((materials/'manifest.json').read_text(encoding='utf-8'))['sources']}
    ix={0,30,59,60,89,90,104,105,110,111,112,118,119,120,128,129,130,224,225,232,233,234,240,247,248,254,255,263,264,265,269,270,299,300,329,330,344,345,346,395,396,397,404}
    f,fn=frames(paths['full'],ix);c,cn=frames(paths['control'],ix);checks=[]
    def add(name,passed,**metrics):checks.append({'check':name,'pass':bool(passed),**metrics})
    for label,path in paths.items():
        p=probe(path);(out/(label+'-ffprobe.json')).write_text(json.dumps(p,indent=2),encoding='utf-8');v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
        add(label+'-clock',int(v['nb_read_frames'])==405 and v['width']==1280 and v['height']==720 and v['avg_frame_rate']=='30/1' and abs(float(v['duration'])-13.5)<1e-5 and abs(float(p['format']['duration'])-13.5)<=1/30,decoded_frames=int(v['nb_read_frames']),video_duration=v['duration'],audio_duration=a['duration'],container_duration=p['format']['duration'])
    # Source identity before/after both overlaps; leave titles and source marker rows out.
    for n,sid,st in [(0,'R',1),(104,'R',1+104/30),(120,'S',1+4-3.5),(224,'S',1+224/30-3.5),(255,'U',.5+8.5-7.5),(404,'U',.5+404/30-7.5)]:
        got=Image.fromarray(c[n][:570]).resize((320,142));ref=Image.fromarray(source(src[sid],st)[:570].astype(np.uint8)).resize((320,142));err=rmse(np.asarray(got),np.asarray(ref));add(f'source-frame-{n}',err<10,source=sid,source_time=st,rmse=err)
    # A fade's midpoint must be a genuine mixture, rather than a hard cut.
    n=112;t=n/30;aa=source(src['R'],1+t)[:570];bb=source(src['S'],1+t-3.5)[:570];got=c[n][:570].astype(float);d=bb-aa
    w=float(np.sum((got-aa)*d)/np.maximum(np.sum(d*d),1));err=rmse(got,aa+w*d)
    add('fade-mixture',.2<w<.8 and err<10,estimated_incoming_weight=w,residual_rmse=err)
    # wipeleft replaces pixels from the right; test each independent source clock.
    for n in [233,240,248]:
        t=n/30;p=(t-7.5);aa=source(src['S'],1+t-3.5);bb=source(src['U'],.5+t-7.5);split=round(1280*(1-p));expected=aa.copy();expected[:,split:]=bb[:,split:]
        err=rmse(c[n][:570],expected[:570]);add('wipe-'+str(n),err<10,incoming_fraction=p,split_x=split,rmse=err)
    for kind,n,x,y,st in [('rectangle',60,800,160,3),('circle',300,180,220,8)]:
        bg=c[n][y:y+320,x:x+320].astype(float);fg=source(src['F'],st,320,320,False);actual=f[n][y:y+320,x:x+320].astype(float);a,valid=alpha(actual,bg,fg)
        yy,xx=np.mgrid[:320,:320];core=((xx-160)**2+(yy-160)**2<70**2)&valid
        outside=((xx<30)&(yy<30)|(xx>289)&(yy<30)|(xx<30)&(yy>289)|(xx>289)&(yy>289))&valid if kind=='circle' else None
        med=float(np.median(a[core]));add(kind+'-opaque-core',med>=.95,median_alpha=med)
        if outside is not None:
            ext=float(np.percentile(np.abs(a[outside]),95));add(kind+'-transparent-corners',ext<=.03,alpha_abs_95percentile=ext)
        else:
            # The rectangle slot covers its whole layer; compare the outer ring.
            bgwhole=c[n].astype(float);whole=f[n].astype(float);mask=np.zeros((720,1280),bool);mask[y-8:y+328,x-8:x+328]=True;mask[y:y+320,x:x+320]=False
            err=float(np.mean(abs(whole[mask]-bgwhole[mask])))
            outside_fg=np.pad(fg,((8,8),(8,8),(0,0)),mode='edge');aa,vv=alpha(whole[y-8:y+328,x-8:x+328],bgwhole[y-8:y+328,x-8:x+328],outside_fg)
            ring=np.ones((336,336),bool);ring[8:328,8:328]=False;valid_ring=ring&vv
            ext=float(np.percentile(np.abs(aa[valid_ring]),95))
            add('rectangle-outer-background',err<3 and ext<=.03,mean_absolute_rgb_difference=err,alpha_abs_95percentile=ext)
        row=160 if kind=='circle' else 120;profile=a[row,:49];v=valid[row,:49];mid=(profile>=.15)&(profile<=.85)&v
        longest=run=0
        for z in mid:run=run+1 if z else 0;longest=max(longest,run)
        levels=len(np.unique(np.round(profile[mid]*50)))
        add(kind+'-feather',longest>=8 and levels>=5,contiguous_intermediate_pixels=longest,intermediate_levels=levels,alpha_profile=[round(float(z),4) for z in profile])
        heat=np.uint8(np.clip(a,0,1)*255);Image.fromarray(heat).save(out/(kind+'-measured-alpha.png'))
    # Small source labels contribute about 123 white pixels. Isolate the much
    # larger 36px cue glyphs, preserving exact global start/end frame criteria.
    for a,b in [(111,129),(234,264),(345,396)]:
        for n,expect in [(a-1,False),(a,True),(b-1,True),(b,False)]:
            roi=f[n][580:680,100:1180];white=int(np.all(roi>220,axis=2).sum());present=white>500
            add(f'title-frame-{n}',present==expect,white_pixels=white,expected_present=expect)
    audio=pcm(paths['full']);music=pcm(materials/'observatory_original_120bpm.wav')
    for start in [4.5,6,12]:
        pos=round(start*8000);length=8000;x=audio[pos:pos+length];lags=list(range(-320,321));cs=[corr(x,music[pos+k:pos+k+length]) for k in lags];best=int(np.argmax(cs));offset=lags[best]/8000
        add('music-'+str(start),abs(offset)<=1/30 and cs[best]>=.96,best_lag_seconds=offset,correlation=cs[best])
    def rawhash(path,args):
        p=subprocess.Popen(['ffmpeg','-v','error','-i',str(path),*args,'-'],stdout=subprocess.PIPE);h=hashlib.sha256()
        while block:=p.stdout.read(1024*1024):h.update(block)
        if p.wait():raise RuntimeError('hash decode failed')
        return h.hexdigest()
    for name,args in [('decoded-video',['-an','-pix_fmt','rgb24','-f','rawvideo']),('decoded-pcm',['-vn','-ac','2','-ar','48000','-f','s16le'])]:
        h1=rawhash(paths['full'],args);h2=rawhash(paths['restored'],args);add('restore-'+name,h1==h2,first_sha256=h1,restored_sha256=h2)
    thumbs=[]
    for n in sorted(ix):
        im=Image.fromarray(f[n]);im.thumbnail((384,216));tile=Image.new('RGB',(400,245),'#e7edf1');tile.paste(im,(8,0));ImageDraw.Draw(tile).text((8,222),f'frame {n} / {n/30:.3f}s',fill='#173146');thumbs.append(tile)
    sheet=Image.new('RGB',(1200,245*math.ceil(len(thumbs)/3)),'#e7edf1')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*400,(i//3)*245))
    sheet.save(out/'decoded-fx-contact-sheet.jpg',quality=94)
    report={'all_technical_checks_pass':all(c['pass'] for c in checks),'checks':checks,'scope':'Actual decoded media comparison, not artistic/listening or real travel validation.'};(out/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2));return report
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--materials',type=Path,required=True);a=p.parse_args();r=check(a.output,a.materials)
    if not r['all_technical_checks_pass']:raise SystemExit(1)
