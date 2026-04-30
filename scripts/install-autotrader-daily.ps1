# Installs the FundAutoTraderDaily Windows scheduled task.
#
# Schedule: Mon-Fri at 06:30 local time
#   Why 06:30 not 07:30 (the autonomous RTH window start):
#   - 1 hour buffer for preflight + initial snapshot capture
#   - The auto_trader's own RTH-only check holds it from placing trades
#     until 07:30 ET, so starting earlier is safe
#   - If preflight fails (e.g., canTrade=false from a Topstep lockout),
#     the launcher aborts before auto_trader ever starts
#
# Stop: there's no stop task — auto_trader runs all day, but its
#   autonomous restrictions stop it from placing new entries after 14:30 ET.
#   The 5-min scan loop continues but only writes snapshots and logs the
#   regime/RTH blocks. Idle CPU/memory cost is negligible. To stop it
#   manually: close the "Fund Auto-Trader" window, or run `fund stop`.
#
# Usage (from project root, in PowerShell):
#   .\scripts\install-autotrader-daily.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = (Get-Location).Path
$Launcher = Join-Path $ProjectRoot "scripts\start-autotrader-daily.ps1"

if (-not (Test-Path $Launcher)) {
    throw "Launcher script not found at $Launcher"
}

Write-Host ""
Write-Host "=== Installing FundAutoTraderDaily ===" -ForegroundColor Cyan
Write-Host ""

$settings  = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 12)

$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

# Mon-Fri at 06:30 local time
$trigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "6:30AM"

$psArg = '-NoProfile -ExecutionPolicy Bypass -File "' + $Launcher + '"'
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument $psArg `
    -WorkingDirectory $ProjectRoot

# Unregister existing if present (idempotent install)
Get-ScheduledTask -TaskName "FundAutoTraderDaily" -ErrorAction SilentlyContinue |
    Unregister-ScheduledTask -Confirm:$false

Register-ScheduledTask `
    -TaskName "FundAutoTraderDaily" `
    -Description "Auto-starts fund auto_trader Mon-Fri at 06:30 local. Runs preflight first; aborts on any failure. The auto_trader's own RTH gate prevents trades before 07:30 ET." `
    -Trigger $trigger `
    -Action $action `
    -Settings $settings `
    -Principal $principal | Out-Null

Write-Host "  registered: Mon-Fri 06:30 local" -ForegroundColor Green
Write-Host ""
Write-Host "=== Installation complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "To run it now (test):  Start-ScheduledTask -TaskName FundAutoTraderDaily"
Write-Host "To stop it now:        fund stop"
Write-Host "To uninstall:          Unregister-ScheduledTask -TaskName FundAutoTraderDaily -Confirm:`$false"
Write-Host ""
Get-ScheduledTask -TaskName "FundAutoTraderDaily" | Format-Table TaskName, State, @{Label="NextRun";Expression={(Get-ScheduledTaskInfo -TaskName $_.TaskName).NextRunTime}} -AutoSize
