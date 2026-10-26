$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    throw "Virtual environment not found. Run: python -m venv venv"
}

$logs = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Force -Path $logs | Out-Null

$pidFile = Join-Path $PSScriptRoot 'logs\server.pid'
if (Test-Path $pidFile) {
    $existingPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if ($existingPid -and (Get-Process -Id $existingPid -ErrorAction SilentlyContinue)) {
        Write-Output "kaoshibao is already running (PID $existingPid)."
        exit 0
    }
}

$env:FLASK_SECRET_KEY = ([guid]::NewGuid().ToString('N') + [guid]::NewGuid().ToString('N'))
$env:PYTHONUNBUFFERED = '1'

$stdout = Join-Path $logs 'server.out.log'
$stderr = Join-Path $logs 'server.err.log'
$arguments = @(
    '-m', 'waitress',
    '--listen=127.0.0.1:5678',
    '--threads=4',
    'app:app'
)

$process = Start-Process `
    -FilePath $python `
    -ArgumentList $arguments `
    -WorkingDirectory $PSScriptRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdout `
    -RedirectStandardError $stderr `
    -PassThru

$listenerPid = $null
for ($attempt = 0; $attempt -lt 50; $attempt++) {
    Start-Sleep -Milliseconds 200
    $connection = Get-NetTCPConnection -LocalPort 5678 -State Listen -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($connection) {
        $listenerPid = $connection.OwningProcess
        break
    }
    if ($process.HasExited) {
        break
    }
}

if (-not $listenerPid) {
    throw "kaoshibao failed to start. Check logs\server.err.log"
}

Set-Content -Path $pidFile -Value $listenerPid -Encoding ascii
Write-Output "Started kaoshibao (PID $listenerPid) at http://127.0.0.1:5678"
