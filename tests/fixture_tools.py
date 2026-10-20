"""Public synthetic fixtures, generated locally without private files or TTS."""
from functools import lru_cache
from pathlib import Path
import subprocess
import tempfile

_folder = tempfile.TemporaryDirectory(prefix='media-fixture-')


@lru_cache(maxsize=1)
def fixture_path():
    p=Path(_folder.name)/'original 空格.mp4'
    subprocess.run(['ffmpeg','-hide_banner','-v','error','-nostdin','-f','lavfi','-i',
        'color=c=blue:s=320x240:r=25:d=4','-f','lavfi','-i','sine=frequency=440:duration=4',
        '-c:v','libx264','-pix_fmt','yuv420p','-c:a','aac','-shortest',str(p)],check=True,capture_output=True)
    return p
