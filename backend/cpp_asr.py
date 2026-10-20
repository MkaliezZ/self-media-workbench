"""Own subprocess adapter for separately installed whisper.cpp Vulkan/Metal.

Raw engine JSON and diagnostics are retained. No shell, downloads, fabricated
character timestamps, or inference from compiled capability flags alone.
"""
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
import uuid
import wave
from pathlib import Path


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def local_files(executable,model):
    executable,model=Path(executable).expanduser().resolve(),Path(model).expanduser().resolve()
    if not executable.is_file():raise ValueError('Configure a local whisper.cpp executable; normal ASR never downloads it')
    if not model.is_file():raise ValueError('Configure a local GGML model file; CT2/MLX weights are incompatible')
    with model.open('rb') as stream:
        if stream.read(4)!=b'lmgg':raise ValueError('Expected whisper.cpp GGML model magic, not CT2/MLX weights')
    return executable,model


def parse_result(raw):
    words=[]
    def bounds(item):
        pair=item['offsets'];a,b=float(pair['from'])/1000,float(pair['to'])/1000
        if not math.isfinite(a+b) or a<0 or b<=a:raise ValueError('Invalid native ASR group offsets')
        return a,b
    for segment in raw['transcription']:
        text=segment['text']
        if not text.strip():continue
        lo,hi=bounds(segment)
        tokens=[t for t in segment.get('tokens',[]) if not re.fullmatch(r'<\|.*?\|>|\[_.*?_\]',t['text'])]
        # If any token has missing/zero/overlapping bounds, keep the actual
        # segment as one explicitly coarse group. Never invent per-word times.
        parsed=[];cursor=lo
        try:
            if ''.join(t['text'] for t in tokens)!=text:raise ValueError('Token text does not cover native segment')
            for token in tokens:
                if not token['text']:continue
                a,b=bounds(token)
                if a<cursor-1e-6 or a<lo-1e-6 or b>hi+1e-6:raise ValueError('Token bounds outside ordered native segment')
                p=float(token['p'])
                if not math.isfinite(p) or not 0<=p<=1:raise ValueError('Invalid native token probability')
                parsed.append({'word':token['text'],'start':a,'end':b,'probability':p,'alignment':'model_token_group'})
                cursor=b
            if not parsed:raise ValueError('No timed tokens')
        except (KeyError,TypeError,ValueError):
            parsed=[{'word':text,'start':lo,'end':hi,'probability':None,'alignment':'model_segment_group'}]
        if words and lo<words[-1]['end']-1e-6:raise ValueError('Native segment timelines overlap')
        words.extend(parsed)
    return words


def gpu_evidence(stderr,acceleration):
    family='Vulkan' if acceleration=='vulkan' else 'Metal'
    selected=re.search(r'whisper_backend_init_gpu: using ('+family+r'[^\r\n]*?) backend',stderr,re.I)
    allocated=re.search(r'whisper_model_load:\s*'+family+r'[^\r\n]*total size\s*=\s*([0-9.]+)\s*MB',stderr,re.I)
    if not selected or not allocated or float(allocated[1])<=0:
        raise RuntimeError('Requested '+acceleration+' GPU execution not established by native backend/model allocation logs')
    return {'selected_native_backend':selected[1],'gpu_model_megabytes':float(allocated[1])}


def cpp_infer(audio,executable,model,acceleration,language,evidence_dir=None,gpu_index=0):
    import numpy as np
    executable,model=local_files(executable,model)
    if acceleration not in ('vulkan','metal','cpu'):raise ValueError('Unknown whisper.cpp acceleration')
    if not isinstance(gpu_index,int) or gpu_index<0:raise ValueError('GPU index must be a nonnegative integer')
    with tempfile.TemporaryDirectory(prefix='workbench-cpp-') as temporary:
        folder=Path(evidence_dir)/('whisper-cpp-'+uuid.uuid4().hex) if evidence_dir else Path(temporary)/'evidence'
        folder.mkdir(parents=True,exist_ok=False)
        audio_path=Path(temporary)/'audio.wav';prefix=folder/'native'
        with wave.open(str(audio_path),'wb') as stream:
            stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(16000)
            stream.writeframes(np.rint(np.clip(audio,-1,32767/32768)*32768).astype('<i2').tobytes())
        command=[str(executable),'-m',str(model),'-f',str(audio_path),'-l',language or 'auto',
                 '-ojf','-of',str(prefix),'-ml','32','-sow','-nfa','-dev',str(gpu_index)]
        if acceleration=='cpu':command.append('-ng')
        def save(name,value):
            (folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
        metadata={'command':command,'binary_sha256':sha(executable),'model_sha256':sha(model),
                  'requested_acceleration':acceleration,'gpu_index':gpu_index}
        save('attempt.json',metadata)
        options={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
        # A native failure cannot bring down the project service. Logs remain
        # even on timeout/nonzero exit and are referenced by the fallback reason.
        try:
            with (folder/'stdout.txt').open('wb') as stdout,(folder/'stderr.txt').open('wb') as stderr:
                proc=subprocess.run(command,stdout=stdout,stderr=stderr,timeout=3600,
                    env={**os.environ,'HF_HUB_OFFLINE':'1','TRANSFORMERS_OFFLINE':'1'},**options)
            if proc.returncode:raise RuntimeError('Native process exited '+str(proc.returncode))
            raw=json.loads((folder/'native.json').read_text('utf-8'))
            words=parse_result(raw)
            proof={} if acceleration=='cpu' else gpu_evidence((folder/'stderr.txt').read_text('utf-8',errors='replace'),acceleration)
            execution={**proof,'acceleration':acceleration,'gpu_inference_verified':acceleration!='cpu',
                       'isolated_worker':True,'binary_sha256':metadata['binary_sha256'],
                       'model_sha256':metadata['model_sha256'],'evidence_dir':str(folder) if evidence_dir else None,
                       'coarse_segment_groups':sum(w['alignment']=='model_segment_group' for w in words)}
            save('completed.json',execution)
            return {'backend':'whisper.cpp','device':acceleration,'model':str(model),
                    'language':raw['result']['language'],'words':words,'fallback_errors':[],'execution':execution}
        except Exception as exc:
            save('failure.json',{'error':str(exc)})
            raise RuntimeError(f'whisper.cpp {acceleration} failed: {exc}; evidence={folder if evidence_dir else "temporary"}') from exc
