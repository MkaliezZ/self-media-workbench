"""Explicit opt-in real ASR/HTTP/export smoke on Windows and macOS CI.

Downloads only when --download-ci-model is supplied. Production never does so.
"""
import argparse
import json
import os
import platform
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--download-ci-model',action='store_true');parser.add_argument('--model',type=Path)
    parser.add_argument('--download-ci-mlx-model',action='store_true');parser.add_argument('--mlx-model',type=Path)
    parser.add_argument('--backend',choices=['auto','faster-whisper','mlx'],default='faster-whisper')
    parser.add_argument('--require-gpu',action='store_true')
    parser.add_argument('--out',type=Path,default=ROOT/'evaluation/runs/ci-smoke.json');args=parser.parse_args()
    if not args.model and not args.download_ci_model:parser.error('Provide a local --model or explicitly allow the CI model download')
    if args.download_ci_model:
        from huggingface_hub import snapshot_download
        model=Path(snapshot_download('Systran/faster-whisper-tiny',allow_patterns=['config.json','model.bin','tokenizer.json','vocabulary.*','preprocessor_config.json']))
    else:model=args.model.resolve()
    mlx_model=args.mlx_model
    if args.download_ci_mlx_model:
        from huggingface_hub import snapshot_download
        mlx_model=Path(snapshot_download('mlx-community/whisper-tiny',allow_patterns=['config.json','*.safetensors','weights.npz']))
    with tempfile.TemporaryDirectory(prefix='workbench-real-smoke-') as directory:
        temp=Path(directory);env={**os.environ,'SELF_MEDIA_STATE_DIR':str(temp/'state'),'SELF_MEDIA_MODEL':str(model),
            'SELF_MEDIA_LANGUAGE':'en','SELF_MEDIA_DEVICE':'auto' if args.backend!='faster-whisper' else 'cpu',
            'SELF_MEDIA_ASR_BACKEND':args.backend,'CODEX_HOME':str(temp/'agent-home')}
        if mlx_model:env['SELF_MEDIA_MLX_MODEL']=str(mlx_model)
        env.pop('SELF_MEDIA_DATA_DIR',None);env.pop('SELF_MEDIA_SKILL_ROOT',None)
        wav=temp/'spoken.wav';text='This is an original local test. Keep every important condition. This is not a promise.'
        if sys.platform=='darwin':
            aiff=temp/'spoken.aiff';subprocess.run(['say','-r','165','-o',str(aiff),text],check=True)
            subprocess.run(['ffmpeg','-v','error','-i',str(aiff),str(wav)],check=True)
        elif os.name=='nt':
            env['SELF_MEDIA_TEST_AUDIO']=str(wav)
            code="Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.SetOutputToWaveFile($env:SELF_MEDIA_TEST_AUDIO); $s.Speak('"+text+"'); $s.Dispose()"
            subprocess.run(['powershell','-NoProfile','-NonInteractive','-Command',code],env=env,check=True)
        else:raise RuntimeError('This real-TTS smoke targets Windows/macOS; unit/media tests also work elsewhere')
        source=temp/'synthetic 原件.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=navy:s=320x240:r=25',
            '-i',str(wav),'-af','apad=pad_dur=1.5','-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(source)],check=True)
        def cli(*values):
            proc=subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'workbench.py'),*map(str,values)],env=env,
                                capture_output=True,text=True,encoding='utf-8',errors='replace')
            if proc.returncode:raise RuntimeError(proc.stdout+'\n'+proc.stderr)
            return json.loads(proc.stdout)
        def payload(name,data):
            p=temp/(name+'.json');p.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');return p
        def job(pid,jid):
            deadline=time.monotonic()+180
            while time.monotonic()<deadline:
                x=cli('call','GET',f'/api/projects/{pid}/jobs/{jid}')
                if x['status']=='done':return x
                if x['status'] in ('failed','interrupted'):raise RuntimeError(json.dumps(x))
                time.sleep(.5)
            raise RuntimeError('Job did not finish within smoke deadline')
        try:
            cli('install-skill')
            wrapper=temp/'agent-home/skills/media-workbench/scripts/run.py'
            installed=json.loads(subprocess.check_output([sys.executable,str(wrapper),'doctor'],env=env,encoding='utf-8'))
            assert Path(installed['root']).resolve()==ROOT and installed['dependencies']['faster_whisper']
            intake=cli('run','Transcribe and edit this original test','--intent','edit','--simulation','--input',source,
                       '--media-nature','generated','--source-note','Explicit CI TTS and color fixture, not a person')
            pid=intake['project_id'];mid=intake['registered'][0]['id'];prefix=f'/api/projects/{pid}/media/{mid}'
            asr=job(pid,cli('call','POST',prefix+'/transcribe')['id']);review=cli('call','GET',prefix+'/review')
            assert review['words'] and 'revision' in review
            if args.backend=='faster-whisper':assert review['device']=='cpu'
            edited=cli('call','PUT',prefix+'/review','--json',payload('review',{'revision':review['revision'],
                'asr_run':review['asr_run'],'source_sha256':review['source_sha256'], 'selected_ids':[], 'speech_cuts':[],
                'caption_groups':[[w['id'] for w in review['words']]]}))
            export=job(pid,cli('call','POST',prefix+'/export','--json',payload('export',{
                'revision':edited['review']['revision'],'asr_run':review['asr_run'],'source_sha256':review['source_sha256']}))['id'])
            context=cli('context',pid);eid=export['result']['export_id'];video=temp/'state/projects'/pid/'exports'/eid/'reviewed_cut.mp4'
            metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(video)]))
            subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True,capture_output=True)
            actual_duration=float(metadata['format']['duration'])
            exported_words=json.loads(video.with_name('reviewed_cut.words.json').read_text('utf-8'))
            timing_checks={
                'duration_matches_source':abs(actual_duration-review['duration'])<.15,
                'duration_matches_plan':abs(actual_duration-edited['plan']['output_duration'])<.15,
                'word_ids_unchanged':[w['id'] for w in exported_words]==[w['id'] for w in review['words']],
                'uncut_word_bounds_unchanged':len(exported_words)==len(review['words']) and all(
                    abs(a['start']-b['start'])<1e-5 and abs(a['end']-b['end'])<1e-5 for a,b in zip(exported_words,review['words'])),
                'last_word_within_output':max((w['end'] for w in exported_words),default=0)<=actual_duration+.1}
            result={'platform':sys.platform,'machine':platform.machine(),'python':sys.version,'real_asr':True,
                'actual_device':review['device'],'words':len(review['words']),'asr_job_status':asr['status'],
                'actual_backend':review['backend'],'execution':review['execution'],
                'fallback_errors':review['fallback_errors'],
                'gpu_asr_verified':review['backend']=='mlx' and review['device']=='gpu' and review['execution'].get('gpu_kernel_verified') is True,
                'installed_agent_entry':True,
                'export_job_status':export['status'],'decoded':True,'actual_duration':actual_duration,
                'source_duration':review['duration'],'source_sha256':review['source_sha256'],
                'planned_duration':edited['plan']['output_duration'],'timing_checks':timing_checks,
                'timing_verified':all(timing_checks.values()),
                'model':('MLX whisper-tiny' if args.download_ci_mlx_model else 'explicit local MLX model') if review['backend']=='mlx' else ('faster-whisper-tiny' if args.download_ci_model else 'explicit local CTranslate2 model'),
                'model_format':'MLX' if review['backend']=='mlx' else 'CTranslate2',
                'scope':'synthetic technical smoke; no human or publication effectiveness claim'}
            args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
            if not result['timing_verified']:raise RuntimeError('Actual source/plan/export timing mismatch; see saved result')
            if args.require_gpu and not result['gpu_asr_verified']:raise RuntimeError('GPU ASR required but actual result used another device; see saved result')
        finally:
            for info in (temp/'state/services').glob('*.json'):
                pid=json.loads(info.read_text('utf-8'))['pid']
                try:os.kill(pid,signal.SIGTERM)
                except ProcessLookupError:pass
            time.sleep(.5)


if __name__=='__main__':main()
