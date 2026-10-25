"""Native reusable mask/matte/occlusion demonstration. All imagery is authored or supplied."""
import argparse,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main(out,video=None,width=1280):
    out=out.resolve();out.mkdir(parents=True,exist_ok=False);assets=out/'assets';assets.mkdir()
    os.environ['SELF_MEDIA_STATE_DIR']=str(out/'state');os.environ['SELF_MEDIA_DATA_DIR']=str(out/'state/projects')
    sys.path.insert(0,str(ROOT/'backend'))
    from PIL import Image,ImageDraw,ImageFont
    from fastapi.testclient import TestClient
    import app as w
    from visual_tools import font_file
    font=font_file(None);W,H=1600,900
    def f(s):return ImageFont.truetype(str(font),s)
    def rect(x,y,width,height):return {'x':float(x),'y':float(y),'width':float(width),'height':float(height)}
    def label(im,xy,text,size,fill):ImageDraw.Draw(im).text(xy,text,font=f(size),fill=fill)
    stages=[('alpha','01 / ALPHA','让真实视频，流进文字'),('luma','02 / LUMA','亮度决定哪里可见'),('inverse','03 / INVERT','同一遮罩，一键反向'),
        ('circle','04 / FEATHER','圆形视频窗口，带着焦点移动'),('split','05 / SPLIT','两段画面，分屏揭示'),('occlusion','06 / OCCLUSION','透明洞 + 前后图层遮挡')]
    for name,tag,title in stages+[('outro','NATIVE / REUSABLE','每个效果，都有素材与动作记录')]:
        im=Image.new('RGB',(W,H),'#0b1423');d=ImageDraw.Draw(im)
        for x in range(0,W,80):d.line((x,0,x,H),fill='#12243a')
        for y in range(0,H,80):d.line((0,y,W,y),fill='#12243a')
        label(im,(75,50),tag,28,'#49dbc9');label(im,(75,105),title,62,'#f6f5ef')
        if name in ('luma','inverse'):label(im,(100,315),'遮罩',30,'#9caec5');label(im,(600,240),'实际视频结果',30,'#9caec5')
        if name=='circle':d.line((150,520,1450,520),fill='#336485',width=3)
        im.save(assets/(name+'.png'))
    mask=Image.new('RGBA',(W,H));d=ImageDraw.Draw(mask);word='MASK';font_big=f(450);bbox=d.textbbox((0,0),word,font=font_big,stroke_width=4)
    d.text(((W-(bbox[2]-bbox[0]))/2-bbox[0],(H-(bbox[3]-bbox[1]))/2-bbox[1]),word,font=font_big,fill='white',stroke_width=4,stroke_fill='white');mask.save(assets/'type-alpha.png')
    mask=Image.new('RGB',(W,H),'black');d=ImageDraw.Draw(mask)
    for x in [0,530,1060]:d.polygon([(x+140,70),(x+460,70),(x+140,830),(x-180,830)],fill='white')
    mask.save(assets/'bands-luma.png')
    frame=Image.new('RGBA',(W,H));d=ImageDraw.Draw(frame);d.rounded_rectangle((90,80,1510,820),50,fill='#0f2339',outline='#51e5cd',width=15)
    d.rectangle((180,170,1420,730),fill=(0,0,0,0));d.rectangle((760,150,840,750),fill='#51e5cd');frame.save(assets/'foreground-alpha.png')
    for name,colour,word in [('cyan','#23c7bd','CIRCLE'),('pink','#e94780','WIPE')]:
        im=Image.new('RGB',(W,H),colour);label(im,(110,330),word,240,'#101c29');im.save(assets/(name+'.png'))
    if video:
        shutil.copyfile(video.resolve(),assets/'moving.mp4');nature='recorded';note='Existing authorized local stock video, not a new personal recording'
    else:
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=1280x720:r=30:d=9','-c:v','libx264','-pix_fmt','yuv420p',str(assets/'moving.mp4')],check=True,capture_output=True);nature='generated';note='Original diagnostic moving video, not filmed footage'
    def moving(kind,start,end,frm,to,reason,**kwargs):return {'kind':kind,'source_id':'moving','start':start,'end':end,'from_rect':frm,'to_rect':to,'enter_seconds':.7,'exit_seconds':.3,'shadow':False,'reason':reason,**kwargs}
    with TestClient(w.app,base_url='http://localhost') as c:
        pid=c.post('/api/projects',json={'title':'常用蒙版、轨道遮罩与转场实测','simulation':True}).json()['id'];base=f'/api/projects/{pid}';refs={}
        for file in assets.glob('*.png'):
            r=c.post('/api/agent/v1/tasks',json={'task':'原生蒙版遮罩技术展示','intent':'edit','project':pid,'input_paths':[str(file)],'simulation':True,'source_note':'Original programmatically authored teaching graphic; not external evidence'});r.raise_for_status();item=r.json()['registered'][0];refs[file.stem]={'id':file.stem,'kind':'image','asset_id':item['id'],'sha256':item['sha256']}
        r=c.post(base+'/media',json={'path':str(assets/'moving.mp4'),'media_nature':nature,'source_note':note,'usage_scope':'Native technical-effect demonstration'});r.raise_for_status();item=r.json()['media'];refs['moving']={'id':'moving','kind':'media','asset_id':item['id'],'sha256':item['sha256']}
        effects=[moving('track_matte',.1,4.9,rect(.08,.25,.84,.60),rect(.03,.22,.94,.67),'Actual moving video through real alpha text pixels',matte_id='type-alpha',matte_mode='alpha',animation='pop'),
            moving('track_matte',5.1,9.9,rect(.36,.30,.60,.60),rect(.36,.30,.60,.60),'Actual video through white luma bands',matte_id='bands-luma',matte_mode='luma'),
            moving('track_matte',10.1,14.9,rect(.36,.30,.60,.60),rect(.36,.30,.60,.60),'Complementary inverted luma mask',matte_id='bands-luma',matte_mode='luma',invert=True),
            moving('motion_layer',15.1,19.9,rect(.03,.35,.27,.48),rect(.70,.35,.27,.48),'Actual video in a moving circular feathered window',shape='ellipse',feather=16),
            moving('motion_layer',20.1,24.9,rect(.02,.57,.20,.20),rect(.02,.33,.46,.46),'First source interval opens on left',animation='reveal_left'),
            moving('motion_layer',20.1,24.9,rect(.77,.57,.20,.20),rect(.52,.33,.46,.46),'Second actual source interval opens on right',animation='reveal_up',source_in=3.),
            moving('motion_layer',25.1,29.9,rect(.05,.35,.50,.50),rect(.45,.35,.50,.50),'Moving video underneath a real foreground alpha cutout'),
            {'kind':'motion_layer','source_id':'foreground-alpha','start':25.,'end':30.,'from_rect':rect(.25,.30,.50,.50),'to_rect':rect(.25,.30,.50,.50),'enter_seconds':.3,'exit_seconds':.2,'shadow':False,'reason':'Foreground panel and bar occlude video, real transparent hole reveals lower pixels'}]
        effects[3]['enter_seconds']=3.5;effects[3]['crop']=rect(.21875,0.,.5625,1.);effects[6]['enter_seconds']=3.5
        for start in [5.,10.]:effects.append({'kind':'motion_layer','source_id':'bands-luma','start':start+.1,'end':start+4.9,'from_rect':rect(.05,.42,.25,.25),'to_rect':rect(.05,.42,.25,.25),'enter_seconds':.3,'exit_seconds':.2,'shadow':False,'reason':'Display the actual luma matte beside its resulting video'})
        scenes=[(s[0],5.,0.) for s in stages]+[('cyan',3.,0.),('pink',3.,0.),('moving',3.,1.),('outro',2.,0.)]
        height=width*9//16
        body={'request_id':'native-mask-technique-showcase','project_revision':c.get(f'/api/agent/v1/projects/{pid}/context').json()['project']['revision'],'revision_reason':'Demonstrate common reusable mask and matte mechanisms in actual motion','intent':'Alpha/luma/inverse track matte, feathered moving circle, split reveal, foreground alpha occlusion, real circle/wipe transitions','width':width,'height':height,'fps':25,'font_path':str(font),'sources':list(refs.values()),
            'shots':[{'id':'s'+str(i),'source_id':name,'source_in':offset,'source_out':offset+duration,'source_audio_gain':0.,'role':'technical demonstration','reason':'Explicit before/matte/result action stage'} for i,(name,duration,offset) in enumerate(scenes)],
            'effects':effects,'transitions':[{'after_shot_id':'s6','kind':'circleopen','duration':.6,'reason':'Clearly visible circular opening between distinct graphic stages'},{'after_shot_id':'s7','kind':'wipeleft','duration':.6,'reason':'Directional reveal from the graphic to actual moving video'}],
            'titles':[{'text':title,'start':i*5.,'end':(i+1)*5.,'font_height':.028,'bottom_margin':.025} for i,title in enumerate(['Alpha：真实视频填充文字，字形外保持透明','Luma：白色显示视频，黑色隐藏视频','反向遮罩：显示区域与上一段互补','椭圆蒙版 + 羽化 + 位移，视频持续播放','同一源的两个时间段：分别位移与蒙版揭示','真正的图层关系：前景遮挡，透明洞显示后层'])]+[{'text':'圆形展开 → 方向擦拭；转场重叠已计入真实帧数','start':30.,'end':37.8,'font_height':.028,'bottom_margin':.025}]}
        r=c.post(base+'/timeline-plans',json=body);(out/'save-response.json').write_text(json.dumps({'status':r.status_code,'body':r.json()},ensure_ascii=False,indent=2),'utf-8');r.raise_for_status();record=r.json();(out/'plan.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
        r=c.post(base+'/timeline/export',json={'plan_id':record['id']});r.raise_for_status();job=r.json();deadline=time.monotonic()+1800
        while job['status'] not in ('done','failed') and time.monotonic()<deadline:time.sleep(.5);job=c.get(base+'/jobs/'+job['id']).json()
        (out/'job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2),'utf-8')
        if job['status']!='done':raise RuntimeError(job)
        directory=w.DATA/pid/'exports'/job['result']['export_id'];shutil.copyfile(directory/'timeline.mp4',out/'蒙版遮罩与转场-技术展示.mp4')
        (out/'result.json').write_text(json.dumps({'project_id':pid,'directory':str(directory),'verification':w.read(directory/'timeline-verification.json'),'scope':note+'; original procedural alpha/luma graphics, no image generation or automatic matting'},ensure_ascii=False,indent=2),'utf-8')
        print(out/'蒙版遮罩与转场-技术展示.mp4')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--video',type=Path);p.add_argument('--width',type=int,choices=[1280,1920],default=1280);a=p.parse_args();main(a.out,a.video,a.width)
