"""Local faster-whisper transcription. No model or media upload/download.

Word groups retain the aligner's actual bounds. This module never invents
character-level alignment and never deletes spoken words automatically.
"""
import argparse
import hashlib
import json
import subprocess
import time
import os
import sys
from pathlib import Path

import numpy as np

from settings import MODEL as DEFAULT_MODEL, MLX_MODEL, ASR_BACKEND, DEVICE, LANGUAGE
from asr_backends import infer


def write_json(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def transcribe(source, output, model_path=DEFAULT_MODEL, device=DEVICE, language=LANGUAGE,
               backend=ASR_BACKEND, mlx_model=MLX_MODEL):
    source, output = Path(source).resolve(), Path(output).resolve()
    if (output / 'transcript.original.json').exists():
        raise ValueError('该输出目录已有原始转录；请使用新目录，保留旧识别与人工修订')
    if not source.is_file():
        raise ValueError('素材文件不存在')
    from faster_whisper.vad import VadOptions, get_speech_timestamps

    output.mkdir(parents=True, exist_ok=True)
    started = time.time()
    # 16 kHz mono PCM is shared by ASR and VAD, keeping one source timeline.
    proc = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(source), '-vn',
                           '-ac', '1', '-ar', '16000', '-f', 'f32le', '-'],
                          check=True, capture_output=True)
    audio = np.frombuffer(proc.stdout, dtype=np.float32).copy()
    audio_duration = len(audio) / 16000
    metadata = json.loads(subprocess.check_output(['ffprobe', '-v', 'error',
                           '-show_format', '-show_streams', '-of', 'json', str(source)]))
    # Video may continue after the audio ends. Restore-all must retain that tail.
    duration = max(audio_duration, float(metadata.get('format', {}).get('duration', 0)))
    inference = infer(audio, model_path, mlx_model, backend, device, language)
    words = []
    for word in inference['words']:
        start, end = max(0.0, float(word['start'])), min(duration, float(word['end']))
        if end > start:
            words.append({'id':len(words),'text':word['word'],'start':start,'end':end,
                          'probability':word.get('probability'),'alignment':'model_word_group'})
    speech = get_speech_timestamps(audio, VadOptions(min_silence_duration_ms=200,
                                                    speech_pad_ms=100))
    speech = [{'start': s['start'] / 16000, 'end': s['end'] / 16000} for s in speech]
    # VAD non-speech is only a candidate. Exclude padded ASR groups as a second
    # guard; breath, dramatic silence and nonverbal sound still need listening.
    gaps, cursor = [], 0.0
    for seg in speech:
        if seg['start'] > cursor:
            gaps.append((cursor, seg['start']))
        cursor = max(cursor, seg['end'])
    if cursor < duration:
        gaps.append((cursor, duration))
    for w in words:
        protected_start, protected_end = max(0, w['start']-.12), min(duration, w['end']+.12)
        split = []
        for a, b in gaps:
            if b <= protected_start or a >= protected_end:
                split.append((a, b))
            else:
                if a < protected_start:
                    split.append((a, protected_start))
                if b > protected_end:
                    split.append((protected_end, b))
        gaps = split
    candidates = []
    for a, b in gaps:
        # Retain .15s at each end of an internal gap, .15s near speech at edges.
        start = a if a == 0 else a + .15
        end = b if b == duration else b - .15
        if end-start >= .35:
            candidates.append({'id': 'pause-' + str(len(candidates)),
                               'start': max(0, round(start, 4)), 'end': min(duration, round(end, 4)),
                               'reason': 'VAD非语音，且避开ASR词组及边缘；需要回听',
                               'selected': False, 'kind': 'pause_candidate'})
    with source.open('rb') as stream:
        source_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
    result = {'source': str(source), 'source_sha256': source_hash,
              'model':inference['model'],'device':inference['device'],'backend':inference['backend'],
              'requested_backend':backend,'requested_device':device,'execution':inference['execution'],
              'fallback_errors':inference['fallback_errors'],'duration':duration,'audio_duration':audio_duration,
              'cuda_dll_dirs':inference.get('cuda_dll_dirs',[]),
              'language':inference['language'],'elapsed_seconds':time.time()-started,
              'text': ''.join(w['text'] for w in words), 'words': words,
              'vad_speech': speech, 'candidates': candidates,
              'limits': ['ASR识别和对齐可能有误，需要回听', '不自动判断口误或删除任何短句',
                         '非语音不等于可删气口；默认全部保留', '修改文字不会改变原词组时间戳']}
    write_json(output / 'transcript.original.json', result)
    write_json(output / 'review.json', result)
    return result


if __name__ == '__main__':
    cli = argparse.ArgumentParser()
    cli.add_argument('source', type=Path)
    cli.add_argument('output', type=Path)
    cli.add_argument('--model', type=Path, default=DEFAULT_MODEL)
    cli.add_argument('--device', choices=['auto','cuda','cpu','gpu'], default=DEVICE)
    cli.add_argument('--backend',choices=['auto','faster-whisper','mlx'],default=ASR_BACKEND)
    cli.add_argument('--mlx-model',type=Path,default=MLX_MODEL)
    args = cli.parse_args()
    result = transcribe(args.source, args.output, args.model, args.device,backend=args.backend,mlx_model=args.mlx_model)
    print(json.dumps({k: result[k] for k in ['device', 'duration', 'elapsed_seconds', 'text', 'candidates', 'fallback_errors']}, ensure_ascii=False, indent=2))
