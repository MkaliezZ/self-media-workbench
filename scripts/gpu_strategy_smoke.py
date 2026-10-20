"""Actual local ASR plus decoded full-source export; GPU claims require execution."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--model',type=Path,required=True)
    p.add_argument('--device',choices=['auto','cuda','vulkan','metal','cpu'],default='auto')
    p.add_argument('--backend',choices=['auto','faster-whisper','mlx','whisper.cpp'],default='auto')
    p.add_argument('--cpp-executable',type=Path);p.add_argument('--cpp-model',type=Path)
    p.add_argument('--require-gpu',action='store_true');args=p.parse_args()
    root=Path(__file__).resolve().parents[1];out=args.out.resolve()
    if out.exists():raise ValueError('Use a fresh output directory; preserve earlier attempts')
    out.mkdir(parents=True);os.environ['SELF_MEDIA_STATE_DIR']=str(out/'state')
    snapshot={'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
              'working_changes':subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).splitlines(),
              'runtime_sha256':{str(f.relative_to(root)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((root/'backend').glob('*.py'))}}
    (out/'source-snapshot.json').write_text(json.dumps(snapshot,indent=2),encoding='utf8')
    config={'model':str(args.model.resolve()),'device':args.device,'asr_backend':args.backend,
            'require_gpu':args.require_gpu,'language':'zh'}
    for key in ['cpp_executable','cpp_model']:
        if getattr(args,key):config[key]=str(getattr(args,key).resolve())
    (out/'state').mkdir();(out/'state/config.json').write_text(json.dumps(config,indent=2),encoding='utf8')
    sys.path.insert(0,str(root/'backend'))
    try:
        from local_asr import transcribe
        from media_render import render
        from review_edits import plan_keeps
        source=root/'fixtures/chinese-talk/synthetic-zh.mkv'
        review=transcribe(source,out/'asr')
        if args.require_gpu and review['device']=='cpu':raise RuntimeError('CPU is not GPU acceptance')
        export=out/'export';render(source,review,plan_keeps(review,[]),export)
        command=['ffmpeg','-v','error','-nostdin','-i',str(export/'reviewed_cut.mp4'),'-map','0:v:0','-map','0:a:0','-f','null','-']
        proc=subprocess.run(command,capture_output=True,timeout=300)
        (out/'decode.stderr.txt').write_bytes(proc.stderr)
        if proc.returncode:raise RuntimeError('Export decode failed')
        words=json.loads((export/'reviewed_cut.words.json').read_text('utf8'))
        if [w['id'] for w in words]!=[w['id'] for w in review['words']]:raise RuntimeError('Export group IDs changed')
        for original,projected in zip(review['words'],words):
            if any([original['text']!=projected['text'],original['start']!=projected['source_start'],
                    original['end']!=projected['source_end'],original['probability']!=projected['asr_probability']]):raise RuntimeError('Export changed native source groups')
        result={'passed':True,'actual_backend':review['backend'],'actual_device':review['device'],
                'execution':review['execution'],'routing':review['routing'],'fallback_errors':review['fallback_errors'],
                'groups':len(review['words']),'source_duration':review['duration'],
                'scope':'Actual Chinese synthetic ASR and full-source decoded export; no human/accuracy/general hardware claim'}
    except Exception as exc:result={'passed':False,'error':str(exc),'traceback':traceback.format_exc()}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    rows=[{'path':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(out.rglob('*')) if f.is_file()]
    (out/'manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False));return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
