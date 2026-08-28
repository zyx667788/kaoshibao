$ErrorActionPreference = 'Continue'
"START " + (Get-Date -Format HH:mm:ss) | Out-File D:\gdx\kaoshibao\debug\run_diag.log -Encoding utf8
Set-Location 'D:\gdx\kaoshibao'
"PY=" + (Get-Command python -ErrorAction SilentlyContinue).Source | Out-File D:\gdx\kaoshibao\debug\run_diag.log -Append -Encoding utf8
"PYVER=" + (python --version 2>&1) | Out-File D:\gdx\kaoshibao\debug\run_diag.log -Append -Encoding utf8
$env:FLASK_APP = 'D:\gdx\kaoshibao\app.py'
python -m flask run --host=0.0.0.0 --port=5678 --no-debugger --no-reload 2>&1 | Out-File D:\gdx\kaoshibao\debug\run_err.log -Append -Encoding utf8