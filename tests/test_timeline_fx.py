"""Decode real FX output and compare pixels, clocks and preserved PNG alpha."""
import copy
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from timeline_models import TimelinePlan
from timeline_tools import timeline_map,render,digest,source_info
from timeline_fx import alpha_field
from visual_tools import sha,font_file


class TimelineFXTests(unittest.TestCase):
    def test_real_transitions_masks_and_old_plan(self):
        root=os.environ.get('TIMELINE_EVIDENCE_ROOT')
        if root:Path(root).mkdir(parents=True,exist_ok=True)
        temp=tempfile.TemporaryDirectory(prefix='fx-',dir=root);folder=Path(temp.name).resolve()
        if root:temp._finalizer.detach()
        resolved={};refs=[]
        for id,colour in [('a','red'),('b','blue'),('c','green')]:
            file=folder/(id+'.mp4')
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color=c={colour}:s=480x320:r=25:d=3','-c:v','libx264','-pix_fmt','yuv420p',str(file)],check=True,capture_output=True)
            resolved[id]={'path':file,'info':source_info(file,'media'),'item':{}}
            refs.append({'id':id,'kind':'media','asset_id':id,'sha256':sha(file)})
        # Original transparent window must survive the separately applied shape alpha.
        array=np.full((120,120,4),255,dtype='uint8');array[45:75,45:75,3]=0
        def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
        file=folder/'layer.png';file.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',120,120,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(b'\0'+row.tobytes() for row in array)))+chunk(b'IEND',b''))
        resolved['layer']={'path':file,'info':source_info(file,'image'),'item':{}}
        refs.append({'id':'layer','kind':'image','asset_id':'layer','sha256':sha(file)})
        body=TimelinePlan.model_validate({'request_id':'fx','project_revision':1,'revision_reason':'Native pixel verification',
            'intent':'Fade, spatial wipe and alpha-preserving feathered local layer','width':480,'height':320,'fps':25,'sources':refs,
            'shots':[{'id':id,'source_id':id,'source_in':0.,'source_out':3.,'role':'test','reason':'Colour identity check'} for id in ['a','b','c']],
            'transitions':[{'after_shot_id':'a','kind':'fade','duration':.4,'reason':'Blend'}, {'after_shot_id':'b','kind':'wipeleft','duration':.6,'reason':'Spatial reveal'}],
            'titles':[{'text':'LOCK','start':3.72,'end':3.88,'font_height':.07}],
            'masks':[{'source_id':'layer','start':4.,'end':7.,'slot':{'x':.25,'y':.25,'width':.25,'height':.375},'shape':'ellipse','feather':16,'reason':'Local alpha check'}]}).model_dump()
        mapping=timeline_map(body,resolved);self.assertEqual(mapping['frames'],200)
        def execute(plan,name):
            directory=folder/name;directory.mkdir()
            sources=[]
            for ref in plan['sources']:
                s=resolved[ref['id']];sources.append({'id':ref['id'],'relative_path':s['path'].name,'info':s['info'],'metadata':{},'sha256':ref['sha256']})
            selected={r['id']:resolved[r['id']] for r in plan['sources']}
            record={'request':plan,'request_sha256':digest(plan),'map':timeline_map(plan,selected),'sources':sources}
            if plan['titles']:
                original=font_file(None);local=folder/('font'+original.suffix)
                if not local.exists():shutil.copyfile(original,local)
                record['font']={'relative_path':local.name,'sha256':sha(local)}
            render(record,folder,directory);return directory/'timeline.mp4'
        movie=execute(body,'actual')
        def frame(t):
            return np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-ss',str(t),'-i',str(movie),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','-']),dtype='uint8').reshape(320,480,3)
        before=frame(2.4)[20,20].astype(float);middle=frame(2.8)[20,20].astype(float);after=frame(3.2)[20,20].astype(float)
        self.assertGreater(before[0],220);self.assertGreater(after[2],220)
        self.assertTrue(70<middle[0]<190 and 70<middle[2]<190,middle)
        def white(at):
            roi=frame(at)[255:300,180:300]
            return int(np.all(roi>210,axis=2).sum())
        self.assertLess(white(3.68),5);self.assertGreater(white(3.72),40);self.assertLess(white(3.88),5)
        wipe=frame(5.3);self.assertGreater(np.linalg.norm(wipe[20,20].astype(float)-wipe[20,-20].astype(float)),100)
        layer=frame(4.4)
        self.assertGreater(layer[110,150,:].mean(),220) # Inside opaque source and ellipse.
        self.assertGreater(layer[140,180,2],220);self.assertLess(layer[140,180,0],25) # Original transparent centre.
        self.assertLess(layer[82,122,0],25) # Outside ellipse.
        a=alpha_field(120,120,'ellipse',16,1.)
        self.assertEqual(int(a[60,60]),255);self.assertEqual(int(a[0,0]),0)
        self.assertGreater(len(np.unique(a[60,:30])),10)
        # Remove newly added optional fields to emulate a genuinely saved older request/map checksum.
        old=copy.deepcopy(body);old.pop('transitions');old.pop('masks');old['sources']=old['sources'][:3];old['titles']=[]
        old_resolved={k:v for k,v in resolved.items() if k!='layer'}
        olddir=folder/'old';olddir.mkdir();oldrecord={'request':old,'request_sha256':digest(old),'map':timeline_map(old,old_resolved),
            'sources':[{'id':r['id'],'relative_path':resolved[r['id']]['path'].name,'info':resolved[r['id']]['info'],'metadata':{},'sha256':r['sha256']} for r in old['sources']]}
        render(oldrecord,folder,olddir)
        primary=movie
        for kind in ('wiperight','slideleft','slideright','circleopen'):
            variant=copy.deepcopy(body);variant.update(sources=body['sources'][:2],shots=body['shots'][:2],masks=[],titles=[],
                transitions=[{'after_shot_id':'a','kind':kind,'duration':.4,'reason':'Verify the declared transition family on actual decoded pixels'}])
            movie=execute(variant,kind)
            self.assertGreater(frame(2.4)[20,20,0],220);self.assertGreater(frame(3.2)[20,20,2],220)
            spatial=frame(2.8).astype(float)
            self.assertGreater(float(spatial[:,:,0].std()+spatial[:,:,2].std()),50,kind)
        movie=primary
        (folder/'acceptance.json').write_text(json.dumps({'status':'passed','video':str(movie),'verification':json.loads((movie.parent/'timeline-verification.json').read_text()),'checks':['fade pixels','spatial wipe','original PNG alpha','ellipse outside','feather gradient','old request integrity/export']},indent=2),'utf-8')
        if not root:temp.cleanup()


if __name__=='__main__':unittest.main()
