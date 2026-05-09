# Install the fund as a Windows Service via NSSM.
# STAGED — manual-start by default; doesn't auto-run on boot until you flip it.
# Requires NSSM (https://nssm.cc/download). Run from project root in ELEVATED PowerShell.

param(
    [string]$ServiceName = "AITradingFund",
    [switch]$DryRun
)

if (-not (Get-Command nssm -ErrorAction SilentlyContinue)) {
    Write-Host "[FAIL] NSSM not on PATH. Download from https://nssm.cc/download" -ForegroundColor Red
    Write-Host "  Extract nssm.exe to C:\tools\nssm\ and add to PATH."
    exit 1
}

$fundDir = (Get-Location).Path
$python  = Join-Path $fundDir ".venv\Scripts\python.exe"

if (-not (Test-Path $python))   { Write-Host "[FAIL] No venv at $python" -ForegroundColor Red; exit 1 }
if (-not (Test-Path ".\.env"))  { Write-Host "[FAIL] No .env" -ForegroundColor Red; exit 1 }

Write-Host ""
Write-Host "=== Fund Service Installer ===" -ForegroundColor Cyan
Write-Host "Service name:   $ServiceName"
Write-Host "Working dir:    $fundDir"
Write-Host "Python:         $python"
Write-Host "Args:           -m runtime.main"
Write-Host "Stdout log:     logs\service_stdout.log"
Write-Host "Stderr log:     logs\service_stderr.log"
Write-Host "Start mode:     manual (you must run 'nssm start' explicitly)"
Write-Host ""

if ($DryRun) {
    Write-Host "[DRY RUN] No changes made. Re-run without -DryRun to install." -ForegroundColor Yellow
    exit 0
}

Write-Host "Press Ctrl+C in the next 5 seconds to abort..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$existing = & nssm status $ServiceName 2>$null
if ($existing) {
    Write-Host "[WARN] Service '$ServiceName' exists ($existing). Removing first..." -ForegroundColor Yellow
    nssm stop $ServiceName 2>$null
    nssm remove $ServiceName confirm
}

Write-Host "Installing service..." -ForegroundColor Cyan
nssm install $ServiceName $python
nssm set $ServiceName AppParameters     "-m runtime.main"
nssm set $ServiceName AppDirectory      $fundDir
nssm set $ServiceName AppEnvironmentExtra "PYTHONUNBUFFERED=1"
nssm set $ServiceName AppStdout         (Join-Path $fundDir "logs\service_stdout.log")
nssm set $ServiceName AppStderr         (Join-Path $fundDir "logs\service_stderr.log")
nssm set $ServiceName AppRotateFiles    1
nssm set $ServiceName AppRotateBytes    10485760
nssm set $ServiceName AppExit Default   Restart
nssm set $ServiceName AppRestartDelay   5000
nssm set $ServiceName Start SERVICE_DEMAND_START

Write-Host ""
Write-Host "[ OK ] Service installed but NOT started. Manual control:" -ForegroundColor Green
Write-Host "  Start:           nssm start $ServiceName"
Write-Host "  Stop:            nssm stop $ServiceName"
Write-Host "  Auto-start:      nssm set $ServiceName Start SERVICE_AUTO_START"
Write-Host "  Remove:          nssm stop $ServiceName ; nssm remove $ServiceName confirm"
Write-Host "  Logs:            logs\service_stdout.log"
