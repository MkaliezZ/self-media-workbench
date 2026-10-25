"""Independent decoded media checks; no product imports. Evidence, not API status.
Usage: python verify_independent_output.py OUTPUT.mp4 [--variant baseline|cut|restored]
"""
from pathlib import Path
import argparse, json, subprocess, wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
def call(args): return subprocess.check_output(args)
def probe(p): return json.loads(call(['ffprobe','-v','error','-count_frames','-show_format','-show_streams','-of','json',str(p)]))
def getframe(p,t,w=1280,h=720):
    data=call(['ffmpeg','-v','error','-ss',f'{t:.6f}','-i',str(p),'-frames:v','1','-vf',f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black','-pix_fmt','rgb24','-f','rawvideo','pipe:1'])
    return Image.frombytes('RGB',(w,h),data)
def pcm(p):
    return np.frombuffer(call(['ffmpeg','-v','error','-i',str(p),'-vn','-ac','1','-ar','8000','-f','f32le','pipe:1']),dtype='<f4')
def correlation(x,y):
    x=x.astype(float)-np.mean(x);y=y.astype(float)-np.mean(y)
    return float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y)+1e-12))
def main():
    pa=argparse.ArgumentParser();pa.add_argument('output',type=Path);pa.add_argument('--materials-root',type=Path,default=ROOT);pa.add_argument('--variant',choices=['baseline','cut','restored'],default='baseline');a=pa.parse_args();global_root=a.materials_root
    evidence=a.output.parent/(a.output.stem+'_independent_v2_evidence');evidence.mkdir(exist_ok=True)
    pr=probe(a.output);(evidence/'ffprobe.json').write_text(json.dumps(pr,indent=2),encoding='utf-8')
    v=next(s for s in pr['streams'] if s['codec_type']=='video');audio=[s for s in pr['streams'] if s['codec_type']=='audio']
    cut=a.variant=='cut';duration=15 if cut else 16
    segments=[('A',0,3,1.25),('B',3,5,2),('B',5,6,5),('C',6,11,1),('D',11,15,.5)] if cut else [('A',0,3,1.25),('B',3,7,2),('C',7,12,1),('D',12,16,.5)]
    manifest=json.loads((global_root/'materials'/'manifest.json').read_text(encoding='utf-8'));sources={s['id']:global_root/'materials'/s['file'] for s in manifest['sources']}
    report={'output':str(a.output.resolve()),'variant':a.variant,'target_duration':duration,'actual_duration':float(pr['format']['duration']),'size':[v['width'],v['height']],'fps':v['avg_frame_rate'],'decoded_frame_count':int(v['nb_read_frames']),'audio_present':bool(audio),'samples':[]}
    samples=sorted(set([.1]+[x+.1 for x in range(1,duration)]+[s[1]+1/30 for s in segments]+[s[2]-1/30 for s in segments]))
    thumbs=[]
    for t in samples:
        sid,start,end,src=next(s for s in segments if s[1]<=t<s[2]);st=src+t-start
        actual=getframe(a.output,t);expected=getframe(sources[sid],st)
        # Compare source-bearing pixels; border colour is not a task constraint.
        # Keep the first sealed checker and its false failure as separate evidence.
        info=next(z for z in manifest['sources'] if z['id']==sid)
        scale=min(1280/info['width'],720/info['height'])
        cw,ch=int(info['width']*scale),int(info['height']*scale)
        left,top=(1280-cw)//2,(720-ch)//2
        box=(left+3,top+3,left+cw-3,top+ch-3)
        aa=np.asarray(actual.crop(box).resize((160,90)),dtype=float);ee=np.asarray(expected.crop(box).resize((160,90)),dtype=float)
        rmse=float(np.sqrt(np.mean((aa-ee)**2)))
        report['samples'].append({'output_time':t,'source':sid,'source_time':st,'decoded_frame_rmse_0_255':rmse,'match':rmse<15})
        thumb=actual.copy();thumb.thumbnail((384,216));tile=Image.new('RGB',(400,250),'#f5f0e4');tile.paste(thumb,((400-thumb.width)//2,0));d=ImageDraw.Draw(tile);d.text((8,220),f'{t:.3f}s -> {sid} {st:.3f}s / RMSE {rmse:.2f}',fill='#172c37');thumbs.append(tile)
    sheet=Image.new('RGB',(1200,250*((len(thumbs)+2)//3)),'#f5f0e4')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*400,(i//3)*250))
    sheet.save(evidence/'decoded_contact_sheet.jpg',quality=92)
    if audio:
        out=pcm(a.output);music=pcm(global_root/'materials'/'journey_original_120bpm.wav')
        # B has no source audio; use its first two seconds to isolate exact music alignment.
        sr=8000;start=int(3.5*sr);length=8000
        x=out[start:start+length]
        lags=range(-400,401);corr=[correlation(x,music[start+k:start+k+length]) for k in lags]
        best=int(np.argmax(corr));report['music']={'best_lag_seconds':list(lags)[best]/sr,'normalized_correlation':corr[best],'zero_lag_correlation':correlation(x,music[start:start+length]),'pass':abs(list(lags)[best]/sr)<=1/30 and corr[best]>.96}
    report['structural_pass']=abs(report['actual_duration']-duration)<=1/30+.001 and report['size']==[1280,720] and report['fps']=='30/1' and report['decoded_frame_count']==duration*30 and bool(audio)
    report['decoded_frame_pass']=all(x['match'] for x in report['samples'])
    report['automated_checks_pass']=report['structural_pass'] and report['decoded_frame_pass'] and report.get('music',{}).get('pass',False)
    report['boundary']='Decoded frame/audio metrics complement visual review; do not establish product state/version semantics or human quality by themselves.'
    (evidence/'result.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
