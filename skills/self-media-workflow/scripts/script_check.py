"""Count the exact spoken text and estimate segment timing; never a recording test."""
import argparse
import json
import math
import re
from pathlib import Path


def markdown_segments(text):
    columns=None
    rows=[]
    for line in text.splitlines():
        if not line.strip().startswith('|'):
            if rows:break
            continue
        cells=[c.strip() for c in line.strip().strip('|').split('|')]
        spoken=[i for i,c in enumerate(cells) if re.search(r'逐字口播|口播词|逐字稿',c)]
        times=[i for i,c in enumerate(cells) if '时间' in c]
        if spoken and times:
            if rows:break
            columns=(times[0],spoken[0])
            continue
        if columns is None or len(cells)<=max(columns):continue
        match=re.fullmatch(r'\s*(\d+(?:\.\d+)?)\s*[—–~～-]\s*(\d+(?:\.\d+)?)\s*(?:s|秒)?\s*',cells[columns[0]])
        if match:
            rows.append({'start':float(match.group(1)),'end':float(match.group(2)),
                         'spoken':cells[columns[1]],'pause_s':0})
        elif rows:
            break
    if not rows:raise ValueError('No spoken timeline table found; use JSON segments instead.')
    return rows


def check(segments,slow=240,fast=300,claimed_total=None):
    if not segments:raise ValueError('segments must not be empty')
    if slow<=0 or fast<slow:raise ValueError('invalid speech rate range')
    rows=[];previous=0
    for segment in segments:
        start=float(segment['start']);end=float(segment['end'])
        if not math.isfinite(start) or not math.isfinite(end):raise ValueError('timeline must be finite')
        if start!=previous or end<=start:raise ValueError('timeline gap, overlap, or nonpositive duration')
        previous=end
        spoken=segment['spoken']
        if not isinstance(spoken,str) or not spoken.strip():raise ValueError('spoken text is empty')
        pause=float(segment.get('pause_s',0))
        if not math.isfinite(pause) or pause<0:raise ValueError('pause_s must be finite and nonnegative')
        # Count visible Chinese characters and alphanumerics; do not pretend this expands numbers/English pronunciation.
        count=len(re.findall(r'[\u4e00-\u9fffA-Za-z0-9]',spoken))
        fast_s=count/fast*60+pause;slow_s=count/slow*60+pause
        rows.append({'start':start,'end':end,'spoken':spoken,'counted_characters':count,
            'pause_s':pause,'estimate_fast_s':round(fast_s,4),'estimate_slow_s':round(slow_s,4),
            'fits_slow_estimate':slow_s<=end-start})
    total=sum(r['counted_characters'] for r in rows)
    return {'verification_level':'text_estimate_not_recording',
        'count_definition':'Chinese characters + alphanumerics, excludes punctuation; numeric/English pronunciation requires review',
        'assumed_characters_per_minute':[slow,fast],'segments':rows,'total_counted_characters':total,
        'claimed_total':claimed_total,'claimed_total_matches':None if claimed_total is None else claimed_total==total,
        'estimate_fast_s':round(sum(r['estimate_fast_s'] for r in rows),4),
        'estimate_slow_s':round(sum(r['estimate_slow_s'] for r in rows),4),
        'timeline_seconds':previous,'all_segments_fit_slow_estimate':all(r['fits_slow_estimate'] for r in rows),
        'human_read_aloud':'not_performed'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input',type=Path)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--claimed-total',type=int)
    args=parser.parse_args()
    try:
        text=args.input.read_text(encoding='utf-8-sig')
        segments=json.loads(text)['segments'] if args.input.suffix=='.json' else markdown_segments(text)
        result=check(segments,claimed_total=args.claimed_total)
    except (ValueError,KeyError,TypeError) as exc:
        parser.exit(2,f'Invalid input: {exc}\n')
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Count={result["total_counted_characters"]}; claimed_match={result["claimed_total_matches"]}; recording=not_performed')
    if result['claimed_total_matches'] is False:parser.exit(1,'Claimed spoken count does not match exact script.\n')


if __name__=='__main__':main()
