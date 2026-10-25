"""Independent predeclared travel task, native Windows/macOS execution.

The calling Agent manages this entry; people need not install/start a service.
No model, ASR, paid resource, product fixture or expected sample video is used.
Outputs must be a new directory, so failures/first exports cannot be overwritten.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
import time
import traceback
import urllib.error
import urllib.request
import uuid

REPO = Path(__file__).resolve().parents[1]
CASE = REPO / 'evaluation' / 'independent_travel'


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prerequisites(output):
    missing = []
    for name in ('PIL', 'numpy', 'fastapi', 'uvicorn', 'pydantic'):
        try:
            __import__(name)
        except ImportError:
            missing.append(name)
    if missing:
        command = [sys.executable, '-m', 'pip', 'install', '-r', str(REPO / 'requirements.txt'), 'Pillow>=10,<13']
        done = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        write(output / 'dependency-install.json', {'command': command, 'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr})
        done.check_returncode()
    if not all(shutil.which(x) for x in ('ffmpeg', 'ffprobe')):
        if sys.platform == 'darwin' and shutil.which('brew'):
            done = subprocess.run(['brew', 'install', 'ffmpeg'], capture_output=True, text=True, encoding='utf-8', errors='replace')
            write(output / 'ffmpeg-install.json', {'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr})
            done.check_returncode()
        else:
            raise RuntimeError('Agent must provision FFmpeg/ffprobe on this host; no platform emulation is accepted')


def load_generator(output):
    spec = importlib.util.spec_from_file_location('independent_travel_generator', CASE / 'generate_materials.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = output
    module.OUT = output / 'materials'
    module.OUT.mkdir(exist_ok=True)
    # Platform font choice is explicit provenance; manifests seal actual host files.
    for path in ('C:/Windows/Fonts/arial.ttf', '/System/Library/Fonts/Supplemental/Arial.ttf', '/Library/Fonts/Arial.ttf'):
        if Path(path).exists():
            module.FONT_PATH = Path(path)
            break
    module.main()


class Run:
    def __init__(self, output):
        self.output = output
        self.env = {**os.environ, 'SELF_MEDIA_STATE_DIR': str(output / 'state'), 'SELF_MEDIA_DATA_DIR': str(output / 'data'), 'PYTHONUTF8': '1'}
        self.base = None
        self.pid = None

    def cli(self, name, args):
        path = self.output / (name + '.json')
        command = [sys.executable, str(REPO / 'workbench.py'), '--out', str(path), *args]
        done = subprocess.run(command, cwd=REPO, env=self.env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=180)
        write(self.output / (name + '-process.json'), {'command': command, 'returncode': done.returncode, 'stdout': done.stdout, 'stderr': done.stderr})
        done.check_returncode()
        return read(path)

    def request(self, name, method, path, body=None, expected=200):
        raw = None if body is None else json.dumps(body).encode('utf-8')
        req = urllib.request.Request(self.base + path, data=raw, method=method, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=120) as res:
                status, data = res.status, json.load(res)
        except urllib.error.HTTPError as error:
            status, data = error.code, json.loads(error.read())
        write(self.output / (name + '.json'), {'request': {'method': method, 'path': path, 'body': body}, 'status': status, 'response': data})
        if status != expected:
            raise RuntimeError(f'{name}: expected HTTP {expected}, got {status}: {data}')
        return data

    def context(self, name):
        return self.request(name, 'GET', f'/api/agent/v1/projects/{self.pid}/context')

    def save(self, name, body):
        ctx = self.context(name + '-context')
        body = copy.deepcopy(body)
        body.update(request_id='independent-' + uuid.uuid4().hex, project_revision=ctx['project']['revision'], supersedes=ctx['project'].get('timeline_head'))
        write(self.output / (name + '-request.json'), body)
        return self.request(name + '-save', 'POST', f'/api/projects/{self.pid}/timeline-plans', body)

    def export(self, name, plan):
        job = self.request(name + '-submit', 'POST', f'/api/projects/{self.pid}/timeline/export', {'plan_id': plan['id']})
        for i in range(180):
            job = self.request(f'{name}-poll-{i:03}', 'GET', f'/api/projects/{self.pid}/jobs/{job["id"]}')
            if job['status'] in ('done', 'failed', 'error'):
                write(self.output / (name + '-terminal.json'), job)
                if job['status'] != 'done':
                    raise RuntimeError(f'{name} failed: {job}')
                dest = self.output / 'data' / self.pid / 'exports' / job['result']['export_id']
                video = dest / 'timeline.mp4'
                # Real full decoding, independent of API success.
                decoded = subprocess.run(['ffmpeg', '-v', 'error', '-i', str(video), '-f', 'null', '-'], capture_output=True, text=True)
                write(self.output / (name + '-decode.json'), {'returncode': decoded.returncode, 'stderr': decoded.stderr})
                decoded.check_returncode()
                variant = name.replace('-export', '')
                checked = subprocess.run([sys.executable, str(CASE / 'verify_output.py'), str(video), '--materials-root', str(self.output), '--variant', variant], capture_output=True, text=True, encoding='utf-8', errors='replace')
                write(self.output / (name + '-independent-process.json'), {'returncode': checked.returncode, 'stdout': checked.stdout, 'stderr': checked.stderr})
                checked.check_returncode()
                result = read(dest / 'timeline_independent_v2_evidence' / 'result.json')
                if not result['automated_checks_pass']:
                    raise RuntimeError(f'{name}: decoded media did not satisfy predeclared task')
                return video, result
            time.sleep(1)
        raise TimeoutError(name)

    def execute(self):
        inputs = sorted((self.output / 'materials').glob('*.mp4')) + [self.output / 'materials' / 'journey_original_120bpm.wav']
        original_hashes = {p.name: sha(p) for p in inputs}
        args = ['run', 'Create the predeclared 16-second silent/multi-source illustrated travel edit with original music; preserve the quiet direction board; no ASR or narration', '--intent', 'edit', '--new', '--title', 'Independent illustrated travel acceptance', '--simulation', '--media-nature', 'generated', '--source-note', 'Original programmatic animation and original synthesized music; not real travel footage', '--usage-scope', 'Independent local technical acceptance; no publication', '--session', 'independent-travel-' + uuid.uuid4().hex]
        for item in inputs:
            args.extend(['--input', str(item)])
        intake = self.cli('intake', args)
        self.base, self.pid = intake['service_url'], intake['project_id']
        self.cli('capabilities', ['call', 'GET', '/api/agent/v1/capabilities'])
        for schema in ('timeline-plan', 'timeline-export', 'music-onsets'):
            self.cli('schema-' + schema, ['schema', schema])
        self.request('logics', 'GET', '/api/visual/logics')
        ctx = self.context('initial-context')
        sources = [{'id': m['name'][0] if m['name'].endswith('.mp4') else 'music', 'kind': 'media', 'asset_id': m['id'], 'sha256': m['sha256']} for m in ctx['project']['media']]
        assert all(m['sha256'] == original_hashes[m['name']] for m in ctx['project']['media'])
        music = next(s for s in sources if s['id'] == 'music')
        self.request('music-onsets', 'POST', f'/api/projects/{self.pid}/music-onsets', {'media_id': music['asset_id'], 'source_sha256': music['sha256'], 'source_in': 0, 'source_out': 16})
        shots = [{'id': sid.lower(), 'source_id': sid, 'source_in': a, 'source_out': b, 'role': role, 'reason': 'Predeclared independent story interval; preserve meaningful silent action', 'fit': 'contain', 'source_audio_gain': .25 if sid in 'AC' else 0} for sid, a, b, role in [('A', 1.25, 4.25, 'arrival'), ('B', 2, 6, 'direction'), ('C', 1, 6, 'summit'), ('D', .5, 4.5, 'return')]]
        baseline = {'request_id': 'independent-first', 'project_revision': ctx['project']['revision'], 'supersedes': None, 'revision_reason': 'First independent predeclared plan', 'intent': 'Four-scene illustrated travel journey, no narration/ASR', 'width': 1280, 'height': 720, 'fps': 30, 'sources': sources, 'shots': shots, 'audio': [{'source_id': 'music', 'role': 'music', 'source_in': 0, 'start': 0, 'duration': 16, 'gain': .65, 'fade_in': 0, 'fade_out': .25, 'reason': 'Original continuous 120 BPM music clock'}], 'music_grid': {'source_id': 'music', 'source_times': [0, 3, 7, 12, 16], 'method': 'manual', 'reason': 'Independent original 0.5-second beat table and reviewed narrative edges', 'max_error_frames': 1}, 'titles': []}
        aligned = self.request('baseline-align', 'POST', f'/api/projects/{self.pid}/timeline/align', baseline)
        assert aligned['map']['frames'] == 480
        first = self.save('baseline', baseline)
        first_video, first_result = self.export('baseline-export', first)
        first_hash = sha(first_video)
        cut = copy.deepcopy(baseline)
        left, right = copy.deepcopy(shots[1]), copy.deepcopy(shots[1])
        left.update(id='b-left', source_out=4)
        right.update(id='b-right', source_in=5)
        cut['shots'] = [shots[0], left, right, *shots[2:]]
        cut['audio'][0]['duration'] = 15
        cut['music_grid']['source_times'] = [0, 3, 5, 6, 11, 15]
        cut['revision_reason'] = 'Remove B source 4-5 seconds, preserving both sides and continuous independent music'
        cut_plan = self.save('cut', cut)
        cut_video, cut_result = self.export('cut-export', cut_plan)
        restored = copy.deepcopy(baseline)
        restored['revision_reason'] = 'Restore original B source 4-5 seconds after reviewing quiet direction board'
        restored_plan = self.save('restored', restored)
        restored_video, restored_result = self.export('restored-export', restored_plan)
        stale = copy.deepcopy(first['request'])
        stale['request_id'] = 'independent-stale-' + uuid.uuid4().hex
        self.request('stale-save-rejected', 'POST', f'/api/projects/{self.pid}/timeline-plans', stale, expected=409)
        ctx = self.context('negative-context')
        for name in ('unknown-source', 'out-of-bounds', 'bad-grid'):
            bad = copy.deepcopy(restored_plan['request'])
            bad.update(request_id='independent-' + uuid.uuid4().hex, project_revision=ctx['project']['revision'], supersedes=ctx['project']['timeline_head'])
            if name == 'unknown-source':
                bad['shots'][0]['source_id'] = 'unregistered'
            elif name == 'out-of-bounds':
                bad['shots'][0]['source_out'] = 999
            else:
                bad['music_grid']['source_times'][-1] = 17
            self.request(name + '-rejected', 'POST', f'/api/projects/{self.pid}/timeline-plans', bad, expected=422)
        final = self.context('final-context')
        assert final['project']['timeline_head'] == restored_plan['id']
        assert len(final['timeline_plans']) == 3
        assert all(sha(p) == original_hashes[p.name] for p in inputs)
        assert sha(first_video) == first_hash
        assert sha(restored_video) == first_hash
        summary = {'status': 'decoded_media_checks_passed', 'platform': platform.platform(), 'machine': platform.machine(), 'python': sys.version, 'product_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip(), 'original_sha256': original_hashes, 'baseline_video': str(first_video), 'cut_video': str(cut_video), 'restored_video': str(restored_video), 'baseline_sha256': first_hash, 'restored_sha256': sha(restored_video), 'restored_byte_identical': True, 'plan_ids': [first['id'], cut_plan['id'], restored_plan['id']], 'actual_durations': [first_result['actual_duration'], cut_result['actual_duration'], restored_result['actual_duration']], 'music_correlations': [r['music']['normalized_correlation'] for r in (first_result, cut_result, restored_result)], 'limits': ['Synthetic illustrated travel technical acceptance; not real footage or general creative quality', 'Decoded audio timing/mix evidence does not constitute human aesthetic listening', 'This execution only proves the reported native host, not another OS or architecture']}
        write(self.output / 'summary.json', summary)
        print(json.dumps(summary, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--materials', type=Path, help='Optional independently presealed materials directory; otherwise generate original scene animations')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    (output / 'evidence').mkdir()
    shutil.copyfile(CASE / 'BLIND_TASK.md', output / 'BLIND_TASK.md')
    try:
        prerequisites(output)
        if args.materials:
            shutil.copytree(args.materials.resolve(), output / 'materials')
        else:
            load_generator(output)
        write(output / 'input-seal.json', {str(p.relative_to(output)): sha(p) for p in (output / 'materials').glob('*') if p.is_file()})
        Run(output).execute()
    except Exception:
        write(output / 'failure.json', {'platform': platform.platform(), 'machine': platform.machine(), 'traceback': traceback.format_exc(), 'preserved_first_attempt': True})
        raise


if __name__ == '__main__':
    main()
