"""Presealed independent observatory FX task on native Windows/macOS. No product fixtures."""
from pathlib import Path
import sys,json,copy,time,subprocess,hashlib
REPO=Path(__file__).resolve().parents[1]
CASE=REPO/'evaluation'/'independent_fx'
sys.path.insert(0,str(REPO/'scripts'))
from independent_timeline_acceptance import Run,read,write,sha,prerequisites

class FxRun(Run):
    def export_fx(self,name,plan):
        job=self.request(name+'-submit','POST',f'/api/projects/{self.pid}/timeline/export',{'plan_id':plan['id']})
        for n in range(180):
            job=self.request(f'{name}-poll-{n:03}','GET',f'/api/projects/{self.pid}/jobs/{job["id"]}')
            if job['status'] in ('done','failed','error'):
                write(self.output/(name+'-terminal.json'),job)
                if job['status']!='done':raise RuntimeError(json.dumps(job))
                return Path(self.env['SELF_MEDIA_DATA_DIR'])/self.pid/'exports'/job['result']['export_id']/'timeline.mp4'
            time.sleep(1)
        raise TimeoutError(name)
    def execute_fx(self):
        inputs=sorted((self.output/'materials').glob('*.mp4'))+[self.output/'materials'/'observatory_original_120bpm.wav']
        args=['run','Create the presealed observatory full-feature film: capture, align, transmit; two overlap transitions, true inward-feather rectangle/circle alpha masks, globally timed titles, continuous original music; no ASR','--intent','edit','--new','--title','Independent observatory FX blind task','--simulation','--media-nature','generated','--source-note','Original procedural observatory animation and synthesized audio, not real footage','--usage-scope','Independent local FX technical acceptance, no publication','--session','independent-observatory-fx-first']
        for p in inputs:args.extend(['--input',str(p)])
        intake=self.cli('intake',args);self.base=intake['service_url'];self.pid=intake['project_id']
        self.cli('capabilities',['call','GET','/api/agent/v1/capabilities']);self.cli('schema',['schema','timeline-plan'])
        ctx=self.context('first-context');media=ctx['project']['media']
        sources=[{'id':m['name'][0] if m['name'].endswith('.mp4') else 'music','kind':'media','asset_id':m['id'],'sha256':m['sha256']} for m in media]
        music=next(s for s in sources if s['id']=='music')
        self.request('onsets','POST',f'/api/projects/{self.pid}/music-onsets',{'media_id':music['asset_id'],'source_sha256':music['sha256'],'source_in':0,'source_out':13.5})
        plan={'request_id':'first-fx-draft','project_revision':ctx['project']['revision'],'supersedes':None,'revision_reason':'First presealed observatory complete film before output inspection','intent':'Capture signal, align target, transmit data; original illustration/audio, no real footage claim','width':1280,'height':720,'fps':30,'sources':sources,'shots':[{'id':sid.lower(),'source_id':sid,'source_in':a,'source_out':b,'fit':'contain','source_audio_gain':.2 if sid in 'RU' else 0,'role':role,'reason':'Preserve presealed story action and independent source clock'} for sid,a,b,role in [('R',1,5,'acquire'),('S',1,6,'align'),('U',.5,6.5,'transmit')]],'audio':[{'source_id':'music','role':'music','source_in':0,'start':0,'duration':13.5,'gain':.6,'fade_in':0,'fade_out':.25,'reason':'Original continuous 120 BPM clock across overlapping visuals'}],'titles':[{'text':text,'start':a,'end':b,'colour':'FFFFFF','font_height':.05,'bottom_margin':.08} for text,a,b in [('SIGNAL LOCK',3.7,4.3),('CAPTURE WINDOW',7.8,8.8),('UPLOAD COMPLETE',11.5,13.2)]],'transitions':[{'after_shot_id':'r','kind':'fade','duration':.5,'reason':'Signal acquisition gives way to star alignment'},{'after_shot_id':'s','kind':'wipeleft','duration':1,'reason':'The aligned observation moves into the transmission stage'}],'masks':[{'source_id':'F','source_in':si,'start':a,'end':b,'crop':{'x':0,'y':0,'width':1,'height':1},'slot':{'x':x/1280,'y':y/720,'width':320/1280,'height':320/720},'shape':shape,'feather':24,'opacity':1,'reason':'Diagnostic sensor feed shown through a real inward-feather alpha mask'} for shape,a,b,si,x,y in [('rectangle',1,3,2,800,160),('ellipse',9,11,7,180,220)]]}
        write(self.output/'first-unsaved-request.json',plan)
        first=self.save('full',plan);full=self.export_fx('full-export',first)
        control=copy.deepcopy(plan);control['masks']=[];control['sources']=[s for s in sources if s['id']!='F'];control['revision_reason']='Control: remove only diagnostic layers and unused F reference, preserve full base edit, titles and music'
        ctrl=self.save('control',control);control_video=self.export_fx('control-export',ctrl)
        plan['revision_reason']='Restore complete first FX decisions as a new immutable version'
        restored=self.save('restored',plan);restored_video=self.export_fx('restored-export',restored)
        write(self.output/'exports-index.json',{'full':str(full),'control':str(control_video),'restored':str(restored_video),'full_plan':first['id'],'control_plan':ctrl['id'],'restored_plan':restored['id'],'full_sha256':sha(full),'restored_sha256':sha(restored_video),'product_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()})
        self.base_plan=plan;self.first_plan=first;print('EXPORTED',self.output,flush=True)

    def negatives(self):
        ctx=self.context('negative-context')
        for name in ['transition-negative','transition-zero','transition-too-long','transition-unknown','feather-negative','slot-outside','mask-empty','layer-overrun','mask-unknown-source']:
            p=copy.deepcopy(self.first_plan['request']);p.update(request_id='independent-fx-negative-'+name,project_revision=ctx['project']['revision'],supersedes=ctx['project']['timeline_head'])
            if name=='transition-negative':p['transitions'][0]['duration']=-.5
            elif name=='transition-zero':p['transitions'][0]['duration']=0
            elif name=='transition-too-long':p['shots'][0]['source_out']=2;p['transitions'][0]['duration']=1.5
            elif name=='transition-unknown':p['transitions'][0]['kind']='unavailable'
            elif name=='feather-negative':p['masks'][0]['feather']=-1
            elif name=='slot-outside':p['masks'][0]['slot']['x']=.95
            elif name=='mask-empty':p['masks'][0]['slot']['width']=0
            elif name=='layer-overrun':p['masks'][0]['end']=20
            elif name=='mask-unknown-source':p['masks'][0]['source_id']='unregistered'
            self.request(name+'-rejected','POST',f'/api/projects/{self.pid}/timeline-plans',p,expected=422)
        stale=copy.deepcopy(self.first_plan['request']);stale['request_id']='independent-fx-stale'
        self.request('stale-rejected','POST',f'/api/projects/{self.pid}/timeline-plans',stale,expected=409)
        final=self.context('after-negatives-context')
        assert final['project']['timeline_head']==ctx['project']['timeline_head']

def stop_owned(run,checkout):
    """Only stop our recorded, command-verified, idle service; no unrelated PID."""
    import os,signal,urllib.request,uuid
    tag='owned-stop-'+uuid.uuid4().hex[:12]
    ctx=run.context('before-'+tag)
    assert all(j.get('status') not in ('running','queued','pending') for j in ctx['jobs'])
    for file in (run.output/'state'/'services').glob('*.json'):
        record=read(file)
        if Path(record['root']).resolve()!=checkout.resolve() or record['base_url']!=run.base:continue
        pid=int(record['pid'])
        command=(subprocess.check_output(['powershell','-NoProfile','-Command',f"(Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}').CommandLine"],text=True,encoding='utf-8',errors='replace') if sys.platform=='win32' else subprocess.check_output(['ps','-p',str(pid),'-o','command='],text=True))
        assert str(checkout).casefold() in command.casefold() and 'workbench.py' in command and 'serve' in command
        write(run.output/(tag+'.json'),{'pid':pid,'recorded_root':str(checkout),'command':command,'all_jobs_terminal':True})
        os.kill(pid,signal.SIGTERM)
        for _ in range(30):
            try:urllib.request.urlopen(run.base+'/api/status',timeout=.2).close()
            except Exception:return
            time.sleep(.1)
        raise RuntimeError('Owned service did not stop')
    raise RuntimeError('No matching owned service record')

def historical_compatibility(run):
    """Create an actual pre-FX frozen plan with historical code, then resume now."""
    import tarfile,uuid
    old_commit='6d3dc308006db9a59ac4ed73b874a2e5d0f4deb6'
    root=run.output/'historical';root.mkdir()
    available=subprocess.run(['git','cat-file','-e',old_commit+'^{commit}'],cwd=REPO,capture_output=True)
    if available.returncode:subprocess.run(['git','fetch','origin',old_commit,'--depth','1'],cwd=REPO,check=True)
    archive=root/'pre-fx-source.tar';checkout=root/'checkout';checkout.mkdir()
    subprocess.run(['git','archive','--format=tar','--output='+str(archive),old_commit],cwd=REPO,check=True)
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if not (checkout/member.name).resolve().is_relative_to(checkout.resolve()) or not (member.isfile() or member.isdir()):raise RuntimeError('Unexpected historical archive path/type')
        tar.extractall(checkout,filter='data')
    class OldRun(FxRun):
        def cli(self,name,args):
            dest=self.output/(name+'.json');cmd=[sys.executable,str(checkout/'workbench.py'),'--out',str(dest),*args]
            done=subprocess.run(cmd,cwd=checkout,env=self.env,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
            write(self.output/(name+'-process.json'),{'command':cmd,'returncode':done.returncode,'stdout':done.stdout,'stderr':done.stderr});done.check_returncode();return read(dest)
    oldout=root/'old-run';oldout.mkdir();old=OldRun(oldout)
    args=['run','Save and render an independent observatory timeline with the historical non-FX contract','--intent','edit','--new','--title','Independent genuine historical plan','--simulation','--media-nature','generated','--source-note','Original observatory animation, not real footage','--session','old-'+uuid.uuid4().hex]
    for path in sorted((run.output/'materials').glob('*.mp4')):
        if not path.name.startswith('F_'):args.extend(['--input',str(path)])
    args.extend(['--input',str(run.output/'materials'/'observatory_original_120bpm.wav')])
    intake=old.cli('intake',args);old.base=intake['service_url'];old.pid=intake['project_id'];ctx=old.context('old-context')
    body=copy.deepcopy(run.base_plan);body.pop('transitions');body.pop('masks');body['titles']=[];body['audio'][0]['duration']=15
    body['sources']=[{'id':m['name'][0] if m['name'].endswith('.mp4') else 'music','kind':'media','asset_id':m['id'],'sha256':m['sha256']} for m in ctx['project']['media']]
    body['revision_reason']='Historical pre-FX persisted record; no new optional fields'
    plan=old.save('historical-plan',body);assert 'masks' not in plan['request'] and 'transitions' not in plan['request']
    video=old.export_fx('old-export',plan);planfile=Path(old.env['SELF_MEDIA_DATA_DIR'])/old.pid/'timeline-plans'/plan['id']/'plan.json';original_hash=sha(planfile)
    stop_owned(old,checkout)
    nowout=root/'current-run';nowout.mkdir();now=FxRun(nowout);now.env['SELF_MEDIA_DATA_DIR']=old.env['SELF_MEDIA_DATA_DIR']
    intake=now.cli('resume',['run','Continue the genuine historical plan without changing frozen decisions','--intent','edit','--project',old.pid,'--session','historical-current']);now.base=intake['service_url'];now.pid=old.pid
    ctx=now.context('current-read');assert ctx['project']['timeline_head']==plan['id'];current=now.export_fx('current-export',plan)
    # Original request must also replay, without adding FX defaults or mutating head.
    replay=now.request('historical-request-replay','POST',f'/api/projects/{now.pid}/timeline-plans',plan['request']);assert replay['id']==plan['id']
    measurements=[]
    for label,path in [('historical',video),('current',current)]:
        p=json.loads(subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_streams','-of','json',str(path)]));v=next(s for s in p['streams'] if s['codec_type']=='video');assert int(v['nb_read_frames'])==450 and abs(float(v['duration'])-15)<1e-5;measurements.append({'version':label,'frames':int(v['nb_read_frames']),'duration':v['duration']})
    import importlib.util
    spec=importlib.util.spec_from_file_location('independent_fx_pixels',CASE/'check_fx.py');pixel=importlib.util.module_from_spec(spec);spec.loader.exec_module(pixel)
    before_frames,_=pixel.frames(video,{0,120,300,449});after_frames,_=pixel.frames(current,{0,120,300,449});identity=[]
    for n in before_frames:
        old_image=pixel.Image.fromarray(before_frames[n]).resize((320,180));new_image=pixel.Image.fromarray(after_frames[n]).resize((320,180));error=pixel.rmse(pixel.np.asarray(old_image),pixel.np.asarray(new_image));assert error<10;identity.append({'frame':n,'decoded_source_identity_rmse':error})
    assert sha(planfile)==original_hash
    result={'historical_commit':old_commit,'record_genuinely_lacks_fx_fields':True,'original_plan_sha256':original_hash,'original_plan_unchanged':True,'original_request_replay_id':replay['id'],'clocks':measurements,'decoded_source_identity':identity};write(root/'result.json',result);stop_owned(now,REPO);return result

def main():
    import argparse,importlib.util,shutil,platform,traceback
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--materials',type=Path);a=p.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);(out/'evidence').mkdir()
    shutil.copyfile(CASE/'FX_BLIND_TASK.md',out/'FX_BLIND_TASK.md')
    try:
        prerequisites(out)
        if a.materials:shutil.copytree(a.materials.resolve(),out/'materials')
        else:
            spec=importlib.util.spec_from_file_location('fx_materials',CASE/'generate_materials.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=out;m.OUT=out/'materials';m.OUT.mkdir();m.main()
        before={p.name:sha(p) for p in (out/'materials').glob('*') if p.is_file()};write(out/'input-seal.json',before)
        run=FxRun(out);run.execute_fx();run.negatives()
        check=subprocess.run([sys.executable,str(CASE/'check_fx.py'),'--output',str(out),'--materials',str(out/'materials')],capture_output=True,text=True,encoding='utf-8',errors='replace');write(out/'checker-process.json',{'returncode':check.returncode,'stdout':check.stdout,'stderr':check.stderr})
        pixels=read(out/'independent-pixel-audio-v2'/'result.json')
        head=run.context('before-restart-context')['project']['timeline_head'];stop_owned(run,REPO)
        intake=run.cli('resume-own',['run','Continue the full observatory FX timeline with original decisions','--intent','edit','--project',run.pid,'--session','fx-resume']);run.base=intake['service_url'];assert run.context('after-restart-context')['project']['timeline_head']==head
        legacy=historical_compatibility(run)
        assert before=={p.name:sha(p) for p in (out/'materials').glob('*') if p.is_file()}
        summary={'status':'independent_fx_decoded_checks_passed' if pixels['all_technical_checks_pass'] else 'independent_fx_decoded_checks_failed','product_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'platform':platform.platform(),'machine':platform.machine(),'all_pixel_audio_clock_restore_checks_pass':pixels['all_technical_checks_pass'],'illegal_requests_rejected':True,'restart_resume_head_unchanged':True,'historical_compatibility':legacy,'input_hashes_unchanged':True,'limits':['Original synthetic observatory illustrations/audio, not real filming','Pixel/waveform technical checks do not prove aesthetic/listening quality or real tourism','Only the reported native host was executed']};write(out/'summary.json',summary);print(json.dumps(summary,indent=2));stop_owned(run,REPO)
        if not pixels['all_technical_checks_pass']:raise RuntimeError('Independent pixel/audio check failed; all outputs retained')
    except Exception:
        write(out/'failure.json',{'traceback':traceback.format_exc(),'platform':platform.platform(),'machine':platform.machine()});raise

if __name__=='__main__':main()
