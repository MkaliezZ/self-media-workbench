"""Run actual HTTP travel timeline and restart/resume on native Windows/macOS."""
import argparse
import copy
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main(out):
    out=out.resolve();out.mkdir(parents=True,exist_ok=True)
    os.environ['SELF_MEDIA_STATE_DIR']=str(out/'state')
    # Isolate from any pre-existing user overrides on a developer machine.
    os.environ['SELF_MEDIA_DATA_DIR']=str(out/'state/projects')
    import workbench
    from timeline_case import exercise
    base=workbench.ensure_service()
    location=next((workbench.STATE/'services').glob('*.json'))
    def stop_owned():
        info=json.loads(location.read_text('utf-8'))
        assert Path(workbench.request(info['base_url'],'GET','/api/status')['root']).resolve()==ROOT
        for p in workbench.request(info['base_url'],'GET','/api/projects'):
            assert not any(j['status'] in ('queued','running') for j in workbench.request(info['base_url'],'GET',f"/api/projects/{p['id']}/jobs"))
        os.kill(info['pid'],signal.SIGTERM)
        for _ in range(50):
            try:workbench.request(info['base_url'],'GET','/api/status')
            except OSError:return
            time.sleep(.1)
        raise RuntimeError('Owned service did not stop')
    try:
        with httpx.Client(base_url=base,timeout=120) as client:
            case=exercise(client,out);pid=case['project_id']
            export=workbench.DATA/pid/'exports'/case['job']['result']['export_id']/'timeline.mp4'
            subprocess.run(['ffmpeg','-v','error','-i',str(export),'-f','null','-'],check=True,capture_output=True)
            assert not any(m.get('asr') for m in client.get(f'/api/agent/v1/projects/{pid}/context').json()['media'])
        stop_owned()
        resume_file=out/'resume.json'
        subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'workbench.py'),'--out',str(resume_file),'run',
            '继续这个纯画面旅行Vlog时间轴','--intent','edit','--project',pid,'--session','native-timeline-http'],
            check=True,stdout=subprocess.DEVNULL,cwd=ROOT)
        resumed=json.loads(resume_file.read_text('utf-8'));assert resumed['project_id']==pid and not resumed['project_created']
        assert resumed['context']['project']['timeline_head']==case['plan_id']
        info=json.loads(location.read_text('utf-8'))
        result={'platform':sys.platform,'http_export':'done','same_project_after_restart':True,'timeline_head_preserved':True,
            'frames':case['plan']['map']['frames'],'duration':case['plan']['map']['duration'],
            'beat_alignment':case['plan']['map']['beat_alignment'],'source_types':'generated illustrated travel animation; mixed dimensions/fps and silent/audio clips',
            'scope':'real rendering, decode and HTTP resume; not real travel or independent listening acceptance'}
        (out/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8');print(json.dumps(result,ensure_ascii=False))
    finally:
        try:stop_owned()
        except OSError:pass


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True)
    main(parser.parse_args().out)
