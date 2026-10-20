$taskPython = if (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.venv\Scripts\python.exe')) { Join-Path $PSScriptRoot '.venv\Scripts\python.exe' } else { 'python' }
& $taskPython -B -X utf8 (Join-Path $PSScriptRoot 'workbench.py') @args
exit $LASTEXITCODE
