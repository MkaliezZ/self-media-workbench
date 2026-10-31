"""Render original diagrams through the public API and compose a silent native-timeline demo."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--compact',action='store_true')
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    os.environ['SELF_MEDIA_STATE_DIR']=str(out/'state')
    os.environ['SELF_MEDIA_DATA_DIR']=str(out/'state/projects')
    sys.path.insert(0,str(ROOT/'backend'))
    import app as w
    from fastapi.testclient import TestClient
    import numpy as np
    shots=[
        {'kind':'concept-network','title':'一个中心，多个服务对象','subtitle':'关系按解释顺序展开',
         'center':'内容服务','nodes':['选题','脚本','剪辑','布光'],'direction':'outward'},
        {'kind':'concept-matrix','title':'从重复现象到一个判断','subtitle':'背景降权，让结论可读',
         'label':'重复任务','rows':4,'columns':7,'conclusion':'相似任务，需要统一规则',
         'data_note':'原创图标重复示意，28个图标不代表市场规模或实际用户数'},
        {'kind':'layered-rings','title':'能力逐层增加','subtitle':'中心概念保留，逐层解释条件',
         'center':'交付能力','layers':['领域经验','资料与数据','工具与服务']},
        {'kind':'process-chain','title':'流程越长，越需要逐步验收','subtitle':'独立同概率模型示意',
         'steps':['输入','判断','处理','校验','合成','复核','交付'],
         'step_probability':.95,'independent_assumption':True,
         'data_note':'假设各环节成功率均为95%，整体为0.95^7；非实测AI成功率'},
    ]
    cases=[(mode,width,height,fps,shot) for mode,width,height,fps in
        [('landscape',640 if args.compact else 1280,360 if args.compact else 720,25),
         ('portrait',360,640,30),('square',640,640,25)] for shot in shots]
    cases += [('failure',1280,720,25,{'kind':'process-chain','title':'局部失败，结果可能偏离',
        'steps':['设计','制造','配送'],'fail_step':2,'data_note':'原创失败分支示意，非真实事故'}),
        ('plain',1280,720,30,{'kind':'process-chain','title':'完整的交付链路','steps':['设计','制造','配送']})]
    with TestClient(w.app,base_url='http://localhost') as c:
        pid=c.post('/api/projects',json={'title':'原创解释型图解技术验收','simulation':True}).json()['id']
        base=f'/api/projects/{pid}';results=[]
        for i,(mode,width,height,fps,shot) in enumerate(cases):
            body={'request_id':f'diagram-{i}','project_revision':c.get(base).json()['revision'],
                'reason':'Original synthetic content; inspect diagram semantics, motion, readability and stable hold',
                'shot':shot,'width':width,'height':height,'fps':fps,'duration':6.}
            response=c.post(base+'/shot-renders',json=body)
            w.write(out/f'request-{i:02}.json',{'request':body,'status_code':response.status_code,'response':response.json()})
            response.raise_for_status();jid=response.json()['job']['id'];deadline=time.monotonic()+1200
            while True:
                job=c.get(base+'/jobs/'+jid).json()
                if job['status'] not in ('queued','running'):break
                if time.monotonic()>deadline:raise TimeoutError(jid)
                time.sleep(.3)
            w.write(out/f'job-{i:02}.json',job)
            if job['status']!='done':raise RuntimeError(json.dumps(job,ensure_ascii=False))
            result=job['result'];source=Path(result['path'])
            frames=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(source),
                '-vf','scale=160:160','-pix_fmt','rgb24','-f','rawvideo','-']),dtype=np.uint8).reshape(-1,160,160,3)
            motion=float(np.abs(frames[int(.6*fps)].astype(float)-frames[int(3.8*fps)].astype(float)).mean())
            hold=float(np.abs(frames[-2].astype(float)-frames[-fps+2].astype(float)).mean())
            assert len(frames)==6*fps and motion>.1 and hold<.5,(mode,shot['kind'],motion,hold)
            for seconds in (.6,2.8,5.5):
                subprocess.run(['ffmpeg','-v','error','-ss',str(seconds),'-i',str(source),'-frames:v','1',
                    '-update','1',str(out/f'{mode}-{shot["kind"]}-{seconds}.jpg')],check=True,capture_output=True)
            record=w.read(Path(result['record_path']))
            assert record['implementation_origin']=='original_native' and record['native_definition']['id']==shot['kind']
            replay=c.post(base+'/shot-renders',json=body);replay.raise_for_status()
            assert replay.json()['idempotent_replay'] and replay.json()['job']['id']==jid
            result.update(case=mode,kind=shot['kind'],motion_difference=motion,hold_difference=hold)
            results.append(result);w.write(out/'renders.json',results)
            print(f'{i+1}/{len(cases)} {mode} {shot["kind"]}: {len(frames)} frames; hold={hold:.3f}',flush=True)
        landscape=[r for r in results if r['case']=='landscape']
        plan={'request_id':'diagram-montage','project_revision':c.get(base).json()['revision'],
            'revision_reason':'Compose four actually completed original diagram renders',
            'intent':'Original silent explanatory diagram technical demo; not a source-video replica',
            'sources':[{'id':f's{i}','kind':'media','asset_id':r['media_id'],'sha256':r['media']['sha256']} for i,r in enumerate(landscape)],
            'shots':[{'id':f'clip{i}','source_id':f's{i}','source_in':0.,'source_out':6.,'source_audio_gain':0.,
                'role':r['kind'],'reason':'Demonstrate an original reusable explanatory mechanism'} for i,r in enumerate(landscape)],
            'width':640 if args.compact else 1280,'height':360 if args.compact else 720,'fps':25}
        response=c.post(base+'/timeline-plans',json=plan);response.raise_for_status();saved=response.json()
        response=c.post(base+'/timeline/export',json={'plan_id':saved['id']});response.raise_for_status();jid=response.json()['id']
        deadline=time.monotonic()+600
        while True:
            job=c.get(base+'/jobs/'+jid).json()
            if job['status'] not in ('running','queued'):break
            if time.monotonic()>deadline:raise TimeoutError(jid)
            time.sleep(.3)
        w.write(out/'native-timeline-job.json',job)
        if job['status']!='done':raise RuntimeError(str(job))
        source=w.DATA/pid/'exports'/job['result']['export_id']/'timeline.mp4'
        subprocess.run(['ffmpeg','-v','error','-i',str(source),'-an','-c:v','copy',str(out/'explanatory-diagrams-silent.mp4')],check=True)
        # Fresh-process read verifies persisted generated-media/render records.
        check=subprocess.run([sys.executable,'-B','-X','utf8','-c',
            "import sys;sys.path.insert(0,'backend');import app as w;from fastapi.testclient import TestClient;"+
            f"c=TestClient(w.app,base_url='http://localhost');s=c.get('/api/agent/v1/projects/{pid}/context').json();"+
            "assert len(s['shot_renders'])==14;assert len(s['media'])==14;print('14 persisted render/media records')"],
            cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        w.write(out/'acceptance.json',{'project_id':pid,'renders':len(results),'technical':'passed',
            'montage':str(out/'explanatory-diagrams-silent.mp4'),'restart_check':check.stdout.strip(),
            'human_acceptance':'pending_user_review','listening':'not_applicable; silent diagrams'})
        print('Native 24-second montage and fresh-process persistence: passed',flush=True)


if __name__=='__main__':main()
