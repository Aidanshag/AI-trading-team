# Stops the runtime daemon launched by start-runtime.ps1.

$ErrorActionPreference = "Continue"

$ProjectRoot = $PSScriptRoot | Split-Path -Parent
$PidFile = Join-Path $ProjectRoot "logs\runtime.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "No PID file at $PidFile - runtime may not be running" -ForegroundColor Yellow
    exit 0
}

$processId = Get-Content $PidFile | Select-Object -First 1
if (-not $processId) {
    Write-Host "PID file empty" -ForegroundColor Yellow
    exit 0
}

$proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
if (-not $proc) {
    Write-Host "Process $processId not running (already exited?)" -ForegroundColor Yellow
    Remove-Item $PidFile -ErrorAction SilentlyContinue
    exit 0
}

Stop-Process -Id $processId -Force
Write-Host "Stopped runtime PID $processId" -ForegroundColor Green
Remove-Item $PidFile -ErrorAction SilentlyContinue
