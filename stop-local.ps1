$ErrorActionPreference = 'Stop'

Set-Location $PSScriptRoot

$pidFile = Join-Path $PSScriptRoot 'logs\server.pid'
if (-not (Test-Path $pidFile)) {
    Write-Output 'kaoshibao is not running.'
    exit 0
}

$serverPid = Get-Content $pidFile -ErrorAction SilentlyContinue
if ($serverPid -and (Get-Process -Id $serverPid -ErrorAction SilentlyContinue)) {
    taskkill.exe /PID $serverPid /T /F | Out-Null
    Write-Output "Stopped kaoshibao (PID $serverPid)."
} else {
    Write-Output 'kaoshibao is not running.'
}

Remove-Item -LiteralPath $pidFile -Force
