"""Native pixels and source-bound talking profile acceptance, no model mock."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
import app as w
from timeline_models import TimelinePlan
from timeline_tools import timeline_map,source_info,render,digest
from visual_tools import sha
from talking_profiles import catalog,TalkingCompile,compile_plan
from keyframe_tools import state,prepare,render as layer_render


def quad(x,y,width,height):return [{'x':float(a),'y':float(b)} for a,b in [(x,y),(x+width,y),(x+width,y+height),(x,y+height)]]


class AdvancedTalkingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name).resolve()
        Image.new('RGB',(320,180),'#203040').save(self.root/'base.png')
        im=Image.new('RGBA',(160,160));d=ImageDraw.Draw(im);d.rectangle((8,8,152,152),fill='#ef3010');d.rectangle((64,64,96,96),fill=(0,0,0,0));im.save(self.root/'subject.png')
        self.refs=[{'id':n,'kind':'image','asset_id':n,'sha256':sha(self.root/(n+'.png'))} for n in ['base','subject']]
        self.resolved={r['id']:{'path':self.root/(r['id']+'.png'),'info':source_info(self.root/(r['id']+'.png'),'image'),'item':{}} for r in self.refs}
        self.cue={'kind':'keyframe_layer','source_id':'subject','start':0.,'end':3.,'reason':'Authored left, right, and return; preserve original transparent hole',
            'keys':[{'at':0.,'quad':quad(.1,.15,.25,.5)},{'at':1.,'quad':quad(.6,.15,.25,.5)},{'at':2.,'quad':quad(.6,.15,.25,.5)},{'at':3.,'quad':quad(.1,.15,.25,.5)}]}
        self.raw={'request_id':'native-keyframes','project_revision':1,'revision_reason':'Actual changed-keyframe acceptance','intent':'Native intermediate keyframes and original alpha','width':320,'height':180,'fps':20,'sources':self.refs,
            'shots':[{'id':'s','source_id':'base','source_in':0.,'source_out':3.,'role':'metaphor','reason':'Original generated graphics, no real event'}],'effects':[self.cue]}
    def tearDown(self):self.temp.cleanup()
    def normalized(self):return TimelinePlan.model_validate(self.raw).model_dump()

    def test_actual_multistage_warp_and_alpha_movie(self):
        b=self.normalized();record={'request':b,'request_sha256':digest(b),'map':timeline_map(b,self.resolved),'sources':[{'id':r['id'],'relative_path':r['id']+'.png','info':self.resolved[r['id']]['info'],'metadata':{},'sha256':r['sha256']} for r in self.refs]}
        out=self.root/'export';render(record,self.root,out)
        data=subprocess.check_output(['ffmpeg','-v','error','-i',str(out/'timeline.mp4'),'-f','rawvideo','-pix_fmt','rgb24','-'])
        v=np.frombuffer(data,dtype=np.uint8).reshape(-1,180,320,3);self.assertEqual(len(v),60)
        def red_x(frame):
            m=(frame[:,:,0]>150)&(frame[:,:,1]<100);return float(np.where(m)[1].mean())
        self.assertGreater(red_x(v[25])-red_x(v[0]),130)
        self.assertLess(red_x(v[59]),red_x(v[25])-120)
        self.assertLess(float(np.abs(v[25,72:80,229:235].astype(float)-[32,48,64]).mean()),8)
        self.assertEqual(json.loads((out/'motion-events.json').read_text('utf-8'))['events'][0]['kind'],'keyframe_layer')

    def test_invalid_keys_and_unknown_sources_are_rejected(self):
        for mutate in [lambda c:c['keys'][1].update(at=0.),lambda c:c['keys'][-1].update(at=2.),lambda c:c['keys'][1].update(quad=list(reversed(c['keys'][1]['quad']))),lambda c:c.update(source_id='not-registered'),lambda c:c.update(edge_blur=3.)]:
            raw=copy.deepcopy(self.raw);mutate(raw['effects'][0])
            with self.assertRaises(ValueError):timeline_map(TimelinePlan.model_validate(raw).model_dump(),self.resolved)

    def test_finish_is_deterministic_and_preserves_alpha(self):
        b=self.normalized();cue=b['effects'][0];cue.update(vignette=.5,chroma_pixels=2,grain=.025,halftone=.15,edge_blur=5.,focus_rect={'x':.4,'y':.35,'width':.2,'height':.3})
        image=Image.open(self.root/'subject.png').convert('RGBA');cache=prepare(cue,(320,180))
        a=layer_render(image,cue,1.5,(320,180),30,cache);again=layer_render(image,cue,1.5,(320,180),30,cache)
        plain=copy.deepcopy(cue);plain.update(vignette=0.,chroma_pixels=0,grain=0.,halftone=0.,edge_blur=0.)
        c=layer_render(image,plain,1.5,(320,180),30,{})
        self.assertEqual(a.tobytes(),again.tobytes());self.assertEqual(a.getchannel('A').tobytes(),c.getchannel('A').tobytes());self.assertNotEqual(a.tobytes(),c.tobytes())

    def test_inverse_highlight_uses_original_glyph_pixels(self):
        image=Image.new('RGBA',(200,100),'white');d=ImageDraw.Draw(image);d.rectangle((80,35,100,65),fill='black')
        raw=copy.deepcopy(self.raw);cue=raw['effects'][0];cue.update(source_id='subject',keys=[{'at':0.,'quad':quad(0,0,1,1)},{'at':3.,'quad':quad(0,0,1,1)}],highlights=[{'x':.3,'y':.2,'width':.4,'height':.6}],highlight_mode='invert',highlight_delay=.2,highlight_seconds=.6)
        b=TimelinePlan.model_validate(raw).model_dump()['effects'][0]
        before=layer_render(image,b,0.,(200,100),0,{});after=layer_render(image,b,1.5,(200,100),30,{})
        self.assertEqual(before.getpixel((70,50)),(255,255,255,255));self.assertEqual(after.getpixel((70,50)),(0,0,0,255));self.assertEqual(after.getpixel((90,50)),(255,255,255,255));self.assertEqual(after.getpixel((10,50)),(255,255,255,255))

    def test_zero_pcm_stream_is_not_a_voice_path(self):
        from talking_audio import check
        zero=self.root/'zero.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=black:s=320x180:r=20:d=3','-f','lavfi','-i','anullsrc=r=48000:cl=stereo','-t','3','-c:v','libx264','-c:a','aac',str(zero)],check=True,capture_output=True)
        source={'silent':{'path':zero,'info':source_info(zero,'media')}}
        self.assertTrue(source['silent']['info']['has_audio'])
        body={'production_profile':{'declared':True},'fps':20,'audio':[]}
        shots=[dict(source_id='silent',source_in=0.,source_out=3.,source_audio_gain=1.,output_start=0.,output_end=3.,frames=60)]
        with self.assertRaisesRegex(ValueError,'no usable voice signal'):check(body,shots,source)

    def test_profile_catalog_clock_freeze_and_ordinary_separation(self):
        p=next(p for p in catalog() if p['id']=='advanced_talking_head')
        request={k:v for k,v in self.raw.items() if k not in ('shots','effects')}
        request.update(profile_id=p['id'],profile_version=p['version'],profile_sha256=p['definition_sha256'],scenes=[{'shot':self.raw['shots'][0],'mode':'metaphor','spoken_text':'Generated demonstration of a moving square.','purpose':self.raw['shots'][0]['reason'],'material_note':'Two original generated graphics','claim_kind':'illustration','effects':[self.cue]}])
        b,binding=compile_plan(TalkingCompile.model_validate(request).model_dump());self.assertEqual(b['production_profile'],binding)
        b['shots'][0]['source_out']=2.
        with self.assertRaisesRegex(ValueError,'clock'):TimelinePlan.model_validate(b)
        p=catalog()[0];request.update(profile_id=p['id'],profile_version=p['version'],profile_sha256=p['definition_sha256'])
        with self.assertRaisesRegex(ValueError,'Ordinary'):compile_plan(TalkingCompile.model_validate(request).model_dump())

    def test_http_silent_talking_is_rejected_without_head_change(self):
        with patch.object(w,'DATA',self.root/'projects'):
            w.DATA.mkdir()
            with TestClient(w.app,base_url='http://localhost') as client:
                p=client.post('/api/agent/v1/tasks',json={'task':'高级口播剪辑','intent':'edit','new_project':True,'simulation':True,'input_paths':[str(self.root/'base.png'),str(self.root/'subject.png')]}).json()
                self.assertEqual(p['talking_profiles']['selected'],'advanced_talking_head');pid=p['project_id'];refs=[]
                for name,item in zip(['base','subject'],p['registered']):refs.append({'id':name,'kind':'image','asset_id':item['id'],'sha256':item['sha256']})
                profile=client.get('/api/visual/talking-profiles').json()['profiles'][1]
                request={k:v for k,v in self.raw.items() if k not in ('shots','effects')};request.update(project_revision=p['context']['project']['revision'],sources=refs,profile_id=profile['id'],profile_version=profile['version'],profile_sha256=profile['definition_sha256'],scenes=[{'shot':self.raw['shots'][0],'mode':'metaphor','spoken_text':'A spoken example needs real voice.','purpose':self.raw['shots'][0]['reason'],'material_note':'Generated graphics without speech','claim_kind':'illustration','effects':[self.cue]}])
                response=client.post(f'/api/projects/{pid}/talking-profile/compile',json=request);self.assertEqual(response.status_code,422,response.text)
                self.assertIn('voice',response.text);now=client.get(f'/api/agent/v1/projects/{pid}/context').json()['project'];self.assertEqual(now['revision'],p['context']['project']['revision']);self.assertIsNone(now.get('timeline_head'))
                self.assertTrue(list((w.DATA/pid/'talking-attempts').glob('*.json')))


if __name__=='__main__':unittest.main()
