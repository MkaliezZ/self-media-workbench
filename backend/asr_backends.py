"""Own adapters for local ASR engines. No implicit Hub/model downloads."""
import importlib.util
import platform
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def apple_silicon():
    return sys.platform=='darwin' and platform.machine().lower() in ('arm64','aarch64')


def mlx_probe():
    result={'apple_silicon':apple_silicon(),'installed':False,'metal_available':False}
    if not result['apple_silicon']:
        return {**result,'reason':'MLX GPU adapter requires native Apple Silicon macOS Python'}
    if importlib.util.find_spec('mlx_whisper') is None:
        return {**result,'reason':'Optional mlx-whisper dependency is not installed'}
    result['installed']=True
    try:
        result['metal_available']=bool(mlx_worker('probe')['metal_available'])
        result['reason']=None if result['metal_available'] else 'Metal GPU unavailable in this environment'
    except Exception as exc:
        result['reason']=str(exc)
    return result


def mlx_local_model(path):
    path=Path(path).expanduser().resolve()
    if not path.is_dir() or not (path/'config.json').is_file():
        raise ValueError('Local MLX model needs config.json; no automatic model download')
    if not any((path/name).is_file() for name in ('model.safetensors','weights.safetensors','weights.npz')):
        raise ValueError('Local MLX model needs MLX weights; CTranslate2 model.bin is not compatible')
    return path


def mlx_infer(audio, model_path, language):
    model_path=mlx_local_model(model_path)
    if not apple_silicon():raise RuntimeError('MLX GPU requires native Apple Silicon macOS Python')
    import numpy as np
    with tempfile.TemporaryDirectory(prefix='workbench-mlx-') as directory:
        audio_file=Path(directory)/'audio.npy';np.save(audio_file,audio)
        return mlx_worker('transcribe','--audio',str(audio_file),'--model',str(model_path),
                          '--language',language or '',timeout=3600)


def mlx_worker(command,*args,timeout=30):
    # Native Metal/library faults must not crash the project service or bypass CPU fallback.
    env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'}
    options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    proc=subprocess.run([sys.executable,'-B','-X','utf8',str(Path(__file__).with_name('mlx_worker.py')),command,*args],
        env=env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout,**options)
    if proc.returncode:raise RuntimeError(f'MLX worker exited {proc.returncode}: {proc.stderr[-2000:]}')
    return json.loads(proc.stdout)


def faster_infer(audio, model_path, device, language):
    model_path=Path(model_path).expanduser().resolve()
    if not (model_path/'model.bin').is_file():
        raise ValueError('Local CTranslate2 model needs model.bin; no automatic model download')
    from faster_whisper import WhisperModel
    from gpu_runtime import configure_cuda_dlls
    directories=[]
    if device=='auto':
        from accelerators import inventory
        device='cuda' if sys.platform!='darwin' and any(a['vendor']=='nvidia' for a in inventory()['adapters']) else 'cpu'
    if device not in ('cpu','cuda'):raise ValueError('faster-whisper accepts auto/cpu/cuda, not Metal GPU')
    def run(selected):
        model=WhisperModel(str(model_path),device=selected,
            compute_type='int8_float16' if selected=='cuda' else 'int8',local_files_only=True)
        segments,info=model.transcribe(audio,language=language or None,beam_size=5,
            word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
        return list(segments),info
    if device=='cuda':directories=configure_cuda_dlls()
    segments,info=run(device)
    words=[{'word':w.word,'start':w.start,'end':w.end,'probability':w.probability}
        for segment in segments for w in segment.words or []]
    return {'backend':'faster-whisper','device':device,'model':str(model_path),'language':info.language,
        'words':words,'fallback_errors':[],'cuda_dll_dirs':directories,
        'execution':{'gpu_inference_verified':device=='cuda','compute_type':'int8_float16' if device=='cuda' else 'int8'}}


def infer(audio, model_path, mlx_model, backend, device, language,*,evidence_dir=None,
          cpp_executable=None,cpp_model=None,cpp_gpu_index=None,require_gpu=None):
    from settings import CPP_EXECUTABLE,CPP_MODEL,CPP_GPU_INDEX,REQUIRE_GPU
    from accelerators import inventory,plan
    from cpp_asr import cpp_infer,local_files
    cpp_executable=CPP_EXECUTABLE if cpp_executable is None else cpp_executable
    cpp_model=CPP_MODEL if cpp_model is None else cpp_model
    cpp_gpu_index=CPP_GPU_INDEX if cpp_gpu_index is None else cpp_gpu_index
    require_gpu=REQUIRE_GPU if require_gpu is None else require_gpu
    hardware=inventory()
    try:local_files(cpp_executable,cpp_model);ready=True
    except (OSError,ValueError):ready=False
    attempts=plan(backend,device,hardware,apple_silicon(),ready,require_gpu)
    errors=[]
    for engine,selected in attempts:
        try:
            if engine=='mlx':result=mlx_infer(audio,mlx_model,language)
            elif engine=='whisper.cpp':result=cpp_infer(audio,cpp_executable,cpp_model,selected,language,evidence_dir,cpp_gpu_index)
            else:result=faster_infer(audio,model_path,selected,language)
            if require_gpu and result.get('device')=='cpu':raise RuntimeError('GPU required; CPU result rejected')
            result.setdefault('fallback_errors',[])[:0]=errors
            result['routing']={'hardware':hardware,'attempts':[{'backend':b,'device':d} for b,d in attempts],
                               'require_gpu':require_gpu,'selection_is_execution_proof':False}
            return result
        except Exception as exc:errors.append({'backend':engine,'device':selected,'error':str(exc)})
    raise RuntimeError('All ASR attempts failed: '+json.dumps(errors,ensure_ascii=False))
