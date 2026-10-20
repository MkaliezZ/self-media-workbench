"""Offline content metrics. No network or third-party dependencies."""
import argparse
import json
import math
import statistics
from pathlib import Path

COUNTS = ('views', 'likes', 'comments', 'saves', 'shares', 'followers_gained',
          'profile_visits', 'three_sec_retained', 'completed_views', 'consultations')
RATES = {'like_rate': 'likes', 'comment_rate': 'comments', 'save_rate': 'saves',
         'share_rate': 'shares', 'follow_rate': 'followers_gained',
         'three_sec_retention': 'three_sec_retained', 'completion_rate': 'completed_views',
         'consultation_rate': 'consultations'}
PROVENANCE = {'synthetic', 'observed', 'user_provided', 'tool_estimate'}
# Detect common source-field mismatches; never assume platform meanings are equal.
SOURCE_ALIASES = {'plays': 'views', 'favorites': 'saves',
                  'new_followers': 'followers_gained', 'complete_plays': 'completed_views'}


def divide(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def summarize(data):
    if not isinstance(data, dict) or not isinstance(data.get('accounts'), list):
        raise ValueError('accounts must be a list')
    result = {'schema_version': 1, 'accounts': [], 'contains_synthetic': False,
              'notice': 'Computed observations only; no causal inference or platform benchmark.'}
    account_ids = set()
    for account in data['accounts']:
        aid = account.get('id')
        if not isinstance(aid, str) or not aid or aid in account_ids:
            raise ValueError('account id must be a unique nonempty string')
        account_ids.add(aid)
        if not isinstance(account.get('platform'), str) or not account['platform']:
            raise ValueError(f'{aid}: platform is required')
        if not isinstance(account.get('videos'), list):
            raise ValueError(f'{aid}: videos must be a list')
        out = {'id': aid, 'platform': account['platform'], 'videos': [], 'cohorts': []}
        seen = set()
        for video in account['videos']:
            vid = video.get('id')
            if not isinstance(vid, str) or not vid or vid in seen:
                raise ValueError(f'{aid}: duplicate or empty video id: {vid}')
            seen.add(vid)
            if not isinstance(video.get('cohort'), str) or not video['cohort']:
                raise ValueError(f'{aid}/{vid}: cohort is required')
            if video.get('role') not in ('baseline', 'candidate'):
                raise ValueError(f'{aid}/{vid}: role must be baseline or candidate')
            if video.get('provenance') not in PROVENANCE:
                raise ValueError(f'{aid}/{vid}: invalid provenance')
            for alias, canonical in SOURCE_ALIASES.items():
                if video.get(alias) is not None:
                    if video.get(canonical) is None:
                        raise ValueError(f'{aid}/{vid}: source field {alias} was not mapped to {canonical}; '
                                         'verify definitions and map explicitly before computing')
                    if video[canonical] != video[alias]:
                        raise ValueError(f'{aid}/{vid}: conflicting {alias} and {canonical}; verify source mapping')
            for field in COUNTS:
                value = video.get(field)
                if value is not None and (type(value) is not int or value < 0):
                    raise ValueError(f'{aid}/{vid}: {field} must be a nonnegative integer or null')
            for field in ('duration_s', 'snapshot_hours'):
                value = video.get(field)
                if value is not None and (type(value) not in (int, float)
                        or not math.isfinite(value) or value <= 0):
                    raise ValueError(f'{aid}/{vid}: {field} must be positive or null')
            row = dict(video)
            views = row.get('views')
            row['rates'] = {key: divide(row.get(field), views) for key, field in RATES.items()}
            known = [row.get(field) for field in ('likes', 'comments', 'saves', 'shares')]
            row['missing_interaction_fields'] = [field for field in ('likes', 'comments', 'saves', 'shares')
                                                 if row.get(field) is None]
            row['engagements_complete'] = sum(known) if all(x is not None for x in known) else None
            row['rates']['engagement_rate'] = divide(row['engagements_complete'], views)
            row['known_engagements_lower_bound'] = sum(x for x in known if x is not None)
            row['known_engagement_rate_lower_bound'] = divide(row['known_engagements_lower_bound'], views)
            row['warnings'] = []
            if views == 0 and any((row.get(f) or 0) > 0 for f in COUNTS if f != 'views'):
                row['warnings'].append('positive action count with zero views; inspect definitions')
            for field in ('three_sec_retained', 'completed_views'):
                if views is not None and row.get(field) is not None and row[field] > views:
                    raise ValueError(f'{aid}/{vid}: {field} exceeds views; incompatible count definition')
            if row['provenance'] == 'synthetic':
                result['contains_synthetic'] = True
            out['videos'].append(row)
        for cohort in sorted({v['cohort'] for v in out['videos']}):
            rows = [v for v in out['videos'] if v['cohort'] == cohort]
            baseline = [v for v in rows if v['role'] == 'baseline']
            provenance = sorted({v['provenance'] for v in rows})
            cohort_out = {'cohort': cohort, 'n_all': len(rows), 'n_baseline': len(baseline),
                          'provenance': provenance, 'statistics': {}}
            if len(provenance) > 1:
                cohort_out['warning'] = 'Mixed provenance; compare separately before interpreting.'
            for key in ('views', 'likes') + tuple(RATES) + ('engagement_rate',):
                values = [v.get(key) if key in ('views', 'likes') else v['rates'].get(key)
                          for v in baseline]
                values = [v for v in values if v is not None]
                cohort_out['statistics'][key] = {'n_valid': len(values),
                    'sorted': sorted(values), 'median': statistics.median(values) if values else None}
            # cohort membership is caller supplied, but mismatched snapshot age is explicitly flagged.
            windows = {v.get('snapshot_hours') for v in rows}
            blockers = []
            if None in windows:
                blockers.append('missing_observation_window')
            if len(windows) > 1:
                blockers.append('unequal_observation_windows')
            cohort_out['comparison_allowed'] = not blockers
            cohort_out['comparison_blockers'] = blockers
            if len(windows) > 1 or None in windows:
                cohort_out['window_warning'] = 'Observation windows missing or unequal; do not compare effects.'
            for video in rows:
                video['baseline_comparison_allowed'] = not blockers
                video['baseline_comparison_blockers'] = list(blockers)
                video['relative_to_baseline'] = {}
                for key, stats in cohort_out['statistics'].items():
                    value = video.get(key) if key in ('views', 'likes') else video['rates'].get(key)
                    video['relative_to_baseline'][key] = divide(value, stats['median']) if not blockers else None
            out['cohorts'].append(cohort_out)
        result['accounts'].append(out)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    try:
        result = summarize(json.loads(args.input.read_text(encoding='utf-8-sig')))
    except (ValueError, KeyError, TypeError) as exc:
        parser.exit(2, f'Invalid input: {exc}\n')
    text = json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + '\n', encoding='utf-8')
        print(f'Wrote {args.out}; contains_synthetic={result["contains_synthetic"]}')
    else:
        print(text)


if __name__ == '__main__':
    main()
