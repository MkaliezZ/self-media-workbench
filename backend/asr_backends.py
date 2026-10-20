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
    errors=[];directories=[]
    if device=='auto':device='cpu' if sys.platform=='darwin' else 'cuda'
    if device not in ('cpu','cuda'):raise ValueError('faster-whisper accepts auto/cpu/cuda, not Metal GPU')
    def run(selected):
        model=WhisperModel(str(model_path),device=selected,
            compute_type='int8_float16' if selected=='cuda' else 'int8',local_files_only=True)
        segments,info=model.transcribe(audio,language=language or None,beam_size=5,
            word_timestamps=True,vad_filter=False,condition_on_previous_text=False)
        return list(segments),info
    try:
        if device=='cuda':directories=configure_cuda_dlls()
        segments,info=run(device)
    except Exception as exc:
        if device!='cuda':raise
        errors.append({'backend':'faster-whisper','device':device,'error':str(exc)})
        device='cpu';segments,info=run(device)
    words=[{'word':w.word,'start':w.start,'end':w.end,'probability':w.probability}
        for segment in segments for w in segment.words or []]
    return {'backend':'faster-whisper','device':device,'model':str(model_path),'language':info.language,
        'words':words,'fallback_errors':errors,'cuda_dll_dirs':directories,'execution':{}}


def infer(audio, model_path, mlx_model, backend, device, language):
    if backend not in ('auto','faster-whisper','mlx'):raise ValueError('Unknown ASR backend')
    if device not in ('auto','cpu','cuda','gpu'):raise ValueError('Unknown ASR device')
    if backend=='mlx' and device in ('cpu','cuda'):
        raise ValueError('MLX GPU backend accepts auto/gpu; use faster-whisper with cpu/cuda')
    if backend=='faster-whisper' and device=='gpu':raise ValueError('Use mlx/auto for Apple GPU, or cuda for NVIDIA')
    wants_mlx=backend=='mlx' or (backend=='auto' and (device=='gpu' or (apple_silicon() and device=='auto')))
    if wants_mlx:
        try:return mlx_infer(audio,mlx_model,language)
        except Exception as exc:
            try:result=faster_infer(audio,model_path,'cpu',language)
            except Exception as cpu_error:
                raise RuntimeError(f'MLX failed: {exc}; CPU fallback failed: {cpu_error}') from cpu_error
            result['fallback_errors'].insert(0,{'backend':'mlx','device':'gpu','error':str(exc)})
            return result
    return faster_infer(audio,model_path,device,language)
