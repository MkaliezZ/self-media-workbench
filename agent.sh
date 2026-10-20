#!/bin/sh
set -eu
task_root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -x "$task_root/.venv/bin/python" ]; then
  exec "$task_root/.venv/bin/python" -B -X utf8 "$task_root/workbench.py" "$@"
fi
exec python3 -B -X utf8 "$task_root/workbench.py" "$@"
