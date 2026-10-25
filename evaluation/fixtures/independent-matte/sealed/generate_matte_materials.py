"""New original deep-sea material and orthogonal alpha/luma calibration masks.
No workbench/showcase/test imports. Images/animation/audio are synthetic.
"""
from pathlib import Path
import hashlib,json,math,subprocess,wave
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent;OUT=ROOT/'materials';OUT.mkdir(exist_ok=True)
FONT=Path('C:/Windows/Fonts/msyh.ttc')
def ft(n):return ImageFont.truetype(str(FONT),n)
def text(d,xy,s,n=26,c='#e4eff1'):d.text(xy,s,font=ft(n),fill=c)
def video_frame(t):
    w,h=960,600;im=Image.new('RGB',(w,h),'#267e91');d=ImageDraw.Draw(im)
    d.rectangle((0,190,w,390),fill='#1d697f');d.rectangle((0,390,w,h),fill='#124f6b')
    for j in range(22):
        x=(j*127+t*11)%w;y=45+(j*71)%500;d.ellipse((x,y,x+4,y+4),fill='#8fd5ca')
    for j in range(5):
        x=(170*j+t*27)%w;y=175+j*52;d.polygon([(x,y),(x+28,y-11),(x+28,y+11)],fill='#85bdb5')
    # The rover has a deterministic motion and a clearly distinct warm colour.
    x=80+((t*37)%760);y=295+62*math.sin(t*.7)
    d.rounded_rectangle((x,y,x+100,y+55),radius=15,fill='#f0a251',outline='#ffe1a4',width=4)
    d.ellipse((x+15,y+10,x+47,y+42),fill='#263f60',outline='#ffe5aa',width=3)
    d.line((x+76,y,x+76,y-28),fill='#ffd898',width=4);d.line((x+18,y+57,x+6,y+76,x+106,y+76,x+94,y+57),fill='#ffca83',width=4)
    text(d,(30,24),'自制深海观测动画',30)
    d.rectangle((0,552,w,h),fill='#082d45');text(d,(24,564),f'DEEP SOURCE {t:05.2f}s / SYNTHETIC, NOT REAL FOOTAGE',22)
    return im
def main():
    bg=Image.new('RGB',(1280,720),'#152a3d');d=ImageDraw.Draw(bg)
    d.rectangle((0,0,1280,74),fill='#0e1e31');text(d,(34,18),'深海观测窗口 · 原创遮罩实验',30);text(d,(34,670),'全部画面、界面及声音为自制演示，不是真实深海拍摄或观测数据。',20,'#a6bec8')
    for x in range(80,1230,80):d.line((x,90,x,638),fill='#29475a',width=1)
    for y in range(120,640,80):d.line((40,y,1240,y),fill='#29475a',width=1)
    # Keep the static calibration window completely flat for inverse alpha.
    d.rectangle((384,104,895,615),fill='#152a3d');text(d,(46,100),'A / 原画面通过遮罩显示',21);text(d,(940,120),'RGB 与 Alpha 独立',21);text(d,(940,174),'黑色不必透明',21);text(d,(940,228),'白色不必不透明',21)
    bg.save(OUT/'deep_background.png')
    size=512;yy,xx=np.mgrid[:size,:size];bands=np.minimum(xx//128,3);levels=np.array([0,64,128,255],dtype=np.uint8)
    alpha=levels[bands].copy();alpha[(xx-256)**2+(yy-256)**2<55**2]=0
    rgb=np.where(((yy//64)%2)[...,None]==0,0,255).astype(np.uint8);rgb=np.repeat(rgb,3,axis=2)
    rgba=np.dstack((rgb,alpha));Image.fromarray(rgba,'RGBA').save(OUT/'independent_alpha_bands.png')
    grey=levels[bands];Image.fromarray(np.dstack((grey,grey,grey,np.full_like(grey,255))),'RGBA').save(OUT/'independent_luma_bands.png')
    distance=np.sqrt((xx-255.5)**2+(yy-255.5)**2);circle=np.uint8(np.clip((256-distance)/38.4,0,1)*255)
    Image.fromarray(np.dstack((np.full_like(circle,233),np.full_like(circle,61),np.full_like(circle,178),circle)),'RGBA').save(OUT/'independent_feather_circle.png')
    # Transparent magenta RGB is deliberately retained under the PNG hole.
    fore=Image.new('RGBA',(640,640),(255,0,255,0));fd=ImageDraw.Draw(fore)
    fd.rounded_rectangle((20,20,620,620),radius=40,fill='#e4a45c',outline='#ffdeb0',width=8)
    fd.ellipse((140,140,500,500),fill=(255,0,255,0))
    fd.rectangle((306,105,334,535),fill='#71452e');fd.rectangle((105,306,535,334),fill='#71452e')
    text(fd,(100,45),'前景观察框',42,'#382f32');text(fd,(106,548),'透明洞 / 遮挡梁',36,'#382f32')
    fore.save(OUT/'independent_foreground_hole.png')
    target=OUT/'deep_rover_960x600_25fps.mp4';p=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s','960x600','-r','25','-i','pipe:0','-an','-c:v','libx264','-crf','18','-preset','fast','-pix_fmt','yuv420p',str(target)],stdin=subprocess.PIPE)
    for n in range(600):p.stdin.write(video_frame(n/25).tobytes())
    p.stdin.close()
    if p.wait():raise RuntimeError('Video generation failed')
    sr=48000;t=np.arange(20*sr)/sr;audio=.028*np.sin(2*np.pi*(180*t+7.3*t*t))*(.8+.2*np.sin(2*np.pi*.37*t))
    with wave.open(str(OUT/'deep_original_clock.wav'),'wb') as f:f.setnchannels(2);f.setsampwidth(2);f.setframerate(sr);f.writeframes((np.column_stack((audio,audio))*32767).astype('<i2').tobytes())
    calibration={'nature':'Original synthetic deep-sea observation illustration/animation/audio; not real filmed or measured data','canvas':[1280,720],'fps':30,'duration':20,'frames':600,'background_rgb':[21,42,61],'static_slot':[384,104,512,512],'source_video_crop_pixels':[180,0,600,600],'alpha_bands':[0,64/255,128/255,1],'alpha_matte_rgb':'Alternating horizontal pure black/white stripes, independent of alpha','alpha_hole':{'centre':[256,256],'radius':55,'alpha':0},'luma_bands':[0,64/255,128/255,1],'luma_alpha':1,'static_probe_local_points':[[64,32],[192,32],[320,32],[448,32],[64,96],[448,96],[256,256]],'moving_slot':{'from':[100,280,320,320],'to':[800,120,320,320],'enter_seconds':3.5,'hold_seconds':.5,'easing':'smoothstep','source_in':16},'circle_matte':{'radius_source_px':256,'inward_feather_source_px':38.4,'inward_feather_at_320_output_px':24},'foreground_slot':[460,160,360,360],'foreground_hole_centre_output':[640,340],'foreground_transparent_rgb':[255,0,255],'foreground_cross_beam_local_pixels':[[306,105,334,535],[105,306,535,334]],'mode_probe_output_times':[2,6,10,14,18]}
    (OUT/'matte_calibration.json').write_text(json.dumps(calibration,ensure_ascii=False,indent=2),encoding='utf-8')
    manifest={'nature':calibration['nature'],'files':{z.name:{'sha256':hashlib.sha256(z.read_bytes()).hexdigest(),'bytes':z.stat().st_size} for z in sorted(OUT.glob('*')) if z.is_file()}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(target)]));(ROOT/'evidence'/'source-video-probe.json').write_text(json.dumps(probe,indent=2),encoding='utf-8');subprocess.run(['ffmpeg','-v','error','-i',str(target),'-f','null','-'],check=True)
    views=[bg,video_frame(8),Image.open(OUT/'independent_alpha_bands.png'),Image.open(OUT/'independent_luma_bands.png'),Image.open(OUT/'independent_feather_circle.png'),fore];sheet=Image.new('RGB',(1280,1110),'#dce6e9')
    for k,im in enumerate(views):
        base=Image.new('RGBA',im.size,'#9fadb3');base.alpha_composite(im.convert('RGBA'));base=base.convert('RGB');base.thumbnail((620,340));x,y=(k%2)*640,(k//2)*370;sheet.paste(base,(x+(640-base.width)//2,y));ImageDraw.Draw(sheet).text((x+10,y+347),['BACKGROUND','NEW SOURCE VIDEO','ALPHA MASK: RGB DOES NOT DEFINE ALPHA','OPAQUE LUMA MASK','FEATHER CIRCLE: MAGENTA RGB','PNG HOLE AND OCCLUSION CROSS'][k],font=ft(14),fill='#14364b')
    sheet.save(ROOT/'evidence'/'new-matte-source-storyboard.jpg',quality=95);print('NEW MATTE MATERIALS READY')
if __name__=='__main__':main()
