"""Reproducible illustrated coastal-travel case and actual HTTP/TestClient exercise.

All scene art and music are generated locally. This is not recorded travel footage.
"""
import argparse
import json
import math
import os
import struct
import subprocess
import sys
import time
import wave
import zlib
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))


def png(path,array):
    h,w,_=array.shape
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\0'+row.tobytes() for row in array.astype('uint8'))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))


def make_materials(folder):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
    files=[]
    specs=[(640,360,24),(360,640,30),(480,480,25),(800,450,30)]
    for i,(w,h,fps) in enumerate(specs):
        yy,xx=np.mgrid[:h,:w];image=np.empty((h,w,3),dtype='uint8')
        image[:]=(154,206,219);image[yy>h*.42]=(66,143,157);image[yy>h*.72]=(211,190,140)
        image[(xx-w*.82)**2+(yy-h*.18)**2<(h*.07)**2]=(255,223,151)
        if i==0:  # Station platform, train, doors and posts.
            image[(yy>h*.57)&(yy<h*.86)]=(96,105,99)
            image[(xx>w*.08)&(xx<w*.92)&(yy>h*.31)&(yy<h*.62)]=(235,223,191)
            for k in range(7):
                image[(xx>w*(.12+k*.11))&(xx<w*(.19+k*.11))&(yy>h*.36)&(yy<h*.49)]=(48,80,91)
            image[(yy>h*.53)&(yy<h*.56)&(xx>w*.08)&(xx<w*.92)]=(186,97,62)
            image[abs(yy-h*.79)<2]=(232,204,125)
        elif i==1:  # Hillside village with a narrow street and roof geometry.
            image[yy>h*.48]=(96,142,111)
            image[(abs(xx-w*.5)<(yy/h)*w*.22)&(yy>h*.5)]=(215,197,160)
            for x,y in [(.16,.44),(.56,.38),(.12,.65),(.64,.62)]:
                left,right=int(w*x),int(w*(x+.22));top,bottom=int(h*y),int(h*(y+.18))
                image[top:bottom,left:right]=(235,213,175)
                image[(xx>=left-5)&(xx<right+5)&(yy>=top-h*.05)&(yy<top)]=(166,92,68)
                image[top+int(h*.05):top+int(h*.11),left+int(w*.07):left+int(w*.14)]=(65,90,90)
        elif i==2:  # Beach path and a person: a meaningful silent scene.
            image[(yy>h*.65)&(abs(xx-w*.58)<(yy/h)*w*.19)]=(232,208,153)
            image[(yy>h*.76)&(yy<h*.87)&(xx>w*.44)&(xx<w*.48)]=(67,81,94)
            image[(xx-w*.46)**2+(yy-h*.73)**2<(h*.025)**2]=(89,71,59)
            image[(yy>h*.49)&(yy<h*.65)&(abs(xx-w*.25)<(h*.65-yy)*.23)]=(73,114,92)
        else:  # Lookout, railing and setting sun over the sea.
            image[:]=(230,186,149);image[yy>h*.43]=(78,133,143)
            image[(xx-w*.63)**2+(yy-h*.30)**2<(h*.085)**2]=(255,223,154)
            image[yy>h*.83]=(99,100,87)
            image[(yy>h*.67)&(yy<h*.69)]=(58,74,76)
            for x in [.08,.28,.48,.68,.88]:image[(abs(xx-w*x)<3)&(yy>h*.68)]=(58,74,76)
        picture=folder/f'scene-{i}.png';png(picture,image)
        video=folder/f'scene-{i}.mp4'
        if not video.exists():
            command=['ffmpeg','-v','error','-nostdin','-n','-loop','1','-i',str(picture)]
            if i in (0,2):command+=['-f','lavfi','-i',f'sine=frequency={180+i*70}:sample_rate=48000:duration=6']
            command+=['-vf',f"zoompan=z='1.02+0.01*sin(on/40)':x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s={w}x{h}:fps={fps}",
                '-t','6','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p']
            if i in (0,2):command+=['-c:a','aac']
            else:command+=['-an']
            subprocess.run(command+[str(video)],check=True,capture_output=True)
        files.append(video)
    audio=folder/'original-music.wav';rate=48000;t=np.arange(rate*14)/rate
    signal=.045*np.sin(2*np.pi*220*t)+.035*np.sin(2*np.pi*330*t)
    for edge in np.arange(0,14,.5):
        dt=t-edge;active=(dt>=0)&(dt<.06)
        signal[active]+=.6*np.sin(2*np.pi*1000*dt[active])*np.exp(-dt[active]*65)
    with wave.open(str(audio),'wb') as stream:
        stream.setparams((1,2,rate,0,'NONE','not compressed'));stream.writeframes((signal*32767).astype('<i2').tobytes())
    (folder/'material-declaration.json').write_text(json.dumps({'nature':'generated','description':'Original procedural illustrated coastal trip and composed tones/clicks; not recorded travel',
        'shots':['station','village','coastal walk','lookout'],'music_onsets_seconds':[float(x) for x in np.arange(0,14,.5)]},indent=2),'utf-8')
    return files,audio


def exercise(client,folder):
    videos,music=make_materials(folder/'materials')
    project=client.post('/api/projects',json={'title':'海边慢旅行·插画技术案例','simulation':True}).json();pid=project['id'];base=f'/api/projects/{pid}'
    imported=[]
    for file in [*videos,music]:
        response=client.post(base+'/media',json={'path':str(file),'media_nature':'generated',
            'source_note':'Self-created illustrated scenery/animated camera and composed music; not travel footage',
            'usage_scope':'reproducible technical demonstration'})
        response.raise_for_status();imported.append(response.json()['media'])
    context=client.get(f'/api/agent/v1/projects/{pid}/context').json()
    refs=[{'id':f's{i}','asset_id':item['id'],'kind':'media','sha256':item['sha256']} for i,item in enumerate(imported)]
    plan={'request_id':'coastal-v1','project_revision':context['project']['revision'],'revision_reason':'Initial illustrated travel structure, no ASR',
        'intent':'Establish the journey, enter the village, hold the quiet walk and close at the lookout',
        'logic_id':'life_story','width':640,'height':360,'fps':25,'sources':refs,
        'shots':[{'id':f'shot{i}','source_id':f's{i}','source_in':0.,'source_out':6.,'source_audio_gain':.15,
            'role':role,'reason':reason} for i,(role,reason) in enumerate([
                ('establish','Show the station and establish a departure'),('arrival','A vertical village view establishes the new location'),
                ('experience','Keep a longer silent visual walk; no VAD deletion'),('reflection','Give the lookout time to close the journey')])],
        'audio':[{'source_id':'s4','role':'music','source_in':0.,'start':0.,'duration':12.,'gain':.55,'fade_out':.4,'reason':'Composed pulse under quiet source ambience'}],
        'music_grid':{'source_id':'s4','source_times':[0.,3.,5.,9.,12.],'method':'manual','reason':'Known authored onsets reviewed; do not cut on every beat'},
        'titles':[{'text':'海边慢旅行 · 原创插画演练','start':0.,'end':2.5},{'text':'留一点时间，只看风景','start':5.,'end':8.5}]}
    analysis=client.post(base+'/music-onsets',json={'media_id':imported[4]['id'],'source_sha256':imported[4]['sha256'],'source_in':0.,'source_out':14.})
    analysis.raise_for_status();(folder/'music-analysis.json').write_text(json.dumps(analysis.json(),ensure_ascii=False,indent=2),'utf-8')
    reviewed=[min(analysis.json()['candidates'],key=lambda c:abs(c['source_time']-target))['source_time'] for target in (3.,5.,9.)]
    if any(abs(t-target)>.04 for t,target in zip(reviewed,(3.,5.,9.))):raise RuntimeError('Authored fixture onsets could not be verified; do not force a music grid')
    plan['music_grid'].update(source_times=[0.,*reviewed,12.],method='reviewed_onsets',
        reason='Reviewed spectral onsets near the selected story edges; opening/ending use authored music bounds, not every onset is a cut')
    aligned=client.post(base+'/timeline/align',json=plan);aligned.raise_for_status()
    (folder/'alignment.json').write_text(json.dumps(aligned.json(),ensure_ascii=False,indent=2),'utf-8')
    plan=aligned.json()['plan'];saved=client.post(base+'/timeline-plans',json=plan);saved.raise_for_status()
    record=saved.json();queued=client.post(base+'/timeline/export',json={'plan_id':record['id']});queued.raise_for_status()
    job=queued.json();deadline=time.monotonic()+180
    while job['status'] not in ('done','failed') and time.monotonic()<deadline:
        time.sleep(.1);response=client.get(base+'/jobs/'+job['id']);response.raise_for_status();job=response.json()
    result={'project_id':pid,'plan_id':record['id'],'job':job,'plan':record,'scope':'generated illustrated travel case; not actual travel or human listening acceptance'}
    (folder/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    if job['status']!='done':raise RuntimeError(str(job))
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    out=args.out.resolve();out.mkdir(parents=True,exist_ok=True)
    os.environ['SELF_MEDIA_STATE_DIR']=str(out/'state')
    from fastapi.testclient import TestClient
    import app
    with TestClient(app.app,base_url='http://localhost') as client:
        result=exercise(client,out)
        print(json.dumps({'project_id':result['project_id'],'job_status':result['job']['status'],'output':str(app.DATA/result['project_id']/'exports'/result['job']['result']['export_id']/'timeline.mp4')},ensure_ascii=False))
