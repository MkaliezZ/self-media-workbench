"""Explicit delivery mastering: retain native video bytes and all audio reports."""
import argparse,hashlib,json,subprocess
from pathlib import Path


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def run(args,out,name):
    p=subprocess.run(args,capture_output=True,timeout=900)
    (out/(name+'.stderr.txt')).write_bytes(p.stderr)
    (out/(name+'.process.json')).write_text(json.dumps({'command':args,'returncode':p.returncode},ensure_ascii=False,indent=2),'utf-8')
    if p.returncode:raise RuntimeError('Audio mastering failed; original retained. Inspect '+name+'.stderr.txt')
    return p


def measured(stderr):
    text=stderr.decode('utf-8',errors='replace');start=text.rfind('{')
    if start<0:raise RuntimeError('No loudness measurement in retained FFmpeg report')
    return json.JSONDecoder().raw_decode(text[start:])[0]


def master(source,out,target=-17.,peak=-1.8):
    source=source.resolve();out=out.resolve();out.mkdir(parents=True,exist_ok=False)
    if not source.is_file():raise ValueError('Provide an existing native video export')
    probe=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(source)],out,'input-probe').stdout)
    video=next(s for s in probe['streams'] if s['codec_type']=='video')
    duration=float(video.get('duration') or probe['format']['duration'])
    before=sha(source);filter=f'loudnorm=I={target}:TP={peak}:LRA=11'
    first=run(['ffmpeg','-hide_banner','-nostdin','-i',str(source),'-map','0:a:0','-af',filter+':print_format=json','-f','null','-'],out,'pass1')
    m=measured(first.stderr)
    if m['input_i'] in ('-inf','inf'):raise ValueError('Silent audio cannot be mastered into speech')
    second=filter+f":measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true:print_format=json"
    destination=out/'mastered.mp4'
    run(['ffmpeg','-hide_banner','-nostdin','-n','-i',str(source),'-map','0:v:0','-map','0:a:0','-c:v','copy','-af',second+f',atrim=duration={duration},asetpts=PTS-STARTPTS','-t',str(duration),'-ar','48000','-c:a','aac','-b:a','192k','-movflags','+faststart',str(destination)],out,'pass2')
    verify=measured(run(['ffmpeg','-hide_banner','-nostdin','-i',str(destination),'-map','0:a:0','-af',filter+':print_format=json','-f','null','-'],out,'verify').stderr)
    streams=[]
    for p in [source,destination]:
        # The workbench native MP4 encoder is H.264. Reject other formats rather
        # than silently applying an incompatible bitstream filter.
        meta=json.loads(run(['ffprobe','-v','error','-show_streams','-show_format','-count_frames','-of','json',str(p)],out,'probe-'+str(len(streams))).stdout)
        v=next(s for s in meta['streams'] if s['codec_type']=='video')
        if v['codec_name']!='h264':raise ValueError('This mastering helper expects a native H.264 export')
        bits=run(['ffmpeg','-v','error','-nostdin','-i',str(p),'-map','0:v:0','-c:v','copy','-bsf:v','h264_mp4toannexb','-f','h264','-'],out,'video-hash-'+str(len(streams))).stdout
        streams.append({'file':str(p),'frames':int(v['nb_read_frames']),'video_elementary_sha256':hashlib.sha256(bits).hexdigest(),'duration':meta['format']['duration']})
    same=streams[0]['video_elementary_sha256']==streams[1]['video_elementary_sha256'] and streams[0]['frames']==streams[1]['frames']
    result={'input':str(source),'input_sha256':before,'output':str(destination),'output_sha256':sha(destination),'before':m,'after':verify,'streams':streams,'video_bytes_preserved':same,'scope':'Explicit final audio mastering after the retained native export; no changed speech rate, images, cuts or caption timing. Technical checks do not replace listening or user acceptance.'}
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),'utf-8')
    if not same or sha(source)!=before:raise RuntimeError('Mastering did not preserve the native source/video')
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(master(a.input,a.out),ensure_ascii=False))
