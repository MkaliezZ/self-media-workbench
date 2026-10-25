"""Independent travel animation fixture. No repository imports or fixtures.
All drawings and audio are generated here; no real footage or licensed media.
Run with Python + Pillow + numpy, and ffmpeg/ffprobe on PATH.
"""
from pathlib import Path
import hashlib, json, math, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'materials'
OUT.mkdir(exist_ok=True)
FONT_PATH = Path('C:/Windows/Fonts/arial.ttf')
def font(size):
    return ImageFont.truetype(str(FONT_PATH), size) if FONT_PATH.exists() else ImageFont.load_default(size=size)

def traveler(d, x, y, s=1):
    x,y,s=round(x),round(y),s
    d.line((x-6*s,y+22*s,x-12*s,y+43*s),fill='#243b50',width=max(2,round(6*s)))
    d.line((x+6*s,y+22*s,x+15*s,y+42*s),fill='#243b50',width=max(2,round(6*s)))
    d.rounded_rectangle((x-15*s,y-5*s,x+13*s,y+27*s),radius=6*s,fill='#e88a37')
    d.rounded_rectangle((x-24*s,y-3*s,x-10*s,y+22*s),radius=4*s,fill='#284d66')
    d.ellipse((x-9*s,y-25*s,x+10*s,y-6*s),fill='#e8bf90')
    d.polygon([(x-13*s,y-23*s),(x+8*s,y-28*s),(x+18*s,y-18*s),(x-18*s,y-17*s)],fill='#d3a543')

def frame(scene,w,h,t):
    im=Image.new('RGB',(w,h),'#c7e3eb');d=ImageDraw.Draw(im)
    sx=w/960;sy=h/540
    if scene=='A':
        # A moving train window framing foothills; the orange backpack recurs.
        d.rectangle((0,h*.55,w,h),fill='#b4c595')
        for k,c in enumerate(['#8cafaa','#67949a','#46777c']):
            pts=[(-100,h*.67)]
            for j in range(7):
                xx=(j*240-(t*35*(k+1))%240)*sx
                pts.extend([(xx,h*(.45-.08*k)),(xx+140*sx,h*(.22+.06*k))])
            pts.extend([(w+100,h),(0,h)]);d.polygon(pts,fill=c)
        d.rounded_rectangle((w*.07,h*.09,w*.93,h*.83),radius=int(35*sx),outline='#263c4b',width=int(32*sx))
        d.rectangle((0,h*.86,w,h),fill='#d5be9b')
        d.line((w*.5,h*.1,w*.5,h*.83),fill='#263c4b',width=int(12*sx))
        traveler(d,w*.78,h*.73,min(sx,sy)*2)
        d.text((w*.12,h*.16),'01 / FOOTHILL TRAIN',font=font(int(28*sx)),fill='#f9efda')
        # A passing signal at 3 seconds, objectively distinct from all other frames.
        px=w*.95-(t%5)*w*.22
        d.rectangle((px,h*.42,px+8*sx,h*.75),fill='#344a43')
        d.ellipse((px-15*sx,h*.37,px+23*sx,h*.44),fill='#e8b53d')
    elif scene=='B':
        d.rectangle((0,h*.45,w,h),fill='#6f9c78')
        d.polygon([(0,h*.55),(w*.35,h*.19),(w*.77,h*.51)],fill='#638a83')
        d.polygon([(w*.37,h*.55),(w*.79,h*.23),(w,h*.52)],fill='#477372')
        d.polygon([(w*.38,h),(w*.57,h),(w*.60,h*.51),(w*.48,h*.51)],fill='#dbc9a1')
        for xx,yy in [(0.1,.53),(.89,.61),(.19,.73),(.86,.86)]:
            d.rectangle((w*xx-4,h*yy,w*xx+4,h*(yy+.11)),fill='#79684b')
            d.polygon([(w*xx-w*.1,h*(yy+.03)),(w*xx,h*(yy-.12)),(w*xx+w*.1,h*(yy+.03))],fill='#315f51')
        traveler(d,w*(.5+.02*math.sin(t*3)),h*(.73-.012*t),min(sx,sy)*2.4)
        # Meaningful silent event: route board and safe direction, held 2.5-5.5 s.
        if 2.5<=t<=5.5:
            d.rectangle((w*.68,h*.41,w*.70,h*.7),fill='#775d3f')
            d.polygon([(w*.54,h*.43),(w*.88,h*.43),(w*.95,h*.47),(w*.88,h*.51),(w*.54,h*.51)],fill='#f1ddaa')
            d.text((w*.57,h*.45),'SUMMIT >',font=font(int(29*sx)),fill='#294947')
            d.text((w*.10,h*.29),'THE QUIET CLUE',font=font(int(34*sx)),fill='#f8f3db')
        d.text((w*.10,h*.10),'02 / FOREST PATH',font=font(int(31*sx)),fill='#244c58')
    elif scene=='C':
        d.ellipse((w*.73,h*.13,w*.85,h*.25),fill='#f6d896')
        for k,c in enumerate(['#87adba','#68939f','#486f7c']):
            pts=[(0,h)]
            for j in range(6):
                xx=j*w*.23-(t*7*k)%int(w*.23)
                pts.extend([(xx,h*(.60-.07*k)),(xx+w*.14,h*(.32+.06*k))])
            pts.extend([(w,h),(0,h)]);d.polygon(pts,fill=c)
        d.polygon([(0,h*.82),(w*.45,h*.65),(w,h*.84),(w,h),(0,h)],fill='#b6b197')
        d.line((w*.25,h*.72,w*.25,h*.53),fill='#4d5f58',width=int(8*sx))
        d.polygon([(w*.25,h*.53),(w*.48,h*.55),(w*.25,h*.62)],fill='#df8649')
        traveler(d,w*.49,h*.72,min(sx,sy)*2)
        d.text((w*.09,h*.12),'03 / SUMMIT REACHED',font=font(int(29*sx)),fill='#274e60')
        d.text((w*.10,h*.89),'LOOK BACK. BREATHE.',font=font(int(26*sx)),fill='#36575a')
        for i in range(3):
            bx=(w*.2+i*w*.17+t*21)%w;by=h*.29+i*h*.04
            d.line((bx-10*sx,by+5*sy,bx,by,bx+10*sx,by+5*sy),fill='#36525f',width=max(1,int(2*sx)))
    else:
        d.rectangle((0,h*.40,w,h),fill='#6b9da5')
        d.ellipse((w*.70,h*.10,w*.83,h*.33),fill='#efc578')
        d.polygon([(0,h*.39),(w*.2,h*.30),(w*.4,h*.39)],fill='#638480')
        for j in range(9):
            yy=h*(.46+j*.045);xx=(t*22+j*71)%w
            d.line((xx,yy,min(w,xx+w*.20),yy),fill='#a3c3c0',width=max(1,int(2*sy)))
        d.polygon([(0,h),(w*.43,h*.63),(w*.59,h*.63),(w*.82,h),(0,h)],fill='#ac9272')
        d.line((w*.43,h*.63,w*.25,h),fill='#ead9b7',width=int(4*sx))
        d.line((w*.59,h*.63,w*.70,h),fill='#ead9b7',width=int(4*sx))
        boatx=w*.72-20*t*sx
        d.polygon([(boatx,h*.55),(boatx+w*.16,h*.55),(boatx+w*.13,h*.60),(boatx+w*.03,h*.60)],fill='#354f5c')
        d.polygon([(boatx+w*.08,h*.53),(boatx+w*.08,h*.36),(boatx+w*.14,h*.52)],fill='#f4e5be')
        traveler(d,w*.50,h*.75,min(sx,sy)*1.5)
        d.text((w*.08,h*.13),'04 / HARBOR HOME',font=font(int(30*sx)),fill='#315768')
    # Reliable evidence frame markers survive scaling and black bars.
    bh=max(36,round(h*.065));d.rectangle((0,h-bh,w,h),fill='#173343')
    label=f'{scene}  SOURCE {t:05.2f}s  |  SYNTHETIC TRAVEL ANIMATION'
    d.text((w*.025,h-bh+bh*.15),label,font=font(max(12,round(w*.021))),fill='#ffffff')
    return im

def write_wav(path,arr,sr=48000):
    arr=np.clip(arr,-.96,.96)
    if arr.ndim==1: arr=np.column_stack((arr,arr))
    with wave.open(str(path),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes((arr*32767).astype('<i2').tobytes())

def music():
    sr=48000;dur=24;n=int(sr*dur);t=np.arange(n)/sr;arr=np.zeros(n)
    notes=[261.63,329.63,392,329.63,293.66,349.23,440,349.23]
    beats=[]
    for b in range(48):
        start=b*.5;i=int(start*sr);tt=np.arange(min(int(.45*sr),n-i))/sr
        # Original arpeggio, kick-like sine and high click: exact beat onset at b/2.
        env=np.exp(-tt*8)*(1-np.exp(-tt*120))
        ar=.10*np.sin(2*np.pi*notes[b%8]*tt)*env
        click=.23*np.cos(2*np.pi*2200*tt)*np.exp(-tt*180)
        kick=.20*np.sin(2*np.pi*(65*tt-22*tt*tt))*np.exp(-tt*22)
        arr[i:i+len(tt)]+=ar+click+kick
        beats.append({'index':b,'time_seconds':start,'bar':b//4+1,'beat_in_bar':b%4+1})
    write_wav(OUT/'journey_original_120bpm.wav',np.column_stack((arr,arr*.98)))
    (OUT/'music_beats.json').write_text(json.dumps({'bpm':120,'first_beat_seconds':0,'beat_interval_seconds':.5,'duration_seconds':dur,'beats':beats},indent=2),encoding='utf-8')

def main():
    music();specs=[('A',960,540,24,'24',9,True),('B',540,960,30,'30',8,False),('C',640,640,25,'25',10,True),('D',1280,720,30000/1001,'30000/1001',7,False)]
    manifest={'provenance':'Original programmatic illustrations and original synthesized audio. Not real travel footage. No external copyrighted or paid resources.','sources':[]}
    thumbs=[]
    for scene,w,h,fps,fpsstr,dur,has_audio in specs:
        path=OUT/f'{scene}_travel_{w}x{h}_{fpsstr.replace("/","-")}fps.mp4'
        silent=OUT/f'_{scene}_video.mp4'
        cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',fpsstr,'-i','pipe:0','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(silent)]
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        for i in range(round(dur*fps)):
            p.stdin.write(frame(scene,w,h,i/fps).tobytes())
        p.stdin.close();rc=p.wait()
        if rc:raise RuntimeError(f'ffmpeg {scene} returned {rc}')
        if has_audio:
            sr=48000;t=np.arange(round(dur*sr))/sr
            rng=np.random.default_rng(20261025+ord(scene))
            # Gentle scene ambience, intentionally not speech.
            amb=.034*np.sin(2*np.pi*(97 if scene=='A' else 211)*t)+.012*rng.normal(size=len(t))
            amb*=.7+.3*np.sin(2*np.pi*.4*t)
            wav=OUT/f'_{scene}_ambience.wav';write_wav(wav,amb)
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(silent),'-i',str(wav),'-c:v','copy','-c:a','aac','-b:a','128k','-shortest','-movflags','+faststart',str(path)],check=True)
            silent.unlink();wav.unlink()
        else:silent.replace(path)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(path)]))
        (ROOT/'evidence'/f'probe_{scene}.json').write_text(json.dumps(probe,indent=2),encoding='utf-8')
        manifest['sources'].append({'id':scene,'file':path.name,'width':w,'height':h,'fps':fpsstr,'nominal_duration_seconds':dur,'audio_present':has_audio,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size,'story':['Train window and moving mountain silhouettes','Forest path; SUMMIT direction board visible from source 2.5 to 5.5 seconds; meaningful silent image','Summit flag and shared backpack traveler','Harbor, sailboat, traveler returning'][ord(scene)-65]})
        for sec in [1,3,5]:
            im=frame(scene,w,h,sec);im.thumbnail((426,260))
            tile=Image.new('RGB',(450,300),'#f5f0e4');tile.paste(im,((450-im.width)//2,10));ImageDraw.Draw(tile).text((12,276),f'{scene} / source {sec:.1f} sec',font=font(18),fill='#213c4c');thumbs.append(tile)
        print(f'generated {path.name}',flush=True)
    sheet=Image.new('RGB',(450*3,300*4),'#f5f0e4')
    for i,im in enumerate(thumbs):sheet.paste(im,((i%3)*450,(i//3)*300))
    sheet.save(ROOT/'evidence'/'independent_source_storyboard.jpg',quality=94)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('DONE',flush=True)
if __name__=='__main__':main()
