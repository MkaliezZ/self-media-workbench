"""Locate the installed local checkout; forward tasks to its unified entry."""
import json
import os
from pathlib import Path
import subprocess
import sys

here=Path(__file__).resolve()
location=here.parents[1]/'location.json'
root=Path(os.environ['SELF_MEDIA_WORKBENCH_ROOT']) if os.environ.get('SELF_MEDIA_WORKBENCH_ROOT') else (
    Path(json.loads(location.read_text('utf-8'))['root']) if location.exists() else here.parents[3])
entry=root/'workbench.py'
if not entry.is_file():
    raise SystemExit('Workbench checkout not found; install it and run workbench.py install-skill, or set SELF_MEDIA_WORKBENCH_ROOT')
raise SystemExit(subprocess.call([sys.executable,'-B','-X','utf8',str(entry),*sys.argv[1:]]))
