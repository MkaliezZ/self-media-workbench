"""Explicit pause and spoken-group decisions on the immutable source timeline."""
import math
import re


def corrected_text(original, replacement):
    """Keep ASR token whitespace when a correction supplies only display text."""
    leading = re.match(r'^\s*',original).group()
    trailing = re.search(r'\s*$',original).group()
    if leading and not replacement[0].isspace():replacement=leading+replacement
    if trailing and not replacement[-1].isspace():replacement+=trailing
    return replacement


def plan_keeps(review, selected_ids, speech_cuts=None):
    duration = float(review['duration'])
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('素材时长无效')
    candidates = {c['id']: c for c in review['candidates']}
    if len(candidates) != len(review['candidates']):
        raise ValueError('候选ID重复')
    unknown = set(selected_ids) - candidates.keys()
    if unknown:
        raise ValueError('未知候选：' + ','.join(sorted(unknown)))
    cuts = []
    decisions = []
    for cid in set(selected_ids):
        c = candidates[cid]
        a, b = float(c['start']), float(c['end'])
        if not all(map(math.isfinite, [a, b])) or not 0 <= a < b <= duration:
            raise ValueError('候选超出原片范围')
        for w in review['words']:
            if a < w['end'] and b > w['start']:
                raise ValueError('气口候选碰到语音词组，必须回听重新划定；不能自动截断词组')
        cuts.append({'start': a, 'end': b})
        decisions.append({'id':cid, 'kind':'pause', 'start':a, 'end':b})
    speech_cuts = review.get('speech_cuts', []) if speech_cuts is None else speech_cuts
    if not isinstance(speech_cuts, list):
        raise ValueError('有声删除须为列表')
    positions = {w.get('id'):i for i,w in enumerate(review['words'])}
    removed_ids, decision_ids = set(), set()
    for cut in speech_cuts:
        ids = cut.get('word_ids', [])
        cid = cut.get('id')
        if not isinstance(cid,str) or not cid.strip() or cid in decision_ids:
            raise ValueError('有声删除ID为空或重复')
        decision_ids.add(cid)
        if not isinstance(ids,list) or not ids or any(type(i) is not int or i not in positions for i in ids):
            raise ValueError('有声删除须指定现有ASR词组ID')
        if len(positions) != len(review['words']):
            raise ValueError('ASR词组ID缺失或重复')
        order = [positions[i] for i in ids]
        if order != list(range(order[0], order[0]+len(order))):
            raise ValueError('每个有声删除须按原顺序选择连续完整词组')
        if removed_ids.intersection(ids):
            raise ValueError('有声删除重复选择同一词组')
        if not isinstance(cut.get('reason'),str) or not cut['reason'].strip():
            raise ValueError('有声删除须说明实际理由')
        words = [review['words'][i] for i in order]
        group_start = min(w['start'] for w in words)
        group_end = max(w['end'] for w in words)
        a = group_start if cut.get('start') is None else float(cut['start'])
        b = group_end if cut.get('end') is None else float(cut['end'])
        if not all(map(math.isfinite,[a,b])) or not 0 <= a < b <= duration:
            raise ValueError('有声删除超出原片范围')
        if a > group_start+1e-7 or b < group_end-1e-7:
            raise ValueError('有声删除不能截断选定ASR词组，不伪造逐字切点')
        for w in review['words']:
            if w['id'] not in ids and a < w['end']-1e-7 and b > w['start']+1e-7:
                raise ValueError('有声删除碰到未选择词组，须重新核对范围')
        removed_ids.update(ids)
        cuts.append({'start':a,'end':b})
        decisions.append({'id':cid,'kind':cut.get('kind','other'),'start':a,'end':b,
                          'word_ids':ids,'review_text':''.join(w['text'] for w in words),
                          'reason':cut['reason'],'alignment':'model_word_group'})
    cuts.sort(key=lambda s: s['start'])
    merged = []
    for cut in cuts:
        if merged and cut['start'] <= merged[-1]['end']:
            merged[-1]['end'] = max(merged[-1]['end'], cut['end'])
        else:
            merged.append(dict(cut))
    keeps, cursor, output_offset = [], 0., 0.
    for cut in merged:
        if cut['start'] > cursor:
            keeps.append({'start': cursor, 'end': cut['start'], 'outputOffset': output_offset})
            output_offset += cut['start'] - cursor
        cursor = cut['end']
    if cursor < duration:
        keeps.append({'start': cursor, 'end': duration, 'outputOffset': output_offset})
    if not keeps:
        raise ValueError('整片被删除，不能导出')
    return {'duration': duration, 'cuts': merged, 'keeps': keeps,
            'output_duration': sum(k['end']-k['start'] for k in keeps),
            'selected_ids': sorted(set(selected_ids)),
            'deleted_word_ids':sorted(removed_ids), 'decisions':decisions,
            'policy': 'Only explicit selected pauses/spoken groups; no hidden silence cutting or boundary snapping.'}
