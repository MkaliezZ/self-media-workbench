"""Independent sealed deep-sea track matte task via documented native API only."""
from pathlib import Path
import sys,copy,json,subprocess
ROOT=Path(__file__).resolve().parent;REPO=ROOT.parent/'product-clone';sys.path.insert(0,str(REPO/'scripts'))
from independent_fx_acceptance import FxRun,write,read,sha
def rect(x,y,w,h):return {'x':x/1280,'y':y/720,'width':w/1280,'height':h/720}
def main():
    out=ROOT/'attempts'/'001-5dcad35';out.mkdir(exist_ok=True);r=FxRun(out)
    args=['run','Independent original deep-sea video through alpha/luma/inverted mattes, moving feather circle and transparent foreground hole/occlusion. No real footage or automatic matting.','--intent','edit','--new','--title','Independent deep-sea track matte task','--simulation','--media-nature','generated','--source-note','Original generated deep-sea illustration/video/PNG masks/audio; not real observations or footage','--usage-scope','Local independent technical acceptance, no publication','--session','track-matte-blind-001']
    for p in sorted((ROOT/'materials').glob('*')):
        if p.suffix in ['.png','.mp4','.wav']:args.extend(['--input',str(p)])
    i=r.cli('intake',args);r.base=i['service_url'];r.pid=i['project_id'];ctx=r.context('initial-context');r.cli('capabilities',['call','GET','/api/agent/v1/capabilities'])
    names={'deep_background.png':'bg','independent_alpha_bands.png':'alpha','independent_luma_bands.png':'luma','independent_feather_circle.png':'circle','independent_foreground_hole.png':'fore'}
    src=[{'id':names[a['label']],'kind':'image','asset_id':a['id'],'sha256':a['sha256']} for a in ctx['project']['image_assets']]
    src += [{'id':'video' if a['has_video'] else 'music','kind':'media','asset_id':a['id'],'sha256':a['sha256']} for a in ctx['project']['media']]
    common={'kind':'track_matte','source_id':'video','crop':{'x':180/960,'y':0,'width':600/960,'height':1},'from_rect':rect(384,104,512,512),'to_rect':rect(384,104,512,512),'enter_seconds':.1,'exit_seconds':0,'animation':'move','easing':'smoothstep','shape':'rectangle','feather':0,'opacity':1,'shadow':False}
    effects=[]
    for start,matte,mode,invert in [(0,'alpha','alpha',False),(4,'alpha','alpha',True),(8,'luma','luma',False),(12,'luma','luma',True)]:
        cue=copy.deepcopy(common);cue.update(start=start,end=start+4,source_in=start,matte_id=matte,matte_mode=mode,invert=invert,reason='Independent orthogonal RGB/alpha calibration and actual continuous source video');effects.append(cue)
    moving=copy.deepcopy(common);moving.update(start=16,end=20,source_in=16,from_rect=rect(100,280,320,320),to_rect=rect(800,120,320,320),enter_seconds=3.5,matte_id='circle',matte_mode='alpha',invert=False,reason='Actual feather alpha window following authored smoothstep endpoints; source keeps advancing');effects.append(moving)
    effects.append({'kind':'motion_layer','source_id':'fore','source_in':0,'start':17,'end':19,'from_rect':rect(460,160,360,360),'to_rect':rect(460,160,360,360),'enter_seconds':.1,'exit_seconds':0,'animation':'move','easing':'smoothstep','opacity':1,'feather':0,'shape':'rectangle','shadow':False,'reason':'Opaque frame/cross with actual transparent PNG hole and hidden magenta RGB, foreground order control'})
    body={'request_id':'sealed-track-first','project_revision':ctx['project']['revision'],'supersedes':None,'revision_reason':'First sealed deep-sea alpha/luma/invert and foreground order plan','intent':'Actual same original source video through prepared masks, not automatic matting','width':1280,'height':720,'fps':30,'sources':src,'shots':[{'id':'deep-base','source_id':'bg','source_in':0,'source_out':20,'fit':'contain','source_audio_gain':0,'role':'calibration','reason':'Independent flat measurement background with synthetic disclosure'}],'audio':[{'source_id':'music','role':'music','source_in':0,'start':0,'duration':20,'gain':.5,'reason':'Original nonperiodic clock across all matte phases'}],'effects':effects,'titles':[{'text':txt,'start':a,'end':b,'font_height':.04,'bottom_margin':.08} for txt,a,b in [('ALPHA / ORIGINAL',0,4),('ALPHA / INVERT',4,8),('LUMA / ORIGINAL',8,12),('LUMA / INVERT',12,16),('FEATHER / PNG HOLE / OCCLUSION',16,20)]],'font_path':'C:/Windows/Fonts/msyh.ttc'}
    write(out/'first-authored-request.json',body);first=r.save('full',body);video=r.export_fx('full-export',first)
    control=copy.deepcopy(body);control['effects'][-2:]=[control['effects'][-1],control['effects'][-2]];control['revision_reason']='Only reverse foreground/window order; preserve source clocks and other pixels';ctrl=r.save('order-control',control);cv=r.export_fx('order-control-export',ctrl)
    body['revision_reason']='Restore original foreground order after actual inspection as new immutable version';restored=r.save('restored',body);rv=r.export_fx('restored-export',restored)
    write(out/'exports-index.json',{'full':str(video),'control':str(cv),'restored':str(rv),'first_sha256':sha(video),'restored_sha256':sha(rv),'project_id':r.pid,'service_url':r.base,'first_plan_id':first['id'],'control_plan_id':ctrl['id'],'restored_plan_id':restored['id'],'product_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()});print('RENDERED ALL THREE')
if __name__=='__main__':
    try:main()
    except Exception:
        import traceback
        write(ROOT/'attempts'/'001-5dcad35'/'driver-failure.json',{'traceback':traceback.format_exc()});raise
