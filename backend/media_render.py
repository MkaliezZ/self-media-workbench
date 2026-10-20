"""MIT. Render explicit keep intervals using FFmpeg; no external renderer code.

Timing contract: every retained ASR group must be fully inside one keep interval.
Subtitles and word JSON are projected through the same piecewise translation.
This module does no inference, silence detection, or implicit cutting.
"""
import json
import math
import subprocess
from pathlib import Path


def project_words(review, keeps):
    windows = []
    offset = 0.0
    for keep in keeps:
        a, b = float(keep['start']), float(keep['end'])
        if not math.isfinite(a + b) or not 0 <= a < b:
            raise ValueError('Invalid keep interval')
        if windows and a < windows[-1][1]:
            raise ValueError('Keep intervals overlap or are out of source order')
        windows.append((a, b, offset))
        offset += b - a
    mapped = []
    for word in review['words']:
        a, b = float(word['start']), float(word['end'])
        overlaps = [(lo, hi, dest) for lo, hi, dest in windows if a < hi and b > lo]
        if not overlaps:
            continue
        if len(overlaps) != 1 or a < overlaps[0][0] - 1e-6 or b > overlaps[0][1] + 1e-6:
            raise ValueError('A keep boundary clips a spoken group; review the explicit cuts')
        lo, _, dest = overlaps[0]
        mapped.append({'id':word['id'], 'text':word['text'],
                       'source_start':a,'source_end':b,
                       'asr_probability':word.get('probability'),
                       'start':round(dest + a - lo, 6), 'end':round(dest + b - lo, 6)})
    return mapped


def captions(review, mapped):
    groups = review.get('caption_groups')
    if groups:
        if any(not group for group in groups) or [i for group in groups for i in group] != [w['id'] for w in mapped]:
            raise ValueError('Caption groups must cover all retained words in order')
    else:
        # A conservative candidate, not a guarantee of semantic segmentation.
        groups, current = [], []
        previous = None
        chars = 0
        for word in mapped:
            if current and (word['start'] - previous['end'] > .6 or chars >= 24 or
                            previous['text'].rstrip().endswith(('。', '！', '？', '.', '!', '?', ';', '；'))):
                groups.append(current)
                current, chars = [], 0
            current.append(word['id'])
            chars += len(word['text'])
            previous = word
        if current:
            groups.append(current)
    by_id = {w['id']:w for w in mapped}
    return [{'text':''.join(by_id[i]['text'] for i in group),
             'start':by_id[group[0]]['start'], 'end':by_id[group[-1]]['end']} for group in groups]


def stamp(value):
    milliseconds = round(value * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f'{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}'


def render(source, review, plan, destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    mapped = project_words(review, plan['keeps'])
    cues = captions(review, mapped)
    video = destination / 'reviewed_cut.mp4'
    if video.exists():
        raise ValueError('An export destination is immutable; create a new export')
    filters, labels = [], []
    for index, keep in enumerate(plan['keeps']):
        bounds = f"start={keep['start']:.6f}:end={keep['end']:.6f}"
        filters.extend([f'[0:v:0]trim={bounds},setpts=PTS-STARTPTS[v{index}]',
                        f'[0:a:0]atrim={bounds},asetpts=PTS-STARTPTS[a{index}]'])
        labels.append(f'[v{index}][a{index}]')
    filters.append(''.join(labels) + f"concat=n={len(labels)}:v=1:a=1[vout][aout]")
    command = ['ffmpeg', '-hide_banner', '-v', 'error', '-nostdin', '-n', '-i', str(source),
               '-filter_complex', ';'.join(filters), '-map', '[vout]', '-map', '[aout]',
               '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p',
               '-c:a', 'aac', '-movflags', '+faststart', str(video)]
    result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
    (destination / 'render-process.json').write_text(json.dumps(
        {'command':command, 'returncode':result.returncode, 'stderr':result.stderr}, ensure_ascii=False, indent=2), encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stderr[-3000:])
    srt = '\n\n'.join(f"{n}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for n,c in enumerate(cues, 1))
    (destination / 'reviewed_cut.srt').write_text(srt + '\n', encoding='utf-8')
    (destination / 'reviewed_cut.words.json').write_text(json.dumps(
        mapped, ensure_ascii=False, indent=2), encoding='utf-8')
    (destination / 'edit-decision.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'words':len(mapped), 'captions':len(cues), 'output':str(video)}
