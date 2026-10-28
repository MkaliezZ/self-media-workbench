#!/usr/bin/env python3
"""One portable entry for the calling Agent. A task starts/resumes the local service."""
import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'backend'))
from settings import (STATE, CONFIG_FILE, CONFIG, DATA, MODEL, MLX_MODEL, ASR_BACKEND, DEVICE, SKILL,
                      CPP_EXECUTABLE,CPP_MODEL,CPP_GPU_INDEX,REQUIRE_GPU)


def request(base, method, path, payload=None):
    parsed = urlsplit(base)
    if parsed.scheme!='http' or parsed.hostname not in ('127.0.0.1','localhost') or parsed.username or parsed.password or parsed.path not in ('','/'):
        raise ValueError('Only a loopback HTTP service is supported')
    if not path.startswith('/api/') and not (method=='GET' and path=='/openapi.json'):
        raise ValueError('Expected an /api/ path or GET /openapi.json')
    raw = json.dumps(payload,ensure_ascii=False,allow_nan=False).encode() if payload is not None else None
    with urlopen(Request(base.rstrip('/')+path,data=raw,method=method,headers={'Content-Type':'application/json'}),timeout=90) as response:
        return json.load(response)


def ensure_service(explicit=None):
    if explicit:
        status=request(explicit,'GET','/api/status')
        if Path(status['root']).resolve()!=ROOT:raise ValueError('The requested port serves another checkout')
        return explicit
    location = STATE/'services'/(hashlib.sha256(str(ROOT).encode()).hexdigest()[:20]+'.json')
    if location.exists():
        info=json.loads(location.read_text('utf-8'))
        try:
            if Path(request(info['base_url'],'GET','/api/status')['root']).resolve()==ROOT:return info['base_url']
        except (OSError,ValueError,KeyError):pass
    for name in ('fastapi','uvicorn','pydantic','numpy'):
        if importlib.util.find_spec(name) is None:raise ValueError(f'Missing {name}; install requirements.txt with this Python interpreter first')
    with socket.socket() as sock:
        sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
    base=f'http://127.0.0.1:{port}'
    location.parent.mkdir(parents=True,exist_ok=True)
    log=location.with_suffix('.log')
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {'start_new_session':True}
    with log.open('ab') as stream:
        process=subprocess.Popen([sys.executable,'-B','-X','utf8',str(ROOT/'workbench.py'),'serve','--port',str(port)],
            cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stream,stderr=stream,**options)
    deadline=time.monotonic()+25
    while time.monotonic()<deadline:
        if process.poll() is not None:raise ValueError(f'Local service exited; inspect {log}')
        try:
            if Path(request(base,'GET','/api/status')['root']).resolve()==ROOT:
                location.write_text(json.dumps({'base_url':base,'pid':process.pid,'root':str(ROOT),'log':str(log)}),encoding='utf-8')
                return base
        except (OSError,ValueError,KeyError):pass
        time.sleep(.15)
    raise ValueError(f'Local service did not become ready; inspect {log}')


def doctor():
    from asr_backends import mlx_probe,mlx_local_model
    from accelerators import inventory,plan
    from cpp_asr import local_files
    hardware=inventory()
    try:local_files(CPP_EXECUTABLE,CPP_MODEL);cpp_ready=True;cpp_reason=None
    except (OSError,ValueError) as exc:cpp_ready=False;cpp_reason=str(exc)
    try:
        from asr_backends import apple_silicon
        routing=[{'backend':b,'device':d} for b,d in plan(ASR_BACKEND,DEVICE,hardware,apple_silicon(),cpp_ready,REQUIRE_GPU)]
        routing_error=None
    except ValueError as exc:routing=[];routing_error=str(exc)
    try:mlx_local_model(MLX_MODEL);mlx_present=True
    except ValueError:mlx_present=False
    try:
        from visual_tools import status as visual_status
        visual=visual_status()
    except ImportError as exc:visual={'available':False,'error':str(exc)}
    return {'platform':sys.platform,'python':sys.version,'python_executable':sys.executable,'root':str(ROOT),
        'state_dir':str(STATE),'data_dir':str(DATA),'skill_entry':str(SKILL/'SKILL.md'),
        'model':str(MODEL),'model_present':(MODEL/'model.bin').is_file(),
        'asr_backend':ASR_BACKEND,'requested_device':DEVICE,'mlx_model':str(MLX_MODEL),
        'mlx_model_present':mlx_present,'mlx':mlx_probe(),
        'gpu_hardware':hardware,'asr_attempt_plan':routing,'asr_plan_error':routing_error,'require_gpu':REQUIRE_GPU,
        'gpu_setup_guide':str(ROOT/'docs/accelerators.md'),'gpu_setup_helper':str(ROOT/'scripts/setup_cpp.py'),
        'whisper_cpp':{'executable':str(CPP_EXECUTABLE),'model':str(CPP_MODEL),'files_ready':cpp_ready,
                       'reason':cpp_reason,'gpu_index':CPP_GPU_INDEX,'gpu_execution_verified':False},
        'dependencies':{k:importlib.util.find_spec(k) is not None for k in ['fastapi','pydantic','uvicorn','numpy','PIL','faster_whisper']},
        'executables':{k:shutil.which(k) for k in ['ffmpeg','ffprobe']},
        'visual_editing':visual,'visual_setup_guide':str(ROOT/'docs/visual-editing.md'),
        'lighting':__import__('lighting_radiance').status(),'lighting_ui':'/ui/#lighting',
        'macos_asr':'Apple Silicon: MLX; Intel GPU: optional whisper.cpp Metal; recorded CPU fallback' if sys.platform=='darwin' else None,
        'network_upload':False,'model_auto_download':False}


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    commands={'run','serve','doctor','configure','install-skill','projects','context','schema','submit','call'}
    if argv and argv[0] not in commands and not argv[0].startswith('-'):argv.insert(0,'run')
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url');parser.add_argument('--out',type=Path)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor')
    serve=sub.add_parser('serve');serve.add_argument('--port',type=int,default=8765)
    config=sub.add_parser('configure')
    for key in ('data-dir','model','mlx-model','cpp-executable','cpp-model','skill-root','library','radiance-bin'):config.add_argument('--'+key,type=Path)
    config.add_argument('--device',choices=['auto','cpu','cuda','gpu','vulkan','metal']);config.add_argument('--language')
    config.add_argument('--asr-backend',choices=['auto','faster-whisper','mlx','whisper.cpp'])
    config.add_argument('--cpp-gpu-index',type=int)
    config.add_argument('--require-gpu',action=argparse.BooleanOptionalAction,default=None)
    config.add_argument('--cuda-dll-dir',action='append',type=Path)
    sub.add_parser('install-skill')
    run=sub.add_parser('run');run.add_argument('task');run.add_argument('--input',action='append',default=[])
    run.add_argument('--intent',default='auto',choices=['auto','full','diagnose','topics','script','edit','publish','review','lighting'])
    run.add_argument('--project');run.add_argument('--new',action='store_true');run.add_argument('--title')
    run.add_argument('--simulation',action='store_true');run.add_argument('--media-nature',default='unknown',choices=['unknown','recorded','generated','restored','mixed'])
    run.add_argument('--source-note',default='');run.add_argument('--usage-scope',default='')
    run.add_argument('--session',default=str(Path.cwd().resolve()))
    run.add_argument('--request-id')
    sub.add_parser('projects')
    context=sub.add_parser('context');context.add_argument('project_id')
    schema=sub.add_parser('schema');schema.add_argument('name')
    submit=sub.add_parser('submit');submit.add_argument('project_id');submit.add_argument('--json',type=Path,required=True)
    call=sub.add_parser('call');call.add_argument('method',choices=['GET','POST','PUT']);call.add_argument('path');call.add_argument('--json',type=Path)
    args=parser.parse_args(argv)
    if args.command=='serve':
        import uvicorn
        import app
        uvicorn.run(app.app,host='127.0.0.1',port=args.port)
        return 0
    if args.command=='doctor':result=doctor()
    elif args.command=='configure':
        config=dict(CONFIG)
        for key in ('data_dir','model','mlx_model','cpp_executable','cpp_model','cpp_gpu_index','require_gpu','asr_backend','skill_root','library','device','language','radiance_bin'):
            value=getattr(args,key,None)
            if value is not None:
                if key=='cpp_gpu_index' and value<0:raise ValueError('GPU index must be nonnegative')
                config[key]=str(value.expanduser().resolve()) if isinstance(value,Path) else value
        if args.cuda_dll_dir is not None:config['cuda_dll_dirs']=[str(p.expanduser().resolve()) for p in args.cuda_dll_dir]
        STATE.mkdir(parents=True,exist_ok=True);CONFIG_FILE.write_text(json.dumps(config,ensure_ascii=False,indent=2),encoding='utf-8')
        result={'configured':True,'config_file':str(CONFIG_FILE),'settings':config,'notice':'Restart an existing service to apply settings; existing projects are not moved or deleted.'}
    elif args.command=='install-skill':
        target=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'skills/media-workbench'
        shutil.copytree(ROOT/'skills/media-workbench',target,dirs_exist_ok=True)
        (target/'location.json').write_text(json.dumps({'root':str(ROOT),'python':sys.executable}),encoding='utf-8')
        result={'installed':str(target),'entry':str(target/'SKILL.md'),'root':str(ROOT)}
    else:
        base=ensure_service(args.base_url)
        if args.command=='run':
            body={'task':args.task,'intent':args.intent,'project':args.project,'new_project':args.new,
                'title':args.title,'input_paths':[str(Path(p).expanduser().resolve()) for p in args.input],
                'simulation':args.simulation,'session_key':args.session,'media_nature':args.media_nature,
                'source_note':args.source_note,'usage_scope':args.usage_scope}
            if args.request_id:body['request_id']=args.request_id
            result=request(base,'POST','/api/agent/v1/tasks',body)
        elif args.command=='projects':result=request(base,'GET','/api/projects')
        elif args.command=='context':result=request(base,'GET',f'/api/agent/v1/projects/{args.project_id}/context')
        elif args.command=='schema':result=request(base,'GET','/api/agent/v1/schemas/'+args.name)
        elif args.command=='submit':result=request(base,'POST',f'/api/agent/v1/projects/{args.project_id}/artifacts',json.loads(args.json.read_text('utf-8-sig')))
        else:result=request(base,args.method,args.path,json.loads(args.json.read_text('utf-8-sig')) if args.json else None)
        if isinstance(result,dict):result.setdefault('service_url',base)
    output=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)
    if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(output+'\n',encoding='utf-8')
    print(output)
    return 0


if __name__=='__main__':
    if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
    try:sys.exit(main())
    except HTTPError as exc:
        raw=exc.read().decode('utf-8',errors='replace')
        try:detail=json.loads(raw)
        except ValueError:detail=raw
        print(json.dumps({'ok':False,'http_status':exc.code,'detail':detail},ensure_ascii=False));sys.exit(2)
    except (OSError,ValueError,KeyError) as exc:
        print(json.dumps({'ok':False,'error':str(exc)},ensure_ascii=False));sys.exit(3)
