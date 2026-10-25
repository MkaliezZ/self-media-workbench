"""Original procedural night-observatory FX assets. No product/fixture imports."""
from pathlib import Path
import hashlib,json,math,subprocess,wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'materials';OUT.mkdir(exist_ok=True)
FONTS=[Path('C:/Windows/Fonts/arial.ttf'),Path('/System/Library/Fonts/Supplemental/Arial.ttf')]
def font(n):
    p=next((p for p in FONTS if p.exists()),None)
    return ImageFont.truetype(str(p),n) if p else ImageFont.load_default(size=n)

def image(scene,w,h,t):
    im=Image.new('RGB',(w,h),'#102137');d=ImageDraw.Draw(im);s=min(w/1000,h/560)
    # Contrast-rich stable reference field, unlike the previous travel illustrations.
    for x in range(0,w,max(24,w//20)):d.line((x,0,x,h),fill='#203e55',width=1)
    for y in range(0,h,max(24,h//12)):d.line((0,y,w,y),fill='#203e55',width=1)
    if scene=='R':
        cx,cy=w*.48,h*.52;rr=h*.31
        for f in [.25,.5,.75,1]:d.ellipse((cx-rr*f,cy-rr*f,cx+rr*f,cy+rr*f),outline='#50a47e',width=max(1,int(2*s)))
        theta=t*1.3;px,py=cx+rr*math.cos(theta),cy+rr*math.sin(theta)
        d.polygon([(cx,cy),(px,py),(cx+rr*math.cos(theta-.24),cy+rr*math.sin(theta-.24))],fill='#285e50')
        d.line((cx,cy,px,py),fill='#b7eaa6',width=max(2,int(3*s)))
        for j in range(4):
            xx=w*(.26+j*.13);yy=h*(.4+.1*math.sin(j*2))
            d.rectangle((xx-8*s,yy-8*s,xx+8*s,yy+8*s),fill='#efb14c')
        d.text((w*.08,h*.12),'01  ACQUIRE',font=font(max(16,int(w*.045))),fill='#d3eed6')
        d.text((w*.67,h*.70),'RADAR / NORTH',font=font(max(12,int(w*.024))),fill='#f0cf85')
    elif scene=='S':
        d.rectangle((w*.06,h*.20,w*.94,h*.83),fill='#243153',outline='#668ab0',width=3)
        pts=[]
        for j in range(8):
            xx=w*(.15+(j%3)*.31);yy=h*(.31+(j//3)*.18)
            pts.append((xx,yy));rad=(4+2*math.sin(t*2+j))*s
            d.ellipse((xx-rad,yy-rad,xx+rad,yy+rad),fill='#f5d49d')
        d.line(pts,fill='#8d88c1',width=max(2,int(3*s)))
        xx=w*(.2+.6*(t%5)/5);d.line((xx,h*.22,xx,h*.81),fill='#f08a76',width=max(2,int(5*s)))
        d.text((w*.08,h*.11),'02  ALIGN',font=font(max(16,int(w*.055))),fill='#e4d5ef')
        # Silent semantic event: the constellation lock appears at source 2-5 s.
        if 2<=t<=5:
            d.rounded_rectangle((w*.18,h*.86,w*.84,h*.91),radius=8,fill='#f5d49d')
            d.text((w*.23,h*.869),'TARGET CONFIRMED',font=font(max(12,int(w*.037))),fill='#243153')
    elif scene=='U':
        d.rectangle((0,h*.74,w,h),fill='#1f3b48')
        d.polygon([(w*.25,h*.77),(w*.51,h*.39),(w*.76,h*.77)],fill='#518f9d')
        d.ellipse((w*.29,h*.23,w*.72,h*.61),fill='#d5a150',outline='#f6d897',width=max(3,int(5*s)))
        d.polygon([(w*.25,h*.23),(w*.70,h*.15),(w*.75,h*.24),(w*.33,h*.42)],fill='#102137')
        for j in range(3):
            rr=h*(.06+((t*.1+j*.11)%.32));cx,cy=w*.75,h*.25
            d.arc((cx-rr,cy-rr,cx+rr,cy+rr),220,320,fill='#b6d8dc',width=max(1,int(3*s)))
        d.text((w*.08,h*.10),'03  TRANSMIT',font=font(max(16,int(w*.045))),fill='#f3ddb8')
        d.text((w*.12,h*.88),'DATA RETURNS TO EARTH',font=font(max(12,int(w*.030))),fill='#cae7de')
    else:
        # Opaque diagnostic feed. Its corners must disappear through the circle mask.
        # Broad light/magenta blocks permit independent alpha reconstruction.
        tile=max(32,w//4)
        for yy in range(0,h,tile):
            for xx in range(0,w,tile):
                d.rectangle((xx,yy,xx+tile-1,yy+tile-1),fill='#f7dfa2' if (xx//tile+yy//tile)%2==0 else '#ec4b9b')
        for q in [.08,.92]:
            x,y=w*q,h*q;rr=w*.035
            d.line((x-rr,y,x+rr,y),fill='#2b2545',width=6);d.line((x,y-rr,x,y+rr),fill='#2b2545',width=6)
        rr=w*(.08+.02*math.sin(t*3));cx,cy=w*.5,h*.5
        d.ellipse((cx-rr,cy-rr,cx+rr,cy+rr),outline='#253958',width=max(2,w//64))
        d.text((w*.17,h*.28),'SENSOR FEED',font=font(max(16,w//17)),fill='#252e4a')
    bh=max(26,int(h*.055));d.rectangle((0,h-bh,w,h),fill='#07121c')
    d.text((w*.02,h-bh+3),f'{scene} SRC {t:05.2f}s | ORIGINAL SYNTHETIC OBSERVATORY',font=font(max(11,int(w*.018))),fill='#e4f0f4')
    return im

def wav(path,a):
    if a.ndim==1:a=np.column_stack((a,a))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(48000);f.writeframes((np.clip(a,-.95,.95)*32767).astype('<i2').tobytes())

def main():
    sr=48000;duration=16;n=sr*duration;track=np.zeros(n);beats=[]
    notes=[196,246.94,293.66,369.99,220,261.63,329.63,392]
    for b in range(32):
        start=b*.5;i=int(start*sr);t=np.arange(int(.45*sr))/sr
        tone=.13*np.sin(2*np.pi*notes[b%8]*t)*np.exp(-7*t)*(1-np.exp(-100*t))
        transient=.24*np.cos(2*np.pi*1800*t)*np.exp(-200*t)
        pulse=.16*np.sin(2*np.pi*58*t)*np.exp(-25*t)
        track[i:i+len(t)]+=tone+transient+pulse;beats.append(b*.5)
    wav(OUT/'observatory_original_120bpm.wav',track)
    (OUT/'music_beats.json').write_text(json.dumps({'bpm':120,'first_beat':0,'interval':.5,'duration':16,'source_seconds':beats},indent=2),encoding='utf-8')
    specs=[('R',1000,560,25,6,True),('S',576,1024,30,8,False),('U',768,768,24,8,True),('F',512,512,30,14,False)]
    manifest={'provenance':'Original programmatic night-observatory illustrations and synthesized sounds; not real filming, no external media/paid resource.','sources':[]};thumbs=[]
    for scene,w,h,fps,dur,has_audio in specs:
        path=OUT/f'{scene}_observatory_{w}x{h}_{fps}fps.mp4';tmp=OUT/f'_{scene}.mp4'
        p=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','pipe:0','-an','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',str(tmp)],stdin=subprocess.PIPE)
        for i in range(dur*fps):p.stdin.write(image(scene,w,h,i/fps).tobytes())
        p.stdin.close()
        if p.wait():raise RuntimeError(scene+' render failed')
        if has_audio:
            t=np.arange(dur*sr)/sr;amb=.025*np.sin(2*np.pi*(113 if scene=='R' else 173)*t)*(.8+.2*np.sin(t*2))
            audio=OUT/f'_{scene}.wav';wav(audio,amb)
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(tmp),'-i',str(audio),'-c:v','copy','-c:a','aac','-b:a','128k','-shortest',str(path)],check=True);tmp.unlink();audio.unlink()
        else:tmp.replace(path)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)]))
        (ROOT/'evidence'/f'probe_{scene}.json').write_text(json.dumps(probe,indent=2),encoding='utf-8')
        dec=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],capture_output=True,text=True)
        manifest['sources'].append({'id':scene,'file':path.name,'size':[w,h],'fps':fps,'duration':dur,'audio_present':has_audio,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'full_decode_exit':dec.returncode,'decode_stderr':dec.stderr})
        for sec in [1,3,5]:
            im=image(scene,w,h,sec);im.thumbnail((426,250));tile=Image.new('RGB',(450,290),'#e7edf1');tile.paste(im,((450-im.width)//2,0));ImageDraw.Draw(tile).text((10,260),f'{scene} / source {sec:.1f}s',font=font(18),fill='#173146');thumbs.append(tile)
        print(path.name,flush=True)
    sheet=Image.new('RGB',(1350,1160),'#e7edf1')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*450,(i//3)*290))
    sheet.save(ROOT/'evidence'/'fx_source_storyboard.jpg',quality=95)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
if __name__=='__main__':main()
