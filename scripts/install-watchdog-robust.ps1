# Install / re-install FundTraderWatchdog with robust settings.
#
# Fixes today's 41-min watchdog gap (caused by "Stop On Battery Mode" +
# "No Start On Batteries" — machine likely went on battery).
#
# New settings:
#   - Runs every 3 minutes (was 5)
#   - DOES start on battery
#   - Does NOT stop on battery
#   - Wakes computer to run (if asleep)
#   - Runs missed runs as soon as possible
#   - Higher priority (less likely to be deferred)
#
# Run this once. Re-run to update settings.
#
#   powershell.exe -ExecutionPolicy Bypass -File scripts\install-watchdog-robust.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$TaskName = "FundTraderWatchdog"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: python.exe not found at $Python" -ForegroundColor Red
    Write-Host "Activate venv or run install-autotrader-daily.ps1 first." -ForegroundColor Red
    exit 1
}

# Remove existing
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing $TaskName task..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Action: run watchdog
$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "-m scripts.trader_watchdog" `
    -WorkingDirectory $ProjectRoot

# Trigger: every 3 minutes, starting now, indefinitely
$StartTime = (Get-Date).AddMinutes(1)
$Trigger = New-ScheduledTaskTrigger -Once -At $StartTime `
    -RepetitionInterval (New-TimeSpan -Minutes 3) `
    -RepetitionDuration (New-TimeSpan -Days 9999)

# Settings: ROBUST mode — fix all the things that caused today's gap
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -WakeToRun

# Run as current user, with highest privileges so it doesn't get deprioritized
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Highest

$Description = "Auto-revives the trader if account_snapshots heartbeat goes stale (>12 min). Robust v2 (2026-05-06): runs on battery, wakes from sleep, retries on missed schedule, every 3 min. Replaces v1 which had 41-min gap on 2026-05-06 due to Stop-On-Battery."

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description $Description | Out-Null

Write-Host "Installed $TaskName with robust settings:" -ForegroundColor Green
Write-Host "  - Every 3 minutes (was 5)" -ForegroundColor Green
Write-Host "  - DOES start on battery" -ForegroundColor Green
Write-Host "  - Does NOT stop on battery" -ForegroundColor Green
Write-Host "  - Wakes computer if asleep" -ForegroundColor Green
Write-Host "  - Retries on missed schedule (StartWhenAvailable)" -ForegroundColor Green
Write-Host "  - Auto-restarts task itself on failure (3 retries, 1 min apart)" -ForegroundColor Green
Write-Host "  - 5-min execution timeout (was 2 min)" -ForegroundColor Green

# Verify
$task = Get-ScheduledTask -TaskName $TaskName
Write-Host ""
Write-Host "Verification:" -ForegroundColor Cyan
Write-Host "  State: $($task.State)"
Write-Host "  Next run: $((Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime)"
