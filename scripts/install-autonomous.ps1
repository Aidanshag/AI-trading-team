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
Write-Host "[2/2] FundRuntimeBoot (at user logon)" -ForegroundColor Yellow
if (-not (Test-Path $BootScript)) {
    Write-Host "  [skip] start-runtime.ps1 missing" -ForegroundColor DarkYellow
} else {
    $trigger2 = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
    $psArg = '-NoProfile -ExecutionPolicy Bypass -File "' + $BootScript + '"'
    $action2  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArg -WorkingDirectory $ProjectRoot

    Get-ScheduledTask -TaskName "FundRuntimeBoot" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
    Register-ScheduledTask -TaskName "FundRuntimeBoot" -Description "Launches runtime/main.py at logon." -Trigger $trigger2 -Action $action2 -Settings $settings -Principal $principal | Out-Null
    Write-Host "  registered" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Installation complete ===" -ForegroundColor Green
Write-Host ""
Get-ScheduledTask -TaskName "FundCIOMorningWake","FundRuntimeBoot" -ErrorAction SilentlyContinue | Format-Table TaskName, State -AutoSize
