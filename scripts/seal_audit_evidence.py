"""Verify driver-owned evidence, then hash the closed workflow artifact envelope."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def write(root,name,value):
    (root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    root=parser.parse_args().out.resolve()
    root.mkdir(parents=True,exist_ok=True)
    report={'passed':False,'mismatches':[]}
    try:
        rows=json.loads((root/'evidence-manifest.json').read_text('utf-8'))
        for row in rows:
            path=(root/row['path']).resolve()
            if not path.is_relative_to(root) or not path.is_file():
                report['mismatches'].append({'path':row['path'],'error':'missing or outside evidence root'})
            elif path.stat().st_size!=row['bytes'] or digest(path)!=row['sha256']:
                report['mismatches'].append({'path':row['path'],'error':'hash or size changed after driver manifest'})
        result=json.loads((root/'final-result.json').read_text('utf-8'))
        report.update(entries=len(rows),runtime_passed=result.get('passed') is True,
                      passed=bool(rows) and not report['mismatches'] and result.get('passed') is True)
    except (OSError,ValueError,KeyError,TypeError) as exc:
        report['error']=str(exc)
    write(root,'artifact-verification.json',report)
    excluded={'hf-home','pip-cache','foreign-python','.git','.venv'}
    files=[]
    for path in sorted(root.rglob('*')):
        relative=path.relative_to(root)
        if (not path.is_file() or any(p in excluded for p in relative.parts)
                or path.name=='artifact-manifest.json' or path.name in {'model.bin','weights.npz'}
                or path.suffix in {'.safetensors','.whl'}):
            continue
        files.append({'path':relative.as_posix(),'bytes':path.stat().st_size,'sha256':digest(path)})
    write(root,'artifact-manifest.json',files)
    print(json.dumps(report,ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
