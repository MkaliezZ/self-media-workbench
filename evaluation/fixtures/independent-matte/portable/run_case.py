"""Run the unchanged sealed 20-second matte case on a native repository host.

The calling Agent supplies a checkout and a NEW output directory; all files,
commands, requests and failures stay there. No historical checkout, source
regeneration, Windows font or output video is needed by this capsule.
"""
from pathlib import Path
import argparse,copy,hashlib,importlib.metadata,json,os,platform,re,shutil,subprocess,sys,time,urllib.request,urllib.error,uuid

CAPSULE=Path(__file__).resolve().parents[1]

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def rect(x,y,w,h):return {'x':x/1280,'y':y/720,'width':w/1280,'height':h/720}

def repository(explicit):
    if explicit:
        repo=explicit.resolve()
        if (repo/'workbench.py').is_file() and (repo/'AGENTS.md').is_file():return repo
        raise RuntimeError('The --repo directory must contain workbench.py and AGENTS.md')
    for p in Path(__file__).resolve().parents:
        if (p/'workbench.py').is_file() and (p/'AGENTS.md').is_file():return p
    raise RuntimeError('Agent must supply --repo for a capsule outside its checkout')

def prerequisites(repo,out,no_install):
    if sys.version_info<(3,11):raise RuntimeError('Native Python 3.11+ is required')
    missing=[]
    for package,minimum in {'fastapi':(0,115),'uvicorn':(0,30),'pydantic':(2,8),'numpy':(1,26),'Pillow':(10,0)}.items():
        try:version=tuple(int(n) for n in re.findall(r'\d+',importlib.metadata.version(package))[:2])
        except importlib.metadata.PackageNotFoundError:version=(0,)
        if version<minimum:missing.append(package)
    if missing:
        if no_install:raise RuntimeError('Missing/old Python dependencies: '+', '.join(missing))
        command=[sys.executable,'-m','pip','install','-r',str(repo/'requirements.txt')]
        done=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace');write(out/'dependency-install.json',{'command':command,'returncode':done.returncode,'stdout':done.stdout,'stderr':done.stderr});done.check_returncode()
    if not all(shutil.which(x) for x in ['ffmpeg','ffprobe']):
        if no_install:raise RuntimeError('FFmpeg and ffprobe are required')
        if sys.platform=='darwin' and shutil.which('brew'):command=['brew','install','ffmpeg']
        elif sys.platform=='win32' and shutil.which('choco'):command=['choco','install','ffmpeg','-y']
        else:raise RuntimeError('Agent must provision native FFmpeg/ffprobe on this host')
        done=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace');write(out/'ffmpeg-install.json',{'command':command,'returncode':done.returncode,'stdout':done.stdout,'stderr':done.stderr});done.check_returncode()
    if not all(shutil.which(x) for x in ['ffmpeg','ffprobe']):raise RuntimeError('FFmpeg tools remain unavailable in this process')

def sealed_inputs(out):
    seal=read(CAPSULE/'sealed'/'original-seal.json');exceptions=read(CAPSULE/'BUNDLE-EXCEPTIONS.json');omitted={x['relative_path'] for x in exceptions['not_redistributed_original_preparation_files']};checked=[]
    for key,expected in seal['files'].items():
        relative=key.replace('\\','/')
        if relative in omitted:continue
        path=CAPSULE/'sealed'/Path(relative)
        if not path.is_file() or sha(path)!=expected:raise RuntimeError('Sealed file hash mismatch: '+relative)
        checked.append(relative)
    shutil.copytree(CAPSULE/'sealed'/'materials',out/'materials');shutil.copyfile(CAPSULE/'sealed'/'SEALED_TRACK_MATTE_TASK.md',out/'SEALED_TRACK_MATTE_TASK.md')
    write(out/'input-integrity.json',{'verified_original_seal_entries':checked,'original_preparation_entries_not_redistributed':sorted(omitted),'input_sha256':{p.name:sha(p) for p in (out/'materials').glob('*') if p.is_file()}})
    return {p.name:sha(p) for p in (out/'materials').glob('*') if p.is_file()}

class Run:
    def __init__(self,repo,out):
        self.repo,self.out=repo,out;self.base=None;self.pid=None;self.env={**os.environ,'SELF_MEDIA_STATE_DIR':str(out/'state'),'SELF_MEDIA_DATA_DIR':str(out/'data'),'PYTHONUTF8':'1','PYTHONDONTWRITEBYTECODE':'1'}
    def cli(self,name,args):
        dest=self.out/(name+'.json');command=[sys.executable,'-B',str(self.repo/'workbench.py'),'--out',str(dest),*args];done=subprocess.run(command,cwd=self.repo,env=self.env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180);write(self.out/(name+'-process.json'),{'command':command,'returncode':done.returncode,'stdout':done.stdout,'stderr':done.stderr});done.check_returncode();return read(dest)
    def request(self,name,method,path,body=None,expected=200):
        req=urllib.request.Request(self.base+path,data=None if body is None else json.dumps(body).encode(),headers={'Content-Type':'application/json'},method=method)
        try:
            with urllib.request.urlopen(req,timeout=120) as response:status=response.status;data=json.load(response)
        except urllib.error.HTTPError as error:
            status=error.code;raw=error.read()
            try:data=json.loads(raw)
            except Exception:data=raw.decode(errors='replace')
        write(self.out/(name+'.json'),{'request':{'method':method,'path':path,'body':body},'status':status,'response':data})
        if status!=expected:raise RuntimeError(f'{name}: expected HTTP{expected}, got{status}: {data}')
        return data
    def context(self,name):return self.request(name,'GET',f'/api/agent/v1/projects/{self.pid}/context')
    def save(self,name,body):
        ctx=self.context(name+'-context');body=copy.deepcopy(body);body.update(request_id='portable-matte-'+uuid.uuid4().hex,project_revision=ctx['project']['revision'],supersedes=ctx['project'].get('timeline_head'));write(self.out/(name+'-request.json'),body);return self.request(name+'-save','POST',f'/api/projects/{self.pid}/timeline-plans',body)
    def export(self,name,plan):
        job=self.request(name+'-submit','POST',f'/api/projects/{self.pid}/timeline/export',{'plan_id':plan['id']})
        for n in range(300):
            job=self.request(f'{name}-poll-{n:03}','GET',f'/api/projects/{self.pid}/jobs/{job["id"]}')
            if job['status'] in ['done','failed','error']:
                write(self.out/(name+'-terminal.json'),job)
                if job['status']!='done':raise RuntimeError(f'{name}: {job}')
                return self.out/'data'/self.pid/'exports'/job['result']['export_id']/'timeline.mp4'
            time.sleep(1)
        raise TimeoutError(name)

    def execute(self):
        args=['run','Execute the unchanged independently sealed deep-sea alpha/luma/inverted track-matte case, moving soft circle and transparent foreground ordering; no real observation or automatic matting claim','--intent','edit','--new','--title','Portable independent deep-sea matte acceptance','--simulation','--media-nature','generated','--source-note','Original sealed synthetic deep-sea illustration/video/PNG/audio, not real footage or observations','--usage-scope','Local independent technical acceptance, no publication','--session','portable-matte-'+uuid.uuid4().hex]
        for p in sorted((self.out/'materials').glob('*')):
            if p.suffix in ['.png','.mp4','.wav']:args.extend(['--input',str(p)])
        intake=self.cli('intake',args);self.base,self.pid=intake['service_url'],intake['project_id'];ctx=self.context('initial-context');self.cli('schema',['schema','timeline-plan']);self.cli('capabilities',['call','GET','/api/agent/v1/capabilities'])
        names={'deep_background.png':'bg','independent_alpha_bands.png':'alpha','independent_luma_bands.png':'luma','independent_feather_circle.png':'circle','independent_foreground_hole.png':'fore'}
        src=[{'id':names[a['label']],'kind':'image','asset_id':a['id'],'sha256':a['sha256']} for a in ctx['project']['image_assets']]+[{'id':'video' if a['has_video'] else 'music','kind':'media','asset_id':a['id'],'sha256':a['sha256']} for a in ctx['project']['media']]
        common={'kind':'track_matte','source_id':'video','crop':{'x':180/960,'y':0,'width':600/960,'height':1},'from_rect':rect(384,104,512,512),'to_rect':rect(384,104,512,512),'enter_seconds':.1,'exit_seconds':0,'animation':'move','easing':'smoothstep','shape':'rectangle','feather':0,'opacity':1,'shadow':False};effects=[]
        for start,matte,mode,invert in [(0,'alpha','alpha',False),(4,'alpha','alpha',True),(8,'luma','luma',False),(12,'luma','luma',True)]:
            cue=copy.deepcopy(common);cue.update(start=start,end=start+4,source_in=start,matte_id=matte,matte_mode=mode,invert=invert,reason='Independent original RGB/alpha orthogonality and continuous source clock');effects.append(cue)
        cue=copy.deepcopy(common);cue.update(start=16,end=20,source_in=16,from_rect=rect(100,280,320,320),to_rect=rect(800,120,320,320),enter_seconds=3.5,matte_id='circle',matte_mode='alpha',invert=False,reason='Original pre-authored24px alpha feather moving window');effects.append(cue)
        effects.append({'kind':'motion_layer','source_id':'fore','source_in':0,'start':17,'end':19,'from_rect':rect(460,160,360,360),'to_rect':rect(460,160,360,360),'enter_seconds':.1,'exit_seconds':0,'animation':'move','easing':'smoothstep','opacity':1,'feather':0,'shape':'rectangle','shadow':False,'reason':'Original transparent-hole PNG and opaque cross; actual ordering comparison'})
        body={'request_id':'portable-first','project_revision':ctx['project']['revision'],'supersedes':None,'revision_reason':'Original sealed20s matte task; portable API execution','intent':'Actual sealed source pixels through prepared mattes, no automatic matting','width':1280,'height':720,'fps':30,'sources':src,'shots':[{'id':'deep-base','source_id':'bg','source_in':0,'source_out':20,'fit':'contain','source_audio_gain':0,'role':'calibration','reason':'Original flat measurement background'}],'audio':[{'source_id':'music','role':'music','source_in':0,'start':0,'duration':20,'gain':.5,'reason':'Original continuous independent chirp clock'}],'effects':effects,'titles':[{'text':text,'start':a,'end':b,'font_height':.04,'bottom_margin':.08} for text,a,b in [('ALPHA / ORIGINAL',0,4),('ALPHA / INVERT',4,8),('LUMA / ORIGINAL',8,12),('LUMA / INVERT',12,16),('FEATHER / PNG HOLE / OCCLUSION',16,20)]]}
        # Host auto-font applies only to these ASCII phase labels. All Chinese
        # source glyphs are immutable pixels; no Windows font is used at runtime.
        first=self.save('full',body);full=self.export('full-export',first);control=copy.deepcopy(body);control['effects'][-2:]=control['effects'][-2:][::-1];control['revision_reason']='Only swap foreground/window ordering';cp=self.save('control',control);cv=self.export('control-export',cp);body['revision_reason']='Restore original order as new immutable revision';rp=self.save('restored',body);rv=self.export('restored-export',rp)
        write(self.out/'exports-index.json',{'full':str(full),'control':str(cv),'restored':str(rv),'first_sha256':sha(full),'restored_sha256':sha(rv),'product_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=self.repo,text=True).strip(),'first_plan_id':first['id'],'control_plan_id':cp['id'],'restored_plan_id':rp['id']})
        before=self.context('before-negatives')
        for name in ['unknown-matte','non-image-matte','unknown-mode','invalid-invert','zero-crop','negative-crop','zero-slot','outside-slot','source-overrun','effect-overrun','alpha-channel-required']:
            bad=copy.deepcopy(rp['request']);bad.update(request_id='negative-'+uuid.uuid4().hex,project_revision=before['project']['revision'],supersedes=before['project']['timeline_head']);e=bad['effects'][0]
            if name=='unknown-matte':e['matte_id']='not-registered'
            elif name=='non-image-matte':e['matte_id']='video'
            elif name=='unknown-mode':e['matte_mode']='red-channel'
            elif name=='invalid-invert':e['invert']='not-a-boolean'
            elif name=='zero-crop':e['crop']['width']=0
            elif name=='negative-crop':e['crop']['height']=-.1
            elif name=='zero-slot':e['to_rect']['width']=0
            elif name=='outside-slot':e['to_rect']['x']=.99
            elif name=='source-overrun':e['source_in']=23
            elif name=='effect-overrun':e['end']=21
            elif name=='alpha-channel-required':e['matte_id']='bg'
            self.request('negative-'+name,'POST',f'/api/projects/{self.pid}/timeline-plans',bad,expected=422)
        after=self.context('after-negatives');assert before['project']['revision']==after['project']['revision'] and before['project']['timeline_head']==after['project']['timeline_head']
        return {'negative_cases':11,'head_revision_unchanged':True}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--repo',type=Path);parser.add_argument('--out',type=Path,required=True);parser.add_argument('--no-install',action='store_true');parser.add_argument('--also-v1',action='store_true',help='Additionally preserve the initial checker result; it is expected to expose the documented measurement defects')
    args=parser.parse_args();repo=repository(args.repo);out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    try:
        before=sealed_inputs(out);prerequisites(repo,out,args.no_install);result=Run(repo,out).execute()
        for version in (['v1','v2'] if args.also_v1 else ['v2']):
            command=[sys.executable,'-B',str(CAPSULE/'portable'/('verify_'+version+'.py')),'--out',str(out),'--materials',str(out/'materials')];done=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace');write(out/('checker-'+version+'-process.json'),{'command':command,'returncode':done.returncode,'stdout':done.stdout,'stderr':done.stderr});done.check_returncode()
        measured=read(out/'decoded-evidence-v2'/'measurements.json');assert before=={p.name:sha(p) for p in (out/'materials').glob('*') if p.is_file()}
        summary={'status':'PASS' if measured['all_checks_pass'] else 'FAIL','native_host':{'system':platform.system(),'platform':platform.platform(),'machine':platform.machine(),'python':sys.version},'product_commit':read(out/'exports-index.json')['product_commit'],'real_media_checks':len(measured['checks']),'all_real_media_checks_pass':measured['all_checks_pass'],'input_hashes_unchanged':True,**result,'scope':['Sealed20-second matte main case only; old Windows overflow history is not inherited','PNG has pre-authored feather; native hard-mask feather argument, alpha video codecs and mixed-alpha luma combinations are not claimed','No cross-host score inheritance, aesthetic or real-observation claim']};write(out/'summary.json',summary);print(json.dumps(summary,indent=2))
        if not measured['all_checks_pass']:raise RuntimeError('Actual decoded matte checks failed; first outputs preserved')
    except Exception:
        import traceback
        write(out/'failure.json',{'traceback':traceback.format_exc(),'system':platform.system(),'machine':platform.machine()});raise
if __name__=='__main__':main()
