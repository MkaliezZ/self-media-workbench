"""Actual decoded motion/quote pixels, video clocks, validation and old requests."""
import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from timeline_models import TimelinePlan
from timeline_tools import timeline_map,render,digest,source_info
from visual_tools import font_file,sha,probe

def rect(x,y,w,h):return {'x':float(x),'y':float(y),'width':float(w),'height':float(h)}

class MotionEffectsTests(unittest.TestCase):
    def setUp(self):
        root=os.environ.get('TIMELINE_EVIDENCE_ROOT')
        if root:Path(root).mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(prefix='motion-',dir=root);self.folder=Path(self.temp.name).resolve()
        if root:self.temp._finalizer.detach()
        self.resolved={};self.refs=[];font=font_file(None);self.font=self.folder/('font'+font.suffix);shutil.copyfile(font,self.font)
        im=Image.new('RGB',(1000,1200),'white');d=ImageDraw.Draw(im);f=ImageFont.truetype(str(font),32)
        for y,t in [(60,'A DOCUMENT WITH ACTUAL SOURCE PIXELS'),(250,'KEEP THE ORIGINAL EVIDENCE.'),(310,'HIGHLIGHT THEN LIFT THE QUOTE.'),(550,'Never invent OCR or acoustic timing.')]:d.text((90,y),t,font=f,fill='black')
        im.save(self.folder/'article.png');Image.new('RGB',(640,360),'#56677a').save(self.folder/'base.png')
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=s=320x180:r=24:d=4','-c:v','libx264','-pix_fmt','yuv420p',str(self.folder/'video.mp4')],check=True,capture_output=True)
        for id,kind,name in [('article','image','article.png'),('base','image','base.png'),('video','media','video.mp4')]:
            p=self.folder/name;self.resolved[id]={'path':p,'info':source_info(p,kind),'item':{}};self.refs.append({'id':id,'kind':kind,'asset_id':id,'sha256':sha(p)})
        self.body={'request_id':'motion','project_revision':1,'revision_reason':'Native motion acceptance','intent':'Verify actual source pixels and timed changes','width':640,'height':360,'fps':25,'sources':self.refs[:2],
            'shots':[{'id':'background','source_id':'base','source_in':0.,'source_out':4.,'role':'source','reason':'Static comparison background'}],
            'effects':[{'kind':'document_extract','source_id':'article','source_rect':rect(.08,.19,.84,.12),'highlights':[rect(.09,.20,.74,.035),rect(.09,.25,.77,.035)],
                'page_quad':[{'x':x,'y':y} for x,y in [(.2,.05),(.8,.1),(.75,.95),(.15,.9)]],'target_rect':rect(.1,.3,.8,.4),'quote':'KEEP THE ORIGINAL EVIDENCE. HIGHLIGHT THEN LIFT THE QUOTE.',
                'start':0.,'end':4.,'reveal_seconds':.2,'highlight_seconds':.4,'lift_seconds':.5,'return_seconds':.5,'reason':'Use real selected pixels rather than redrawn invented text'}]}
    def tearDown(self):
        if not os.environ.get('TIMELINE_EVIDENCE_ROOT'):self.temp.cleanup()
    def execute(self,raw,name):
        body=TimelinePlan.model_validate(raw).model_dump();selected={r['id']:self.resolved[r['id']] for r in body['sources']}
        record={'request':body,'request_sha256':digest(body),'map':timeline_map(body,selected),'font':{'relative_path':self.font.name,'sha256':sha(self.font)},
            'sources':[{'id':r['id'],'relative_path':selected[r['id']]['path'].name,'info':selected[r['id']]['info'],'metadata':{},'sha256':r['sha256']} for r in body['sources']]}
        out=self.folder/name;render(record,self.folder,out)
        raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(out/'timeline.mp4'),'-pix_fmt','rgb24','-f','rawvideo','-'])
        frames=np.frombuffer(raw,dtype='uint8').reshape(-1,360,640,3);self.assertEqual(len(frames),100)
        return out,frames
    def test_document_highlight_pullout_rectification_and_return(self):
        out,v=self.execute(self.body,'document')
        # The readable lifted card is front-facing and yellow, actual background dims.
        yellow=lambda f:int(((f[:,:,0]>150)&(f[:,:,1]>130)&(f[:,:,2]<145)).sum())
        self.assertGreater(yellow(v[45]),yellow(v[2])+300)
        self.assertLess(float(v[45,10,10].mean()),float(v[2,10,10].mean())*.6)
        self.assertLess(np.abs(v[2].astype(float)-v[99].astype(float)).mean(),20.)
        crop=Image.open(out/'document-crop-00.png').convert('RGB');width=512;height=round(crop.height*width/crop.width);left=64;top=round(108+(144-height)/2)
        expected=np.asarray(crop.resize((width,height),Image.Resampling.BICUBIC));actual=v[50,top:top+height,left:left+width]
        expected_dark=expected.mean(axis=2)<100;actual_dark=actual.mean(axis=2)<100
        self.assertGreater(float((expected_dark&actual_dark).sum()/max(1,(expected_dark|actual_dark).sum())),.65)
        for change in [{'highlights':[rect(.0,.0,.1,.1)]},{'lift_seconds':4.},{'page_quad':[{'x':x,'y':y} for x,y in [(0.,0.),(1.,1.),(1.,0.),(0.,1.)]]}]:
            body=copy.deepcopy(self.body);body['effects'][0].update(change)
            with self.assertRaises(ValueError):timeline_map(TimelinePlan.model_validate(body).model_dump(),{k:self.resolved[k] for k in ('base','article')})
    def test_video_pip_reveal_spotlight_and_authored_text(self):
        b=copy.deepcopy(self.body);b['sources']=[self.refs[1],self.refs[2]]
        b['effects']=[{'kind':'motion_layer','source_id':'video','start':0.,'end':4.,'source_in':0.,'from_rect':rect(.05,.2,.15,.15),'to_rect':rect(.3,.2,.55,.55),'enter_seconds':.6,'exit_seconds':.5,'animation':'reveal_left','reason':'Actual moving source, authored zoom and reveal'},
            {'kind':'motion_text','text':'ACTUAL MOTION','accent':'MOTION','start':1.,'end':3.5,'slot':rect(.05,.72,.9,.2),'font_height':.06,'reason':'Author-timed text, no claimed word alignment'},
            {'kind':'spotlight','start':.5,'end':3.5,'from_rect':rect(.3,.2,.25,.3),'to_rect':rect(.6,.2,.25,.3),'reason':'Authored moving attention region'}]
        out,v=self.execute(b,'mixed');self.assertGreater(np.abs(v[45].astype(float)-v[60].astype(float)).mean(),5.)
        self.assertGreater(float(v[98,10,10].mean()),float(v[50,10,10].mean())*1.8)
        self.assertTrue((out/'motion-source-00.stderr').exists())

    def test_pop_executes_scale_and_text_rejects_vertical_clipping(self):
        b=copy.deepcopy(self.body);b['sources']=[self.refs[1],self.refs[0]]
        b['effects']=[{'kind':'motion_layer','source_id':'article','start':0.,'end':4.,'from_rect':rect(.25,.2,.5,.6),
            'to_rect':rect(.25,.2,.5,.6),'enter_seconds':1.,'exit_seconds':.5,'animation':'pop','shadow':False,'reason':'Pop must change the actual bounds even when endpoint slots match'}]
        _,v=self.execute(b,'pop')
        self.assertGreater(np.abs(v[10,180,180].astype(float)-v[40,180,180].astype(float)).mean(),30.)
        b['sources']=[self.refs[1]];b['effects']=[{'kind':'motion_text','start':0.,'end':4.,'text':'TOO\nMANY\nLINES',
            'slot':rect(.1,.4,.8,.08),'font_height':.08,'reason':'Refuse cropped text, rather than silently cutting lower lines'}]
        with self.assertRaisesRegex(ValueError,'vertically'):self.execute(b,'invalid-text')
        b['effects'][0].update(text='KEEP\nEVIDENCE',accent='KEEP\nEVIDENCE',slot=rect(.1,.3,.8,.4),font_height=.07)
        _,v=self.execute(b,'multiline-accent');region=v[40,108:252,64:576]
        yellow=(region[:,:,0]>140)&(region[:,:,1]>115)&(region[:,:,2]<160)
        self.assertGreater(int(yellow[:72].sum()),30);self.assertGreater(int(yellow[72:].sum()),30)

if __name__=='__main__':unittest.main()
