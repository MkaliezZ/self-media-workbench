"""Reject silent talking-profile intervals; signal presence is not speech proof."""
import subprocess
import numpy as np


def check(body,shots,resolved):
    if not body.get('production_profile'):return
    if sum(s['frames'] for s in shots)/body['fps']>300:raise ValueError('Talking profile v1 supports clips up to 300 seconds; edit longer programs in declared segments')
    cache={}
    def signal(id,start,duration,gain):
        key=(id,start,duration,gain)
        if key not in cache:
            result=subprocess.run(['ffmpeg','-v','error','-nostdin','-ss',str(start),'-i',str(resolved[id]['path']),'-t',str(duration),'-vn','-ac','2','-ar','8000','-f','f32le','-'],capture_output=True,timeout=120)
            if result.returncode:raise ValueError('Cannot decode talking-profile audio interval')
            pcm=np.frombuffer(result.stdout,dtype='<f4').astype(np.float64)*gain
            cache[key]=bool(pcm.size and np.isfinite(pcm).all() and float(np.max(np.abs(pcm)))>=1e-4 and float(np.sqrt(np.mean(pcm*pcm)))>=1e-5)
        return cache[key]
    for shot in shots:
        a,b=shot['output_start'],shot['output_end'];candidates=[]
        if resolved[shot['source_id']]['info']['has_audio'] and shot['source_audio_gain']>0:
            candidates.append((shot['source_id'],shot['source_in'],b-a,shot['source_audio_gain']))
        for bed in body['audio']:
            if bed['role']=='voice' and bed['gain']>0 and bed['start']<=a+1e-6 and bed['start']+bed['duration']>=b-1e-6:
                candidates.append((bed['source_id'],bed['source_in']+a-bed['start'],b-a,bed['gain']))
        if not any(signal(*v) for v in candidates):raise ValueError('Talking scene has no usable voice signal in its actual interval; an audio stream alone is not audible speech')
