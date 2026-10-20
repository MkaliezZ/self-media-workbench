"""Record native Intel Mac hardware/Metal prerequisites, without a CPU stand-in."""
import argparse
import hashlib
import json
import platform
import subprocess
import sys
import traceback
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[1]
    commands = []

    def run(label, command):
        proc = subprocess.run(command, capture_output=True, timeout=180)
        (out / (label + '.stdout.txt')).write_bytes(proc.stdout)
        (out / (label + '.stderr.txt')).write_bytes(proc.stderr)
        commands.append({'label': label, 'command': command, 'exit_code': proc.returncode})
        return proc

    result = {'platform': sys.platform, 'machine': platform.machine(), 'asr_tested': False,
              'status': 'environment_unavailable', 'metal_compute_available': False}
    try:
        result['commit'] = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
        result['probe_sources_sha256'] = {name: hashlib.sha256((root / 'scripts' / name).read_bytes()).hexdigest()
                                          for name in ['metal_probe.swift', 'probe_macos_metal.py']}
        if sys.platform != 'darwin':
            raise RuntimeError('Requires an actual macOS host')
        for label, command in [
            ('os', ['sw_vers']),
            ('cpu', ['sysctl', '-n', 'machdep.cpu.brand_string']),
            ('translated', ['sysctl', '-in', 'sysctl.proc_translated']),
            ('displays', ['system_profiler', 'SPDisplaysDataType', '-json']),
        ]:
            run(label, command)
        compiled = run('compile', ['xcrun', 'swiftc', str(root / 'scripts/metal_probe.swift'),
                                  '-framework', 'Metal', '-o', str(out / 'metal-probe')])
        if compiled.returncode:
            raise RuntimeError('Native Metal probe did not compile; see retained diagnostics')
        result['probe_binary_sha256'] = hashlib.sha256((out / 'metal-probe').read_bytes()).hexdigest()
        executed = run('metal', [str(out / 'metal-probe')])
        if executed.returncode:
            raise RuntimeError('Native Metal probe process failed')
        native = json.loads(executed.stdout)
        result['native'] = native
        result['metal_compute_available'] = native['metal_compute_available']
        translated = (out / 'translated.stdout.txt').read_text().strip() == '1'
        result['native_intel'] = platform.machine() == 'x86_64' and not translated
        if native['metal_compute_available'] and result['native_intel']:
            result['status'] = 'ready_for_actual_asr'
        else:
            result['reason'] = 'No verified native Intel Metal compute device; ASR not run'
    except Exception as exc:
        result.update(error=str(exc), traceback=traceback.format_exc())
    (out / 'commands.json').write_text(json.dumps(commands, indent=2), encoding='utf8')
    result['manifest_scope'] = 'All retained artifact files except manifest.json; compiled probe binary excluded, its SHA256 recorded here'
    (out / 'result.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    rows = [{'path': f.relative_to(out).as_posix(), 'bytes': f.stat().st_size,
             'sha256': hashlib.sha256(f.read_bytes()).hexdigest()}
            for f in sorted(out.rglob('*')) if f.is_file() and f.name != 'metal-probe']
    (out / 'manifest.json').write_text(json.dumps(rows, indent=2), encoding='utf8')
    print(json.dumps(result))
    # An unavailable device is a recorded prerequisite result, never ASR success.
    return 1 if 'error' in result else 0


if __name__ == '__main__':
    raise SystemExit(main())
