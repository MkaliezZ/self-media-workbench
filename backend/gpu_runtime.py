"""Find trusted NVIDIA wheel DLLs for this process, without global PATH changes."""
import os
import sys
import threading
from pathlib import Path

_LOCK = threading.Lock()
_HANDLES = {}  # Keep AddDllDirectory cookies alive for delayed CUDA loads.


def configure_cuda_dlls():
    if os.name != 'nt':
        return []
    root = Path(__file__).resolve().parents[1]
    package_roots = [root / 'runtime/cuda12/nvidia',
                     Path(sys.prefix) / 'Lib/site-packages/nvidia']
    from settings import CONFIG
    explicit = os.environ.get('SELF_MEDIA_CUDA_DLL_DIRS')
    configured = explicit.split(os.pathsep) if explicit is not None else CONFIG.get('cuda_dll_dirs',[])
    with _LOCK:
        directories = []
        candidates = [Path(p).expanduser() for p in configured if p]
        for packages in package_roots:
            if not packages.is_dir():
                continue
            candidates.extend(sorted(packages.glob('*/bin')))
        for directory in candidates:
            if not any(directory.glob('*.dll')):
                continue
            value = str(directory.resolve())
            directories.append(value)
            if value not in _HANDLES:
                _HANDLES[value] = os.add_dll_directory(value)
        # CTranslate2 also loads libraries with native LoadLibrary. The change
        # is process-local and inherited only by children of this workbench.
        current = os.environ.get('PATH', '').split(os.pathsep)
        additions = [p for p in directories if p.casefold() not in
                     {q.casefold() for q in current}]
        if additions:
            os.environ['PATH'] = os.pathsep.join(additions + current)
        return directories
