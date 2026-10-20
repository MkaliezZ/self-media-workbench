"""Real Chinese ASR, source-bound proofreading, pause cut and restore acceptance.

The reference is known synthetic TTS input. Reference-assisted substitutions
are not an automatic production proofreader or an ASR accuracy improvement.
"""
import argparse
import difflib
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import time
import traceback
from pathlib import Path
from opencc import OpenCC
from fresh_macos_acceptance import Audit,sha

CC=OpenCC('t2s')
MODELS=[('ct2','Systran/faster-whisper-small','536b0662742c02347bc0e980a01041f333bce120'),
        ('mlx','mlx-community/whisper-small-mlx','45f3915923c7a79a5a5b5a7d909d39aeb0e5630e')]


def bare(text):return ''.join(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',text))


def norm(text):
    # Exact equivalents in this fixture only. ASR may split 48000 into 48/000.
    # Apply the same mapping to whole text and existing word groups.
    value=bare(CC.convert(text))
    for a,b in [('48000','四十八千'),('24','二十四'),('48','四十八'),('000','千'),('赫兹','赫')]:value=value.replace(a,b)
    return re.sub('hz','赫',value,flags=re.I)


def error_stats(reference,hypothesis):
    a,b=reference,hypothesis;n,m=len(a),len(b)
    dp=[[0]*(m+1) for _ in range(n+1)]
    for i in range(n+1):dp[i][0]=i
    for j in range(m+1):dp[0][j]=j
    for i in range(1,n+1):
        for j in range(1,m+1):dp[i][j]=min(dp[i-1][j-1]+(a[i-1]!=b[j-1]),dp[i-1][j]+1,dp[i][j-1]+1)
    edits=[];i,j=n,m
    while i or j:
        if i and j and dp[i][j]==dp[i-1][j-1]+(a[i-1]!=b[j-1]):
            if a[i-1]!=b[j-1]:edits.append({'op':'S','reference':a[i-1],'recognized':b[j-1],'reference_index':i-1,'hypothesis_index':j-1})
            i-=1;j-=1
        elif i and dp[i][j]==dp[i-1][j]+1:
            edits.append({'op':'D','reference':a[i-1],'recognized':'','reference_index':i-1,'hypothesis_index':j});i-=1
        else:
            edits.append({'op':'I','reference':'','recognized':b[j-1],'reference_index':i,'hypothesis_index':j-1});j-=1
    edits.reverse()
    return {'S':sum(e['op']=='S' for e in edits),'D':sum(e['op']=='D' for e in edits),'I':sum(e['op']=='I' for e in edits),'N':n,'CER':dp[n][m]/max(1,n),'edits':edits}


def reference_review(words,reference):
    chunks=[norm(w['text']) for w in words];actual=''.join(chunks);target=norm(reference)
    owners=[i for i,c in enumerate(chunks) for _ in c];replaced=list(actual);unresolved=[];typos=[]
    for tag,a,b,c,d in difflib.SequenceMatcher(None,actual,target,autojunk=False).get_opcodes():
        if tag=='equal':continue
        if tag!='replace' or b-a!=d-c:
            unresolved.append({'kind':tag,'recognized':actual[a:b],'reference':target[c:d],'reason':'No fabricated timestamps or reference-only insertion/deletion'});continue
        replaced[a:b]=target[c:d]
        typos.append({'recognized':actual[a:b],'reference':target[c:d],'word_ids':sorted({words[owners[k]]['id'] for k in range(a,b)})})
    corrections={};decisions=[];cursor=0
    for index,word in enumerate(words):
        text=CC.convert(word['text']);new=''.join(replaced[cursor:cursor+len(chunks[index])]);cursor+=len(chunks[index])
        if new!=chunks[index]:
            if bare(text)!=chunks[index] or len(bare(text))!=len(new):
                unresolved.append({'word_id':word['id'],'reason':'Normalized numeric/group mapping cannot safely project a substitution'});continue
            iterator=iter(new);text=''.join(next(iterator) if bare(ch) else ch for ch in text)
        if text!=word['text']:
            corrections[str(word['id'])]=text
            decisions.append({'id':word['id'],'before':word['text'],'after':text,'source_start':word['start'],'source_end':word['end'],'kind':'orthography' if norm(word['text'])==norm(text) else 'reference_assisted_substitution'})
    return corrections,{'mode':'Known synthetic reference assisted; not human listening or general automatic proofreading','typos':typos,'decisions':decisions,'unresolved':unresolved}


def chinese_groups(words,reference):
    breaks=[];cursor=0
    for phrase in re.split(r'[，。；！？]',reference):
        cursor+=len(norm(phrase))
        if phrase:breaks.append(cursor)
    groups=[];current=[];cursor=0;boundary=0;characters=0
    for w in words:
        current.append(w);cursor+=len(norm(w['text']));characters+=len(norm(w['text']))
        if boundary<len(breaks) and cursor>=breaks[boundary]:
            while boundary<len(breaks) and cursor>=breaks[boundary]:boundary+=1
            if characters>=4 and current[-1]['end']-current[0]['start']>=.9:
                groups.append(current);current=[];characters=0
    if current:
        if groups and (len(norm(''.join(w['text'] for w in current)))<4 or current[-1]['end']-current[0]['start']<.9):groups[-1].extend(current)
        else:groups.append(current)
    return [[w['id'] for w in group] for group in groups]


class ChineseAudit(Audit):
    def __init__(self,args):
        super().__init__(args)
        self.py=self.root/('.venv/Scripts/python.exe' if os.name=='nt' else '.venv/bin/python')
        self.fresh=False;self.started_service=False

    def setup(self):
        expected={'windows':('win32',None),'arm64':('darwin','arm64'),'intel':('darwin','x86_64')}[self.args.profile]
        self.check('native platform',__import__('sys').platform==expected[0] and (not expected[1] or platform.machine()==expected[1]))
        self.commit=self.run('checkout-sha',['git','rev-parse','HEAD']).strip()
        self.check('clean public clone',not self.run('checkout-status',['git','status','--porcelain']).strip())
        self.check('fresh application state',not (self.state/'config.json').exists() and not any((self.state/'services').glob('*.json')))
        self.fresh=True
        for key,path in [('SELF_MEDIA_STATE_DIR',self.state),('CODEX_HOME',self.agent),('HF_HOME',self.hf)]:self.env[key]=str(path)
        self.check('no configuration bypass',not any(k.startswith('SELF_MEDIA_') and k!='SELF_MEDIA_STATE_DIR' for k in self.env))
        self.env.update(PYTHONNOUSERSITE='1',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',HF_HUB_DISABLE_XET='1')
        self.run('pip-check',[self.py,'-m','pip','check'])
        self.cli('doctor-before-configure','doctor')
        paths={}
        for kind,repo,rev in MODELS:
            if kind=='mlx' and self.args.profile!='arm64':continue
            code='''import json,hashlib,sys
from pathlib import Path
from huggingface_hub import HfApi,snapshot_download
repo,rev,dest,output=sys.argv[1:]
info=HfApi().model_info(repo,revision=rev,files_metadata=True);remote={s.rfilename:s for s in info.siblings}
p=Path(snapshot_download(repo,revision=rev,local_dir=dest,allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*','preprocessor_config.json','*.safetensors','weights.npz']))
files=[]
for f in sorted(p.rglob('*')):
 if not f.is_file() or '.cache' in f.parts:continue
 rel=f.relative_to(p).as_posix();s=remote[rel];lfs=s.lfs
 with f.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
 expected=lfs.sha256 if lfs else None
 blob=hashlib.sha1(b'blob '+str(f.stat().st_size).encode()+b'\\0'+f.read_bytes()).hexdigest() if not lfs else None
 files.append(dict(file=rel,sha256=actual,expected_lfs_sha256=expected,expected_git_blob=s.blob_id,actual_git_blob=blob,verified=actual==expected if lfs else blob==s.blob_id))
value=dict(repo=repo,requested_revision=rev,resolved_revision=info.sha,files=files,verified=bool(files) and info.sha==rev and all(f['verified'] for f in files))
Path(output).parent.mkdir(parents=True,exist_ok=True);Path(output).write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value));raise SystemExit(0 if value['verified'] else 3)
'''
            dest=self.hf/'models'/kind
            self.run('download-'+kind,[self.py,'-c',code,repo,rev,dest,self.out/'models'/(kind+'.json')],env={**self.env,'HF_HUB_OFFLINE':'0','TRANSFORMERS_OFFLINE':'0'},timeout=1800)
            paths[kind]=dest
        options=['configure','--model',paths['ct2'],'--language','zh','--asr-backend','auto','--device','auto' if self.args.profile=='arm64' else 'cpu']
        if 'mlx' in paths:options+=['--mlx-model',paths['mlx']]
        self.cli('configure',*options);self.cli('doctor-configured','doctor');self.cli('install-entry','install-skill')
        self.fixture=json.loads((self.root/'fixtures/chinese-talk/fixture.json').read_text('utf-8'))
        self.source=self.root/'fixtures/chinese-talk/synthetic-zh.mkv'
        self.check('identical fixture SHA256',sha(self.source)==self.fixture['source_sha256'])
        self.started_service=True
        task=self.cli('intake','run','中文口播验收：纠错、字幕断句、只删空白A并恢复；展示停顿B保留','--intent','edit','--new','--simulation','--input',self.source,'--media-nature','generated','--source-note','Same newly authored synthetic Chinese PCM fixture, no recorded person','--session','chinese-acceptance')
        self.pid=task['project_id'];self.mid=task['registered'][0]['id'];self.prefix=f'/api/projects/{self.pid}/media/{self.mid}'
        self.check('service actual checkout',Path(self.call('service-status','GET','/api/status')['root']).resolve()==self.root)

    def edit(self,name,review,**changes):
        return self.call(name,'PUT',self.prefix+'/review',{'revision':review.get('revision',0),'asr_run':review['asr_run'],'source_sha256':review['source_sha256'],**changes})

    def export(self,name,review):
        job=self.call(name+'-submit','POST',self.prefix+'/export',{'revision':review.get('revision',0),'asr_run':review['asr_run'],'source_sha256':review['source_sha256']})
        terminal=self.wait(name,self.pid,job)
        d=self.state/'projects'/self.pid/'exports'/terminal['result']['export_id']
        self.run(name+'-decode',['ffmpeg','-v','error','-nostdin','-i',d/'reviewed_cut.mp4','-map','0:v:0','-map','0:a:0','-f','null','-'],timeout=300)
        probe=json.loads(self.run(name+'-probe',['ffprobe','-v','error','-show_format','-of','json',d/'reviewed_cut.mp4']))
        words=json.loads((d/'reviewed_cut.words.json').read_text('utf-8'));plan=json.loads((d/'edit-decision.json').read_text('utf-8'))
        self.check(name+' retains every word ID',[w['id'] for w in words]==[w['id'] for w in review['words']])
        self.check(name+' duration matches actual plan',abs(float(probe['format']['duration'])-plan['output_duration'])<.15)
        cursor=0;windows=[]
        for k in plan['keeps']:windows.append((k['start'],k['end'],cursor));cursor+=k['end']-k['start']
        for a,b in zip(review['words'],words):
            lo,hi,dest=next(k for k in windows if a['start']>=k[0]-1e-6 and a['end']<=k[1]+1e-6)
            self.check(name+' word '+str(a['id']),a['text']==b['text'] and a['probability']==b['asr_probability'] and a['start']==b['source_start'] and a['end']==b['source_end'] and abs(b['start']-(a['start']-lo+dest))<2e-6 and abs(b['end']-(a['end']-lo+dest))<2e-6)
        if name!='raw':
            lookup={w['id']:w for w in words};cues=[b.splitlines() for b in (d/'reviewed_cut.srt').read_text('utf-8').strip().split('\n\n')]
            def sec(s):
                h,m,t=s.split(':');a,b=t.split(',');return int(h)*3600+int(m)*60+int(a)+int(b)/1000
            self.check(name+' cue count',len(cues)==len(review['caption_groups']))
            for cue,group in zip(cues,review['caption_groups']):
                a,b=cue[1].split(' --> ');text=''.join(lookup[i]['text'] for i in group)
                self.check(name+' cue '+cue[0],'\n'.join(cue[2:])==text and abs(sec(a)-lookup[group[0]]['start'])<.0011 and abs(sec(b)-lookup[group[-1]]['end'])<.0011 and sec(b)-sec(a)>=.899 and len(norm(text))>=4)
        shutil.copytree(d,self.out/'delivered'/name)
        return d,plan,words

    def exercise(self):
        self.asr_execution=self.wait('asr',self.pid,self.call('asr-submit','POST',self.prefix+'/transcribe'))['result']
        original=self.call('original-review','GET',self.prefix+'/review');self.original=original
        self.check('actual requested backend',original['backend']==('mlx' if self.args.profile=='arm64' else 'faster-whisper') and original['device']==('gpu' if self.args.profile=='arm64' else 'cpu') and not original['fallback_errors'])
        if self.args.profile=='arm64':self.check('real GPU kernel',original['execution'].get('gpu_kernel_verified') and original['execution'].get('isolated_worker'))
        rawfile=Path(original['source']).parent/'asr'/original['asr_run']/'transcript.original.json';original_hash=sha(rawfile)
        rawdir,_,_=self.export('raw',original)
        reference=self.fixture['reference_text'];rawtext=''.join(w['text'] for w in original['words'])
        self.save('asr-error-analysis.json',{'raw':error_stats(bare(reference),bare(rawtext)),'orthography_and_numeric_normalized':error_stats(norm(reference),norm(rawtext)),'raw_text':rawtext,'reference':reference,'normalization':'OpenCC t2s; fixture-only 24=二十四,48=四十八,000=千,48000=四十八千,Hz/赫兹=赫; punctuation/whitespace excluded','source_sha256':original['source_sha256']})
        self.check('whole text and group normalization agree',norm(rawtext)==''.join(norm(w['text']) for w in original['words']))
        corrections,reason=reference_review(original['words'],reference);self.save('reference-assisted-review.json',reason)
        self.check('no unsupported reference insertion or deletion',not reason['unresolved'],reason)
        fixed=self.edit('proofread',original,corrections=corrections)['review']
        self.save('post-review-error-analysis.json',error_stats(norm(reference),norm(fixed['text'])))
        self.check('reference assisted display text matches',norm(fixed['text'])==norm(reference),'This does not change original ASR accuracy')
        groups=chinese_groups(fixed['words'],reference)
        fixed=self.edit('group-captions',fixed,caption_groups=groups)['review']
        full,_,_=self.export('reviewed-full',fixed)
        A,B=self.fixture['gaps']
        # Native TTS includes silent padding before the inserted gap. Accept a
        # candidate in that same contiguous silent interval only after examining
        # every decoded source sample, rather than assuming inserted gap bounds.
        import array,math
        pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(self.source),'-ar','16000','-ac','1','-f','f32le','-'])
        samples=array.array('f');samples.frombytes(pcm)
        def peak(a,b):return max((abs(x) for x in samples[round(a*16000):round(b*16000)]),default=1)
        inspected=[];candidates=[]
        for c in fixed['candidates']:
            overlap=min(c['end'],A['end'])-max(c['start'],A['start'])
            lo,hi=min(c['start'],A['start']),max(c['end'],A['end'])
            p=peak(lo,hi) if overlap>0 else None
            allowed=overlap>=.4 and p is not None and p<.005
            inspected.append({'candidate':c,'overlap_with_inserted_A':overlap,'union_source_peak':p,'allowed':allowed})
            if allowed:candidates.append(c)
        self.save('pause-source-inspection.json',{'policy':'Only A-overlapping candidate whose union with A is silent in every decoded source sample; B remains excluded','candidates':inspected})
        self.check('authorized pause A has safe candidate',bool(candidates),{'A':A,'candidates':fixed['candidates']})
        cut=max(candidates,key=lambda c:c['end']-c['start'])
        result=self.edit('cut-A',fixed,selected_ids=[cut['id']]);review=result['review']
        cutdir,plan,cutwords=self.export('cut-A',review)
        self.check('only authorized silent A interval removed',len(plan['cuts'])==1 and plan['cuts'][0]['start']==cut['start'] and plan['cuts'][0]['end']==cut['end'])
        self.check('demonstration hold B fully kept',any(k['start']<=B['start'] and k['end']>=B['end'] for k in plan['keeps']))
        cut_hashes={f.name:sha(f) for f in cutdir.iterdir() if f.is_file()}
        failure=self.save('requests/stale-negative-probe.json',{'revision':fixed['revision'],'asr_run':fixed['asr_run'],'source_sha256':fixed['source_sha256'],'selected_ids':[]})
        rejected=json.loads(self.run('intentional-stale-probe',[self.py,self.root/'workbench.py','call','PUT',self.prefix+'/review','--json',failure],ok=(2,)))
        self.check('real stale rejection retained',rejected.get('http_status')==409,rejected)
        current=self.call('current-before-restore','GET',self.prefix+'/review')
        restored=self.edit('restore-A',current,selected_ids=[])['review']
        restored_dir,restored_plan,restored_words=self.export('restored',restored)
        self.check('restored complete source plan',restored_plan['cuts']==[] and len(restored_plan['keeps'])==1 and restored_plan['keeps'][0]['start']==0 and restored_plan['keeps'][0]['end']==original['duration'])
        self.check('restoration keeps corrections and caption decisions',restored['words']==fixed['words'] and restored['caption_groups']==groups)
        self.check('source and original ASR immutable',sha(self.source)==self.fixture['source_sha256'] and sha(rawfile)==original_hash)
        self.check('previous cut export immutable',all(sha(cutdir/name)==value for name,value in cut_hashes.items()))
        # Binary PCM is captured separately, not decoded as text.
        def rms(path,a,b):
            pcm=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-ar','16000','-ac','1','-f','f32le','-'])
            x=array.array('f');x.frombytes(pcm);v=x[round(a*16000):round(b*16000)];return math.sqrt(sum(t*t for t in v)/max(1,len(v)))
        restored_rms=rms(restored_dir/'reviewed_cut.mp4',A['start']+.6,A['end']-.6)
        self.check('restored actual silent interval A',restored_rms<.005,restored_rms)
        mapped_b=B['start']-(cut['end']-cut['start'])
        self.check('actual display hold B remains in cut',rms(cutdir/'reviewed_cut.mp4',mapped_b+.5,mapped_b+1.2)<.005)
        self.save('result-detail.json',{'source_sha256':sha(self.source),'pcm_sha256':self.fixture['pcm_sha256'],'original_asr_sha256':original_hash,'word_groups':len(original['words']),'caption_groups':len(groups),'actual_backend':original['backend'],'actual_device':original['device'],'reference_assisted_corrections':reason,'cut':cut,'restored_source_duration':restored_plan['output_duration'],'restored_silence_rms':restored_rms,'unverified':['human listening','general ASR accuracy or automatic proofreading','target player typography','noisy/long/human speech']})

    def finish(self,error=None):
        cleanup={'only_own_service':True}
        if self.fresh and self.started_service:
            for f in (self.state/'services').glob('*.json'):
                try:
                    info=json.loads(f.read_text('utf-8'));pid=int(info['pid'])
                    if Path(info['root']).resolve()!=self.root:raise RuntimeError('Wrong checkout; will not stop')
                    if os.name=='nt':
                        cmd=self.run('process-identity',['powershell','-NoProfile','-Command',f'(Get-CimInstance Win32_Process -Filter "ProcessId={pid}").CommandLine']).strip()
                    else:cmd=self.run('process-identity',['ps','-p',str(pid),'-o','command='],ok=(0,1)).strip()
                    if cmd:
                        if str(self.root/'workbench.py').lower() not in cmd.lower() or 'serve' not in cmd:raise RuntimeError('Wrong process; will not stop')
                        os.kill(pid,signal.SIGTERM)
                    for _ in range(60):
                        if os.name=='nt':
                            p=subprocess.run(['powershell','-NoProfile','-Command',f'if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) {{ exit 1 }}'],capture_output=True);gone=p.returncode==0
                        else:
                            p=subprocess.run(['ps','-p',str(pid),'-o','stat='],capture_output=True,text=True);gone=p.returncode!=0 or not p.stdout.strip() or p.stdout.strip().startswith('Z')
                        if gone:cleanup['exit_confirmed']=True;break
                        time.sleep(.1)
                    if not cleanup.get('exit_confirmed'):raise RuntimeError('Service did not exit')
                except Exception as exc:cleanup['error']=repr(exc)
        self.save('cleanup.json',cleanup);self.check('own service exit before sealing','error' not in cleanup,cleanup,fatal=False)
        result={'passed':error is None and all(x['passed'] for x in self.results),'profile':self.args.profile,'platform':__import__('sys').platform,'architecture':platform.machine(),'commit':getattr(self,'commit',None),'asr_execution':getattr(self,'asr_execution',None),'exception':error,'failures':[x for x in self.results if not x['passed']],'scope':'Synthetic Chinese reference-assisted review, not human speech accuracy or a live LLM trial'}
        self.save('final-result.json',result);self.save('failure.json',{'exception':error,'failures':result['failures']})
        excluded={'hf-home','foreign-python','pip-cache','.git','.venv'}
        rows=[{'path':p.relative_to(self.out).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(self.out.rglob('*')) if p.is_file() and not any(x in excluded for x in p.relative_to(self.out).parts) and p.name not in {'evidence-manifest.json','first-use.log'}]
        self.save('evidence-manifest.json',rows);print(json.dumps(result,ensure_ascii=False));return 0 if result['passed'] else 1


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',required=True);parser.add_argument('--out',required=True);parser.add_argument('--profile',choices=['windows','arm64','intel'],required=True);args=parser.parse_args()
    audit=ChineseAudit(args);error=None
    try:audit.setup();audit.exercise()
    except BaseException as exc:error={'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()}
    return audit.finish(error)


if __name__=='__main__':raise SystemExit(main())
