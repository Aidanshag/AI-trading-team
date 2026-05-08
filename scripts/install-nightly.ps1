# Install the FundNightlyReports scheduled task.
# Runs nightly at 6:30 PM local time after the cash session has settled.
# Includes: shadow recap, P&L attribution, sim equity curve, scorecards,
# lesson auto-promote, and tomorrow's economic calendar.
#
# Usage:
#   cd "C:\Users\Owner\OneDrive\Personal AI\AI Trading"
#   powershell -NoProfile -ExecutionPolicy Bypass -File scripts\install-nightly.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot   = (Get-Location).Path
$Python        = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$NightlyScript = Join-Path $ProjectRoot "scripts\nightly_reports.py"

if (-not (Test-Path $Python))        { throw "Python not found at $Python — activate the venv or run install-claude-cli.ps1 first." }
if (-not (Test-Path $NightlyScript)) { throw "Nightly script not found at $NightlyScript" }

Write-Host ""
Write-Host "=== Installing FundNightlyReports task ===" -ForegroundColor Cyan
Write-Host ""

$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Minutes 20)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

# Run nightly at 18:30 local. Mon-Fri only — weekends nothing closes.
Write-Host "[1/1] FundNightlyReports (Mon-Fri 18:30 local)" -ForegroundColor Yellow
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "6:30PM"
$pyArg   = '-m scripts.nightly_reports'
$action  = New-ScheduledTaskAction -Execute $Python -Argument $pyArg -WorkingDirectory $ProjectRoot

Get-ScheduledTask -TaskName "FundNightlyReports" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false
Register-ScheduledTask `
    -TaskName    "FundNightlyReports" `
    -Description "End-of-day fund maintenance: shadow recap, P&L attribution, scorecards, lesson auto-promote, economic calendar build." `
    -Trigger     $trigger `
    -Action      $action `
    -Settings    $settings `
    -Principal   $principal | Out-Null

Write-Host "  registered" -ForegroundColor Green
Write-Host ""
Write-Host "=== Installation complete ===" -ForegroundColor Green
Write-Host ""
Get-ScheduledTask -TaskName "FundNightlyReports" -ErrorAction SilentlyContinue | Format-Table TaskName, State, @{Label="NextRun"; Expression={(Get-ScheduledTaskInfo $_).NextRunTime}} -AutoSize
Write-Host ""
Write-Host "To run it manually right now:" -ForegroundColor DarkGray
Write-Host "  Start-ScheduledTask -TaskName FundNightlyReports" -ForegroundColor DarkGray
Write-Host ""
Write-Host "To uninstall:" -ForegroundColor DarkGray
Write-Host "  Unregister-ScheduledTask -TaskName FundNightlyReports -Confirm:`$false" -ForegroundColor DarkGray
