"""Locate the installed local checkout; forward tasks to its unified entry."""
import json
import os
from pathlib import Path
import subprocess
import sys

here=Path(__file__).resolve()
location=here.parents[1]/'location.json'
installed=json.loads(location.read_text('utf-8')) if location.exists() else {}
root=Path(os.environ['SELF_MEDIA_WORKBENCH_ROOT']) if os.environ.get('SELF_MEDIA_WORKBENCH_ROOT') else (
    Path(installed['root']) if installed else here.parents[3])
entry=root/'workbench.py'
if not entry.is_file():
    raise SystemExit('Workbench checkout not found; install it and run workbench.py install-skill, or set SELF_MEDIA_WORKBENCH_ROOT')
# An Agent may use a different Python from the one with this workbench's deps.
# Prefer the checkout venv, then the interpreter recorded by install-skill.
venv=root/('.venv/Scripts/python.exe' if os.name=='nt' else '.venv/bin/python')
recorded=Path(installed.get('python',sys.executable))
interpreter=venv if venv.is_file() else recorded if recorded.is_file() else Path(sys.executable)
raise SystemExit(subprocess.call([str(interpreter),'-B','-X','utf8',str(entry),*sys.argv[1:]]))
