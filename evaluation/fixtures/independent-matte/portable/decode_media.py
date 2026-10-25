"""Self-contained, independent decoded media helpers (no repository imports)."""
from pathlib import Path
import json,subprocess
import numpy as np

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-show_format','-of','json',str(path)]))

def frames(path,indices):
    process=subprocess.Popen(['ffmpeg','-v','error','-i',str(path),'-an','-pix_fmt','rgb24','-f','rawvideo','pipe:1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    found={};n=0;size=1280*720*3
    while True:
        raw=process.stdout.read(size)
        if not raw:break
        if len(raw)!=size:raise RuntimeError('Partial decoded frame')
        if n in indices:found[n]=np.frombuffer(raw,dtype=np.uint8).reshape((720,1280,3)).copy()
        n+=1
    error=process.stderr.read().decode(errors='replace');status=process.wait()
    if status or error.strip():raise RuntimeError(f'Decode error: {error}')
    return found,n

def rmse(a,b):
    return float(np.sqrt(np.mean((a.astype(float)-b.astype(float))**2)))

def pcm(path):
    return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-vn','-ac','1','-ar','8000','-f','f32le','pipe:1']),dtype='<f4').astype(float)

def corr(x,y):
    x=x-x.mean();y=y-y.mean()
    return float(np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y)+1e-15))
