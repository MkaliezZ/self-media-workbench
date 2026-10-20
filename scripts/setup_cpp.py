"""Agent setup helper: explicit upstream build/model provisioning, never normal ASR."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from settings import STATE,CONFIG_FILE,CONFIG

UPSTREAM='https://github.com/ggml-org/whisper.cpp.git'
REVISION='d1be6fde11ac6e0407606b4e42fe72d34add8037'  # v1.9.5, includes CJK JSON fix


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--acceleration',choices=['vulkan','metal'],default='metal' if sys.platform=='darwin' else 'vulkan')
    p.add_argument('--workspace',type=Path,default=STATE/'runtime/whisper-cpp')
    p.add_argument('--vulkan-sdk',type=Path)
    p.add_argument('--download-model',choices=['tiny','base','small','medium'])
    p.add_argument('--model',type=Path)
    p.add_argument('--configure',action='store_true')
    args=p.parse_args();requested=args.workspace.expanduser().resolve()
    folder=requested/(REVISION[:12]+'-'+args.acceleration)
    # MSBuild's Vulkan shader-generator subproject still hits MAX_PATH even on
    # a long-path-enabled host. Use a short, uniquely owned drive-local cache.
    if os.name=='nt' and len(str(folder))>48:
        key=hashlib.sha256(str(requested).casefold().encode()).hexdigest()[:8]
        folder=Path(requested.anchor)/'.smw-build'/key/(REVISION[:8]+'-'+args.acceleration)
    folder.mkdir(parents=True,exist_ok=True);env=dict(os.environ);commands=[]
    def run(command):
        commands.append([str(c) for c in command]);(folder/'commands.json').write_text(json.dumps(commands,indent=2),encoding='utf8')
        with (folder/'build.log').open('ab') as stream:
            subprocess.run([str(c) for c in command],stdout=stream,stderr=subprocess.STDOUT,env=env,check=True,timeout=1800)
    try:
        marker=folder/'workbench-build-owner.json'
        owner={'requested_workspace':str(requested),'source_revision':REVISION,'acceleration':args.acceleration}
        if marker.exists() and json.loads(marker.read_text('utf8'))!=owner:raise RuntimeError('Build directory belongs to another configuration; will not overwrite')
        marker.write_text(json.dumps(owner,indent=2),encoding='utf8')
        if not shutil.which('git') or not shutil.which('cmake'):raise RuntimeError('Setup requires Git, CMake and a C++ toolchain (MSVC on Windows, Xcode command line tools on macOS)')
        if args.acceleration=='vulkan':
            sdk=args.vulkan_sdk or (Path(env['VULKAN_SDK']) if env.get('VULKAN_SDK') else None)
            if sdk:
                sdk=sdk.expanduser().resolve();env['VULKAN_SDK']=str(sdk);env['PATH']=str(sdk/'Bin')+os.pathsep+env.get('PATH','')
        source=folder/'source';build=folder/'build'
        if not source.exists():run(['git','clone','--depth','1','--branch','v1.9.5',UPSTREAM,source])
        actual=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
        if actual!=REVISION:raise RuntimeError('Existing checkout/tag does not match pinned upstream; will not reset it')
        options=['-DWHISPER_BUILD_TESTS=OFF','-DWHISPER_BUILD_SERVER=OFF','-DBUILD_SHARED_LIBS=OFF',
                 '-DGGML_BACKEND_DL=OFF','-DGGML_NATIVE=OFF',
                 '-DGGML_VULKAN='+('ON' if args.acceleration=='vulkan' else 'OFF'),
                 '-DGGML_METAL='+('ON' if args.acceleration=='metal' else 'OFF')]
        if args.acceleration=='metal':options.append('-DGGML_METAL_EMBED_LIBRARY=ON')
        run(['cmake','-S',source,'-B',build,*options])
        run(['cmake','--build',build,'--config','Release','--target','whisper-cli','-j','2'])
        name='whisper-cli.exe' if os.name=='nt' else 'whisper-cli'
        executable=next((f for f in [build/'bin/Release'/name,build/'bin'/name] if f.is_file()),None)
        if not executable:raise RuntimeError('Build completed without expected executable')
        # Keep upstream MIT notices alongside the optional native executable.
        for original,name in [(source/'LICENSE','LICENSE-whisper.cpp.txt'),(source/'ggml/LICENSE','LICENSE-ggml.txt')]:
            if original.is_file():shutil.copy2(original,executable.parent/name)
        model=args.model.expanduser().resolve() if args.model else None;download=None
        if args.download_model:
            if model:raise ValueError('Choose --model or --download-model')
            from huggingface_hub import HfApi,hf_hub_download
            repo='ggerganov/whisper.cpp';filename='ggml-'+args.download_model+'.bin'
            info=HfApi().model_info(repo,files_metadata=True)
            remote=next(s for s in info.siblings if s.rfilename==filename)
            model=Path(hf_hub_download(repo,filename,revision=info.sha,local_dir=str(folder/'models')))
            with model.open('rb') as stream:digest=hashlib.file_digest(stream,'sha256').hexdigest()
            if not remote.lfs or digest!=remote.lfs.sha256:raise RuntimeError('Downloaded model does not match upstream LFS SHA256')
            download={'repo':repo,'revision':info.sha,'file':filename,'sha256':digest,'verified':True}
            (folder/'model-download.json').write_text(json.dumps(download,indent=2),encoding='utf8')
        if args.configure:
            if not model:raise ValueError('A local GGML model is required before saving configuration')
            from cpp_asr import local_files
            local_files(executable,model)
            config={**CONFIG,'cpp_executable':str(executable),'cpp_model':str(model)}
            CONFIG_FILE.parent.mkdir(parents=True,exist_ok=True)
            CONFIG_FILE.write_text(json.dumps(config,indent=2,ensure_ascii=False),encoding='utf8')
        result={'built':True,'configured':args.configure,'executable':str(executable),'model':str(model) if model else None,
                'source_revision':actual,'acceleration':args.acceleration,'gpu_execution_verified':False,
                'download':download,'workspace':str(folder),'requested_workspace':str(requested),
                'restart_existing_service_required':args.configure,
                'notice':'After configure, restart only the verified own idle service before resuming the same project. Run actual ASR and check backend/device/execution; build success is not GPU inference proof'}
        code=0
    except Exception as exc:result={'built':False,'error':str(exc),'workspace':str(folder)};code=1
    (folder/'setup-result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False));return code


if __name__=='__main__':raise SystemExit(main())
