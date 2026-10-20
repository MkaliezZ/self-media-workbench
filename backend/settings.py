"""Portable, process-local settings. No user paths or model downloads in source."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def user_state():
    if os.name == 'nt':
        return Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData/Local')) / 'SelfMediaWorkbench'
    if sys.platform == 'darwin':
        return Path.home() / 'Library/Application Support/SelfMediaWorkbench'
    return Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local/state')) / 'self-media-workbench'


STATE = Path(os.environ.get('SELF_MEDIA_STATE_DIR', str(user_state()))).expanduser().resolve()
CONFIG_FILE = STATE / 'config.json'
CONFIG = json.loads(CONFIG_FILE.read_text('utf-8')) if CONFIG_FILE.is_file() else {}


def setting(env, key, default):
    return os.environ.get(env, CONFIG.get(key, str(default)))


DATA = Path(setting('SELF_MEDIA_DATA_DIR', 'data_dir', STATE / 'projects')).expanduser().resolve()
SKILL = Path(setting('SELF_MEDIA_SKILL_ROOT', 'skill_root', ROOT / 'skills/self-media-workflow')).expanduser().resolve()
MODEL = Path(setting('SELF_MEDIA_MODEL', 'model', STATE / 'models/faster-whisper-medium')).expanduser().resolve()
MLX_MODEL = Path(setting('SELF_MEDIA_MLX_MODEL', 'mlx_model', STATE / 'models/mlx-whisper-medium')).expanduser().resolve()
ASR_BACKEND = setting('SELF_MEDIA_ASR_BACKEND', 'asr_backend', 'auto')
CPP_EXECUTABLE = Path(setting('SELF_MEDIA_CPP_EXECUTABLE', 'cpp_executable', STATE / 'runtime/whisper-cli')).expanduser().resolve()
CPP_MODEL = Path(setting('SELF_MEDIA_CPP_MODEL', 'cpp_model', STATE / 'models/ggml-medium.bin')).expanduser().resolve()
CPP_GPU_INDEX = int(setting('SELF_MEDIA_CPP_GPU_INDEX', 'cpp_gpu_index', 0))
REQUIRE_GPU = str(setting('SELF_MEDIA_REQUIRE_GPU', 'require_gpu', False)).lower() in ('true','1','yes')
library = setting('SELF_MEDIA_LIBRARY', 'library', '')
LIBRARY = Path(library).expanduser().resolve() if library else None
DEVICE = setting('SELF_MEDIA_DEVICE', 'device', 'auto')
LANGUAGE = setting('SELF_MEDIA_LANGUAGE', 'language', 'zh')
