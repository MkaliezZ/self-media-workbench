"""Native real-scenery edit using pinned public-domain inputs and original music.

External clips are downloaded only by this explicitly invoked acceptance entry.
Normal workbench/timeline requests never download media.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path
from urllib.request import urlopen
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCES=[('coast','6fc09aec-7fc2-47ed-b8cc-e1b10861dd3e','2fecba5664992fc6aa321c10fed6f735394a0cce4af6349bd59ef28a6f397f28'),
         ('trails','99ba7527-b163-432d-a1c4-f949b0140520','949053217a966a43536bae64f465c48d1c1bbc4ee4c63879abd054084c9a6681')]


def score(path):
    rate=48000;t=np.arange(rate*14)/rate;signal=np.zeros_like(t)
    chords=[(146.83,185.,220.),(110.,138.59,164.81),(123.47,146.83,185.),(98.,123.47,146.83)]
    for bar in range(7):
        chord=chords[bar%4]
        for k in range(8):
            start=bar*2+k*.25;dt=t-start;active=(dt>=0)&(dt<1.4);freq=chord[k%3]*2
            env=np.exp(-dt[active]*4)*(1-np.exp(-dt[active]*90))
            signal[active]+=.11*env*(np.sin(2*np.pi*freq*dt[active])+.3*np.sin(2*np.pi*freq*2*dt[active]))
    rng=np.random.default_rng(8031)
    for start in np.arange(0,14,.5):
        dt=t-start;active=(dt>=0)&(dt<.12);u=dt[active]
        signal[active]+=.22*np.sin(2*np.pi*(65*u+5*(1-np.exp(-u*40))))*np.exp(-u*35)
        if round(start*2)%2:signal[active]+=.028*rng.normal(size=len(u))*np.exp(-u*55)
    signal*=np.minimum(t/.12,1)*np.minimum((14-t)/.35,1)
    with wave.open(str(path),'wb') as stream:
        stream.setparams((1,2,rate,0,'NONE','not compressed'));stream.writeframes((np.clip(signal,-.9,.9)*32767).astype('<i2').tobytes())


def main(out):
    out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    os.environ['SELF_MEDIA_STATE_DIR']=str(out/'state');os.environ['SELF_MEDIA_DATA_DIR']=str(out/'state/projects')
    sys.path.insert(0,str(ROOT/'backend'))
    from fastapi.testclient import TestClient
    import app as w
    manifest=[]
    for name,id,expected in SOURCES:
        file=out/(name+'.mp4');url=f'https://npgallery.nps.gov/GetAsset/{id}/proxyhires'
        with urlopen(url,timeout=90) as response,file.open('xb') as stream:
            while chunk:=response.read(1024*1024):stream.write(chunk)
        actual=hashlib.sha256(file.read_bytes()).hexdigest()
        entry={'id':name,'file':str(file),'sha256':actual,'expected_sha256':expected,
            'page':f'https://npgallery.nps.gov/AssetDetail/{id}','download':url,
            'source_nature':'recorded scenic B-roll; not a personal trip','usage_declaration':'Asset page states Public domain:Full Granting Rights'}
        manifest.append(entry)
        (out/'source-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
        if actual!=expected:raise RuntimeError('Public input changed; inspect the new material rather than silently replacing pinned evidence')
    music=out/'original-score.wav';score(music)
    with TestClient(w.app,base_url='http://localhost') as client:
        project=client.post('/api/projects',json={'title':'山径到海边 · 实景剪辑演示','simulation':True}).json();pid=project['id'];base=f'/api/projects/{pid}'
        items=[]
        for file,nature,note in [(out/'coast.mp4','recorded',manifest[0]['source_nature']),
                                (out/'trails.mp4','recorded',manifest[1]['source_nature']),
                                (music,'generated','Original locally composed arpeggios/percussion for this edit')]:
            response=client.post(base+'/media',json={'path':str(file),'media_nature':nature,'source_note':note,
                'usage_scope':'Public-domain scenic footage / original composed score; editing demonstration, not a claimed personal journey'})
            response.raise_for_status();items.append(response.json()['media'])
        c=client.get(f'/api/agent/v1/projects/{pid}/context').json()
        refs=[{'id':id,'kind':'media','asset_id':item['id'],'sha256':item['sha256']} for id,item in zip(['coast','trails','music'],items)]
        response=client.post(base+'/music-onsets',json={'media_id':items[-1]['id'],'source_sha256':items[-1]['sha256'],'source_in':0.,'source_out':14.})
        response.raise_for_status();analysis=response.json()
        edges=[min(analysis['candidates'],key=lambda x:abs(x['source_time']-t))['source_time'] for t in [3.,7.,10.]]
        if any(abs(a-b)>.06 for a,b in zip(edges,[3.,7.,10.])):raise RuntimeError('Score onset candidates require review; do not force alignment')
        body={'request_id':'real-travel','project_revision':c['project']['revision'],'revision_reason':'Scenery-based travel edit with original music, without claimed personal experience',
            'intent':'Establish coast, enter a forest path, look at waves, hold sunset; no fabricated continuous personal itinerary',
            'logic_id':'life_story','width':1280,'height':720,'fps':25,'sources':refs,
            'shots':[{'id':id,'source_id':source,'source_in':a,'source_out':b,'source_audio_gain':0.,'role':role,'reason':reason}
                for id,source,a,b,role,reason in [('sea','coast',20.,23.5,'establish','Establish the coastline'),
                    ('path','trails',15.3,19.8,'action','Preserve the visible walk and space'),('water','coast',3.1,6.6,'detail','Move to water texture'),
                    ('sunset','coast',23.3,27.8,'reflection','Hold the sunset; not a meaningless silent gap')]],
            'audio':[{'source_id':'music','role':'music','source_in':0.,'start':0.,'duration':14.,'gain':.8,'fade_in':.15,'fade_out':.5,
                'reason':'Original composed music; source B-roll is explicitly muted'}],
            'music_grid':{'source_id':'music','source_times':[0.,*edges,14.],'method':'reviewed_onsets','reason':'Selected scored onsets at scene changes, authored opening/ending bounds'},
            'titles':[{'text':'山径到海边','start':0.,'end':2.7,'font_height':.06},
                {'text':'脚步慢一点，风景就多一点','start':3.2,'end':6.5,'font_height':.045},
                {'text':'实景素材剪辑演示 · 非本人旅拍','start':10.5,'end':13.6,'font_height':.032}]}
        draft=client.post(base+'/timeline/align',json=body);draft.raise_for_status()
        saved=client.post(base+'/timeline-plans',json=draft.json()['plan']);saved.raise_for_status()
        response=client.post(base+'/timeline/export',json={'plan_id':saved.json()['id']});response.raise_for_status();job=response.json()
        deadline=time.monotonic()+180
        while job['status'] not in ('done','failed') and time.monotonic()<deadline:
            time.sleep(.1);job=client.get(base+'/jobs/'+job['id']).json()
        result={'platform':sys.platform,'project_id':pid,'plan':saved.json(),'job':job,'source_manifest':manifest,'analysis':analysis,
            'scope':'real public scenic inputs, generated score, actual native rendering; not a personal trip or human listening verdict'}
        (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
        if job['status']!='done':raise RuntimeError(job)
        directory=w.DATA/pid/'exports'/job['result']['export_id'];video=directory/'timeline.mp4'
        subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True,capture_output=True)
        verification=w.read(directory/'timeline-verification.json')
        if verification['actual_frames']!=350:raise RuntimeError('Actual real-scene edit is not 350 frames')
        (out/'acceptance.json').write_text(json.dumps({'status':'decoded_real_scenic_edit_passed','platform':sys.platform,'video':str(video),
            'verification':verification,'beat_alignment':saved.json()['map']['beat_alignment'],'scope':result['scope']},ensure_ascii=False,indent=2),'utf-8')
        print(json.dumps({'status':'decoded_real_scenic_edit_passed','frames':350,'video':str(video)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);main(parser.parse_args().out)
