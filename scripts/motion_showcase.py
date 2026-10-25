"""Reproducible technical-effect film, original documents/UI and optional local video."""
import argparse,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main(out,video=None):
    out=out.resolve();out.mkdir(parents=True,exist_ok=False);assets=out/'assets';assets.mkdir()
    os.environ['SELF_MEDIA_STATE_DIR']=str(out/'state');os.environ['SELF_MEDIA_DATA_DIR']=str(out/'state/projects')
    sys.path.insert(0,str(ROOT/'backend'))
    from PIL import Image,ImageDraw,ImageFont
    from fastapi.testclient import TestClient
    import app as w
    from visual_tools import font_file,sha
    font=font_file(None);W,H,FPS=1920,1080,25
    def f(size):return ImageFont.truetype(str(font),size)
    def rect(x,y,width,height):return {'x':float(x),'y':float(y),'width':float(width),'height':float(height)}
    def text(d,xy,t,size=42,fill='#212c3a'):d.text(xy,t,font=f(size),fill=fill)
    lines=['一条视频要解决一个明确的问题。','主画面负责展示过程，字幕负责帮助理解。','强调的对象必须来自真实材料，不能靠装饰替代证据。',
        '当观众需要阅读一段资料时，先定位原文，','再标出重点，随后把关键段落抽离、放大。','背景应当退后，重点才能真正被看见。',
        '动效的目的，是引导注意力，而不是遮挡信息。','文章、截图和口播中的每一项修改，都需要保留版本。']
    page=Image.new('RGB',(1400,1800),'#fffef9');d=ImageDraw.Draw(page)
    text(d,(110,145),'短视频剪辑中的信息层级',64);text(d,(110,255),'教学示例 · 原创文本 · 非外部报道',30,'#76808a')
    lineboxes=[]
    for i,line in enumerate(lines):
        y=400+i*86;text(d,(110,y),line,40);bbox=d.textbbox((110,y),line,font=f(40));lineboxes.append(bbox)
    d.line((110,1240,1290,1240),fill='#cbd0d4',width=2);text(d,(110,1290),'原文的内容与坐标，是效果可复用的基础。',35,'#76808a');page.save(assets/'article.png')
    (assets/'article.txt').write_text('短视频剪辑中的信息层级\n\n'+'\n'.join(lines),'utf-8')
    selected=lineboxes[3:5];x=min(b[0] for b in selected)-16;y=min(b[1] for b in selected)-10;x2=max(b[2] for b in selected)+16;y2=max(b[3] for b in selected)+10
    selection=rect(x/1400,y/1800,(x2-x)/1400,(y2-y)/1800)
    highlights=[rect((b[0]-4)/1400,(b[1]-2)/1800,(b[2]-b[0]+8)/1400,(b[3]-b[1]+4)/1800) for b in selected]
    source_layout={'text':lines,'line_boxes':lineboxes,'selected_quote':'\n'.join(lines[3:5]),'source_rect':selection,'highlights':highlights,'scope':'Original generated typesetting with known glyph bounds; not automatic OCR'}
    (assets/'article-layout.json').write_text(json.dumps(source_layout,ensure_ascii=False,indent=2),'utf-8')
    im=Image.new('RGB',(W,H),'#e9edf3');d=ImageDraw.Draw(im);text(d,(120,100),'项目状态检查',78);text(d,(120,210),'界面示例：没有真实账号指标或发布数据',32,'#707e8e')
    for i,(title,status,note) in enumerate([('选题','已保存','有依据的选题进入创作'),('脚本','待复核','关键句与资料一一对应'),('剪辑','可恢复','原件与旧版本分别保留')]):
        xx=120+i*570;d.rounded_rectangle((xx,340,xx+510,800),24,fill='white',outline='#bdc8d5',width=3)
        text(d,(xx+40,390),title,62);text(d,(xx+40,540),status,56,'#356ddd');text(d,(xx+40,670),note,30,'#687b90')
    im.save(assets/'dashboard.png')
    for name,title,sub in [('dark','实际演示，不靠口头宣称','原始素材 → 操作过程 → 最终效果'),('pip','画中画入场','视频继续播放，同时控制位置、尺寸、旋转和透明度'),('text','重点文案动效','这里的文字时间由作者编排，不冒充逐字声学对齐'),('reveal','线性蒙版揭示','同一张图，横向与纵向逐步揭示'),('end','换一段文章，效果仍能复用','原文坐标 · 明确关键帧 · 原件与版本保留')]:
        im=Image.new('RGB',(W,H),'#101825');d=ImageDraw.Draw(im)
        for xx in range(0,W,80):d.line((xx,0,xx,H),fill='#172336')
        for yy in range(0,H,80):d.line((0,yy,W,yy),fill='#172336')
        if name!='dark':text(d,(115,120),title,78,'#f1f5fa');text(d,(120,235),sub,31,'#94aac6')
        im.save(assets/(name+'.png'))
    if video:
        video=video.resolve();shutil.copyfile(video,assets/'moving-source.mp4');source_nature='recorded';note='Existing locally licensed stock video; separately designed source, not a new personal recording'
    else:
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=1280x720:r=24:d=9','-c:v','libx264','-pix_fmt','yuv420p',str(assets/'moving-source.mp4')],check=True,capture_output=True);source_nature='generated';note='Original generated diagnostic moving pattern; not real filming'
    with TestClient(w.app,base_url='http://localhost') as c:
        p=c.post('/api/projects',json={'title':'常用视频特效：技术展示v03','simulation':True}).json();pid=p['id'];base=f'/api/projects/{pid}';refs={}
        for name in ['article','dashboard','dark','pip','text','reveal','end']:
            r=c.post('/api/agent/v1/tasks',json={'task':'继续原生技术特效展示','intent':'edit','project':pid,'input_paths':[str(assets/(name+'.png'))],'source_note':'Original teaching document or illustrative UI, no actual account metrics','usage_scope':'technical capability film','simulation':True});r.raise_for_status();item=r.json()['registered'][0];refs[name]={'id':name,'kind':'image','asset_id':item['id'],'sha256':item['sha256']}
        r=c.post(base+'/media',json={'path':str(assets/'moving-source.mp4'),'media_nature':source_nature,'source_note':note,'usage_scope':'technical effect demonstration'});r.raise_for_status();item=r.json()['media'];refs['moving']={'id':'moving','kind':'media','asset_id':item['id'],'sha256':item['sha256']}
        effects=[{'kind':'document_extract','source_id':'article','source_rect':selection,'highlights':highlights,'page_quad':[{'x':x,'y':y} for x,y in [(.31,.07),(.73,.14),(.65,.91),(.23,.84)]],
            'target_rect':rect(.08,.30,.84,.40),'quote':'\n'.join(lines[3:5]),'start':.2,'end':13.8,'reveal_seconds':1.0,'highlight_seconds':1.5,'lift_seconds':1.1,'return_seconds':1.1,'reason':'Highlight the actual article lines, detach their pixels, rectify to a front-facing readable card, then return to the source'},
            {'kind':'spotlight','start':14.3,'end':21.7,'from_rect':rect(.055,.30,.285,.45),'to_rect':rect(.65,.30,.285,.45),'fade_seconds':.4,'dim':.78,'feather':22,'reason':'Authored spotlight scan between actual UI cards; no object tracking'},
            {'kind':'motion_layer','source_id':'dashboard','crop':rect(.35,.30,.29,.45),'start':22.3,'end':29.7,'from_rect':rect(.35,.30,.29,.45),'to_rect':rect(.24,.08,.52,.807),'enter_seconds':1.0,'exit_seconds':.5,'dim':.65,'shadow':True,'reason':'Lift and enlarge actual screenshot pixels without redrawing the UI'},
            {'kind':'motion_layer','source_id':'moving','source_in':.5,'start':30.3,'end':37.7,'from_rect':rect(.025,.60,.22,.22),'to_rect':rect(.46,.34,.49,.49),'from_angle':-9.,'to_angle':0.,'enter_seconds':1.2,'exit_seconds':.5,'opacity':1.,'reason':'A moving video slides in, enlarges, rotates upright and continues playing'},
            {'kind':'motion_text','text':'把「重要」\n真正摆到前面','accent':'重要','start':38.3,'end':43.7,'slot':rect(.12,.33,.76,.47),'font_height':.105,'animation':'pop','enter_seconds':.75,'exit_seconds':.4,'reason':'Authored text scale/fade with the actual important substring coloured'},
            {'kind':'motion_layer','source_id':'dashboard','start':44.3,'end':47.8,'from_rect':rect(.19,.30,.62,.62),'to_rect':rect(.19,.30,.62,.62),'animation':'reveal_left','enter_seconds':1.5,'exit_seconds':.3,'shadow':False,'reason':'Real linear alpha reveal from left to right'},
            {'kind':'motion_layer','source_id':'dashboard','start':48.,'end':51.7,'from_rect':rect(.19,.30,.62,.62),'to_rect':rect(.19,.30,.62,.62),'animation':'reveal_up','enter_seconds':1.5,'exit_seconds':.3,'shadow':False,'reason':'The same actual image revealed along the vertical axis'}]
        scenes=[('dark',14.),('dashboard',8.),('dashboard',8.),('pip',8.),('text',6.),('reveal',8.),('end',4.)]
        body={'request_id':'technical-motion-v03','project_revision':c.get(f'/api/agent/v1/projects/{pid}/context').json()['project']['revision'],'revision_reason':'Implement the missing dynamic reading/compositing functions, instead of substituting better photography','intent':'Actual functional demonstration: article highlight/extract/rectify/return, moving focus, magnification, video PiP, kinetic text and animated masks','width':W,'height':H,'fps':FPS,'font_path':str(font),'sources':list(refs.values()),
            'shots':[{'id':'shot'+str(i),'source_id':name,'source_in':0.,'source_out':duration,'source_audio_gain':0.,'role':'demonstration','reason':'Clear technical-effect stage'} for i,(name,duration) in enumerate(scenes)],'effects':effects,
            'titles':[{'text':'01 文章标黄 → 段落抽离 → 放大并正向展示 → 收回原位','start':0.,'end':14.,'font_height':.033,'bottom_margin':.035},
                {'text':'02 移动聚光灯：非重点压暗，按关键帧切换关注区域','start':14.,'end':22.,'font_height':.033,'bottom_margin':.035},
                {'text':'03 局部放大：裁切原图像素，拉近后保持可读','start':22.,'end':30.,'font_height':.033,'bottom_margin':.035}]}
        r=c.post(base+'/timeline-plans',json=body);(out/'save-response.json').write_text(json.dumps({'status':r.status_code,'body':r.json()},ensure_ascii=False,indent=2),'utf-8');r.raise_for_status();record=r.json();(out/'plan.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),'utf-8')
        r=c.post(base+'/timeline/export',json={'plan_id':record['id']});r.raise_for_status();job=r.json();deadline=time.monotonic()+2400
        while job['status'] not in ('done','failed') and time.monotonic()<deadline:time.sleep(.5);job=c.get(base+'/jobs/'+job['id']).json()
        (out/'job.json').write_text(json.dumps(job,ensure_ascii=False,indent=2),'utf-8')
        if job['status']!='done':raise RuntimeError(job)
        directory=w.DATA/pid/'exports'/job['result']['export_id'];shutil.copyfile(directory/'timeline.mp4',out/'常用视频特效-技术展示-v03.mp4')
        (out/'result.json').write_text(json.dumps({'project_id':pid,'video':str(out/'常用视频特效-技术展示-v03.mp4'),'directory':str(directory),'verification':w.read(directory/'timeline-verification.json'),'scope':'Actual native effect execution with authored source geometry; no generative images, OCR certification or automatic tracking'},ensure_ascii=False,indent=2),'utf-8')
        print(str(out/'常用视频特效-技术展示-v03.mp4'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--video',type=Path);a=p.parse_args();main(a.out,a.video)
