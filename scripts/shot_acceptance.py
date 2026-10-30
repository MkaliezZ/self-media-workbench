"""Actual optional-renderer/API/native-timeline acceptance with original synthetic materials."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--limit',type=int,default=0,help='Limit renders for diagnosis; not full acceptance')
    parser.add_argument('--offset',type=int,default=0,help='Start at a case index for diagnosis')
    parser.add_argument('--compact',action='store_true',help='640x360 landscape instead of 1280x720')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    os.environ['SELF_MEDIA_STATE_DIR']=str(out/'state')
    os.environ['SELF_MEDIA_DATA_DIR']=str(out/'state/projects')
    sys.path.insert(0,str(ROOT/'backend'))
    import app as w
    from fastapi.testclient import TestClient
    from PIL import Image,ImageDraw,ImageFont
    from visual_tools import font_file
    font=font_file(None)
    assets=out/'assets';assets.mkdir()
    for i,color in enumerate(('#F7F4EE','#152437')):
        im=Image.new('RGB',(1200,800),color);d=ImageDraw.Draw(im);ink='#142132' if i==0 else '#FFFFFF'
        d.text((80,80),'从问题，到可验证的行动',font=ImageFont.truetype(str(font),62),fill=ink)
        for j,text in enumerate(('明确目标','核对材料','执行与复盘')):
            x=80+j*370;d.rectangle((x,280,x+300,610),fill=('#DCEAFF' if i==0 else '#29445D'))
            d.text((x+24,330),text,font=ImageFont.truetype(str(font),42),fill=ink)
            d.text((x+24,450),str(j+1),font=ImageFont.truetype(str(font),84),fill='#E77BA3' if i else '#3778BC')
        im.save(assets/f'original-{i}.png')
    with TestClient(w.app,base_url='http://localhost') as c:
        pid=c.post('/api/projects',json={'title':'参数化镜头库实际验收','simulation':True}).json()['id'];base=f'/api/projects/{pid}'
        refs=[]
        for p in sorted(assets.glob('*.png')):
            r=c.post('/api/agent/v1/tasks',json={'task':'登记原创示意图用于动效技术验收','intent':'edit','project':pid,
                'input_paths':[str(p)],'simulation':True,'source_note':'Original synthetic teaching image; not a real account result'})
            r.raise_for_status();item=r.json()['registered'][0];refs.append({'asset_id':item['id'],'sha256':item['sha256']})
        def item(label,detail='',image=None):return {'label':label,'detail':detail,**({'image':image} if image else {})}
        shots=[
            {'kind':'typewriter-rewrite','title':'让每次表达，都有依据','subtitle':'先提出判断，再把它改得更准确','initial':'凭感觉，继续做','replacement':'看证据，决定下一步'},
            {'kind':'marker-title','title':'先让观众看懂','subtitle':'强调一个值得记住的重点'},
            {'kind':'outline-title','title':'把重点点亮','subtitle':'一次清楚的落点，胜过持续闪烁'},
            {'kind':'list-reveal','title':'把行动拆成三步','subtitle':'按理解顺序逐项展开','items':[item('明确问题','先知道要改变什么'),item('找到证据','核对已有材料'),item('执行复盘','让下一次更有依据')]},
            {'kind':'card-stack','title':'把材料组织起来','subtitle':'从多张卡片，建立一个集合','items':[item('问题',image=refs[0]),item('证据',image=refs[1]),item('行动','每一层，都有明确作用')]},
            {'kind':'before-after','title':'同一内容，两种呈现','subtitle':'原创示意图对照；不代表效果提升','before':refs[0],'after':refs[1]},
            {'kind':'line-chart','title':'让数据变化看得见','subtitle':'原创示意数据，仅用于技术验收','points':[{'label':label,'value':float(value)} for label,value in [('第一轮',12),('第二轮',18),('第三轮',15),('第四轮',27)]],'unit':'条','data_note':'Synthetic demonstration data, not observed account performance'},
            {'kind':'split-screen','title':'把不同视角放在一起','subtitle':'同时比较，帮助理解差别','items':[item('整体','先交代上下文',refs[0]),item('局部','再把焦点说清楚',refs[1])]},
            {'kind':'digit-roll','title':'让数字有一个落点','subtitle':'示意计数；不代表真实用户或收益','value':'1,280条','data_note':'Synthetic counter value for render acceptance only'},
        ]
        configurations=[('landscape',640 if args.compact else 1280,360 if args.compact else 720,25),('portrait',360,640,30)]
        cases=[(mode,width,height,fps,s) for mode,width,height,fps in configurations for s in shots]
        if not args.limit:
            cases += [('fullhd',1920,1080,30,shots[1]),('portrait-fullhd',1080,1920,25,shots[5]),('square',640,640,25,shots[3])]
        else:cases=cases[args.offset:args.offset+args.limit]
        results=[]
        for n,(mode,width,height,fps,shot) in enumerate(cases):
            rev=c.get(base).json()['revision']
            body={'request_id':f'{mode}-{shot["kind"]}','project_revision':rev,'reason':'Inspect actual motion, readable Chinese, frozen images and frame clock',
                'shot':shot,'width':width,'height':height,'fps':fps,'duration':5.}
            r=c.post(base+'/shot-renders',json=body);r.raise_for_status();queued=r.json();jid=queued['job']['id']
            deadline=time.monotonic()+1200
            while True:
                job=c.get(base+'/jobs/'+jid).json()
                if job['status'] not in ('running','queued'):break
                if time.monotonic()>deadline:raise TimeoutError(jid)
                time.sleep(.2)
            w.write(out/f'job-{n:02d}.json',job)
            if job['status']!='done':raise RuntimeError(json.dumps(job,ensure_ascii=False))
            result=job['result'];result.update(case=mode,kind=shot['kind']);results.append(result)
            w.write(out/'renders.json',results)
            # Same request returns the exact job, without registering a second media item.
            replay=c.post(base+'/shot-renders',json=body);replay.raise_for_status()
            assert replay.json()['idempotent_replay'] and replay.json()['job']['id']==jid
            source=Path(result['path']);dest=out/f'{mode}-{shot["kind"]}.jpg'
            subprocess.run(['ffmpeg','-v','error','-ss','4.4','-i',str(source),'-frames:v','1','-update','1',str(dest)],check=True,capture_output=True)
            # Decode late moving frames and the final stable hold, not only frame zero.
            raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(source),'-vf','scale=160:160','-pix_fmt','rgb24','-f','rawvideo','-'])
            import numpy as np
            v=np.frombuffer(raw,dtype=np.uint8).reshape(-1,160,160,3)
            assert len(v)==round(5*fps)
            motion=float(np.abs(v[int(.6*fps)].astype(float)-v[int(2.6*fps)].astype(float)).mean())
            hold=float(np.abs(v[-2].astype(float)-v[-fps+2].astype(float)).mean())
            assert motion>.1,(shot['kind'],'no motion',motion)
            assert hold<.5,(shot['kind'],'hold changed',hold)
            result['pixel_checks']={'motion_difference':motion,'final_hold_difference':hold}
            w.write(out/'renders.json',results)
            print(f'{n+1}/{len(cases)} {mode} {shot["kind"]}: done, {len(v)} frames, hold={hold:.3f}',flush=True)
        if args.limit:return
        # Original diagnostic tone proves independent audio mixing, not listening or narration quality.
        audio=assets/'diagnostic.wav'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=45:sample_rate=48000','-af','volume=0.05',str(audio)],check=True,capture_output=True)
        a=c.post(base+'/media',json={'path':str(audio),'media_nature':'generated','source_note':'Original diagnostic tone, not narration or music'}).json()['media']
        landscape=[r for r in results if r['case']=='landscape']
        sources=[{'id':f's{i}','kind':'media','asset_id':r['media_id'],'sha256':r['media']['sha256']} for i,r in enumerate(landscape)]
        sources.append({'id':'tone','kind':'media','asset_id':a['id'],'sha256':a['sha256']})
        plan={'request_id':'shot-library-montage','project_revision':c.get(base).json()['revision'],
            'revision_reason':'Combine actual completed shot renders through the existing native timeline',
            'intent':'Technical montage of nine parameterized adaptations; synthetic data and images',
            'sources':sources,'shots':[{'id':f'clip{i}','source_id':f's{i}','source_in':0.,'source_out':5.,'source_audio_gain':0.,'role':r['kind'],'reason':'Observe actual motion and final reading hold'} for i,r in enumerate(landscape)],
            'audio':[{'source_id':'tone','role':'effect','start':0.,'duration':45.,'gain':.2,'reason':'Check independent audio bed and decoded output'}],
            'width':1280,'height':720,'fps':25}
        r=c.post(base+'/timeline-plans',json=plan);r.raise_for_status();saved=r.json()
        r=c.post(base+'/timeline/export',json={'plan_id':saved['id']});r.raise_for_status();jid=r.json()['id']
        deadline=time.monotonic()+600
        while True:
            job=c.get(base+'/jobs/'+jid).json()
            if job['status'] not in ('queued','running'):break
            if time.monotonic()>deadline:raise TimeoutError(jid)
            time.sleep(.2)
        w.write(out/'native-timeline-job.json',job)
        if job['status']!='done':raise RuntimeError(str(job))
        import shutil
        video=w.DATA/pid/'exports'/job['result']['export_id']/'timeline.mp4'
        shutil.copyfile(video,out/'shot-library-showcase.mp4')
        # Service restart semantics: a fresh process reads project, jobs and registered generated media.
        check=subprocess.run([sys.executable,'-B','-X','utf8','-c',
            "import sys,json;sys.path.insert(0,'backend');import app as w;from fastapi.testclient import TestClient;"+
            f"c=TestClient(w.app,base_url='http://localhost');s=c.get('/api/agent/v1/projects/{pid}/context').json();"+
            "assert len(s['shot_renders'])==21;assert len(s['media'])==22;print(json.dumps({'renders':len(s['shot_renders']),'media':len(s['media'])}))"],
            cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        w.write(out/'restart-check.json',json.loads(check.stdout))
        w.write(out/'acceptance.json',{'project_id':pid,'renders':len(results),'native_timeline':str(video),
            'showcase':str(out/'shot-library-showcase.mp4'),'restart':True,'technical':'passed',
            'human_acceptance':'pending_user_review','listening':'not_performed; diagnostic tone only'})
        print('Native timeline composition and fresh-process recovery: passed',flush=True)


if __name__=='__main__':main()
