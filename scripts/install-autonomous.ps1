$ErrorActionPreference = "Stop"

$ProjectRoot = (Get-Location).Path
$Python      = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$WakeScript  = Join-Path $ProjectRoot "scripts\morning_auto_wake.py"
$BootScript  = Join-Path $ProjectRoot "scripts\start-runtime.ps1"

if (-not (Test-Path $Python))     { throw "Python not found at $Python" }
if (-not (Test-Path $WakeScript)) { throw "Wake script not found at $WakeScript" }

Write-Host ""
Write-Host "=== Installing autonomous fund tasks ===" -ForegroundColor Cyan
Write-Host ""

$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

# Task 1 — FundCIOMorningWake
Write-Host "[1/2] FundCIOMorningWake (weekdays 09:30 local)" -ForegroundColor Yellow
$trigger1 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "9:30AM"
$pyArg = '"' + $WakeScript + '"'
$action1  = New-ScheduledTaskAction -Execute $Python -Argument $pyArg -WorkingDirectory $ProjectRoot

Get-ScheduledTask -TaskName "FundCIOMorningWake" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
Register-ScheduledTask -TaskName "FundCIOMorningWake" -Description "One-shot CIO wake. Mon-Fri 09:30 local." -Trigger $trigger1 -Action $action1 -Settings $settings -Principal $principal | Out-Null
Write-Host "  registered" -ForegroundColor Green

# Task 2 — FundRuntimeBoot
# Triggers (all three for redundancy — non-admin install must use these):
#   1. AtLogOn — fires when user logs in (covers daily reboot/logon path)
#   2. Daily 08:00 — fires once a day even if no logon happened (e.g.
#      laptop never restarts)
#   3. Repetition every 30 min — if the runtime ever crashes, the next
#      cycle re-launches it. start-runtime.ps1 is idempotent: if a python
#      process already holds the runtime, it exits without spawning a dup.
Write-Host "[2/2] FundRuntimeBoot (logon + daily 08:00 + every 30min retry)" -ForegroundColor Yellow
if (-not (Test-Path $BootScript)) {
    Write-Host "  [skip] start-runtime.ps1 missing" -ForegroundColor DarkYellow
} else {
    $logonTrigger  = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $dailyTrigger  = New-ScheduledTaskTrigger -Daily -At "8:00AM"
    # Repeat every 30 min for 24h after each daily trigger (catches crashes)
    $dailyTrigger.Repetition = (New-ScheduledTaskTrigger -Once -At "8:00AM" `
        -RepetitionInterval (New-TimeSpan -Minutes 30) `
        -RepetitionDuration (New-TimeSpan -Hours 24)).Repetition

    $psArg    = '-NoProfile -ExecutionPolicy Bypass -File "' + $BootScript + '"'
    $action2  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArg -WorkingDirectory $ProjectRoot

    Get-ScheduledTask -TaskName "FundRuntimeBoot" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    Register-ScheduledTask -TaskName "FundRuntimeBoot" `
        -Description "Launches runtime/main.py at logon + daily 08:00 with 30-min retry. Idempotent: duplicate launches no-op." `
        -Trigger $logonTrigger,$dailyTrigger -Action $action2 -Settings $settings -Principal $principal | Out-Null
    Write-Host "  registered (logon + daily 08:00 + 30min retry)" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Installation complete ===" -ForegroundColor Green
Write-Host ""
Get-ScheduledTask -TaskName "FundCIOMorningWake","FundRuntimeBoot" -ErrorAction SilentlyContinue | Format-Table TaskName, State -AutoSize
