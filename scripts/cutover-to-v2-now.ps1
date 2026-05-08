# One-shot admin cutover script — runs the entire Sunday cutover today.
#
# Performs:
#   1. Disable FundAutoTraderDaily (v1 task — won't fire again)
#   2. Disable FundTraderWatchdog (v1-aware watchdog — needs update)
#   3. Install FundLiveTraderDaily (v2 task — picks up Mon 06:30 ET)
#   4. Verify all task states
#
# Run as Administrator:
#   Right-click PowerShell → Run as Administrator → cd to project → run this script
#   OR from elevated terminal:  powershell.exe -ExecutionPolicy Bypass -File scripts\cutover-to-v2-now.ps1
#
# Idempotent — safe to re-run.
#
# After this runs:
#   - Today's manual live_trader process keeps running (this script doesn't touch it)
#   - Mon 06:30 ET: scheduled task auto-launches v2 from cold
#   - Watchdog stays disabled until updated (rewrite scheduled separately)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path

# Sanity: must be admin
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: must run as Administrator." -ForegroundColor Red
    Write-Host "Right-click PowerShell -> Run as Administrator -> re-run this script." -ForegroundColor Red
    exit 1
}

Write-Host "=== v2 Cutover ===" -ForegroundColor Cyan
Write-Host ""

# Step 1: disable v1 trader scheduled task
Write-Host "1. Disabling FundAutoTraderDaily (v1)..." -ForegroundColor Yellow
$v1 = Get-ScheduledTask -TaskName "FundAutoTraderDaily" -ErrorAction SilentlyContinue
if ($v1) {
    Disable-ScheduledTask -TaskName "FundAutoTraderDaily" | Out-Null
    Write-Host "   v1 task: Disabled" -ForegroundColor Green
} else {
    Write-Host "   v1 task: not present (skipped)" -ForegroundColor Gray
}

# Step 2: disable watchdog (was configured for v1 task name)
Write-Host "2. Disabling FundTraderWatchdog (v1-aware)..." -ForegroundColor Yellow
$wd = Get-ScheduledTask -TaskName "FundTraderWatchdog" -ErrorAction SilentlyContinue
if ($wd) {
    Disable-ScheduledTask -TaskName "FundTraderWatchdog" | Out-Null
    Write-Host "   watchdog task: Disabled (will be updated to v2-aware in followup)" -ForegroundColor Green
} else {
    Write-Host "   watchdog task: not present (skipped)" -ForegroundColor Gray
}

# Step 3: install v2 trader scheduled task
Write-Host "3. Installing FundLiveTraderDaily (v2)..." -ForegroundColor Yellow
& "$ProjectRoot\scripts\install-livetrader-daily.ps1"

# Step 4: final verification
Write-Host ""
Write-Host "=== Final state ===" -ForegroundColor Cyan
Get-ScheduledTask | Where-Object { $_.TaskName -match "Fund" } |
    Sort-Object TaskName |
    Format-Table TaskName,State

Write-Host ""
Write-Host "Cutover complete." -ForegroundColor Green
Write-Host "Today's manual live_trader run is unaffected." -ForegroundColor Green
Write-Host "Monday 06:30 ET: scheduled task launches v2 automatically." -ForegroundColor Green
