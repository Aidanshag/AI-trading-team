# One-shot: schedule FundRestoreEmergencyFlatten to fire at 9:00 AM
# tomorrow (local Eastern Time). Idempotent — re-running replaces the task.

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\Owner\OneDrive\Personal AI\AI Trading"
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

$TomorrowAt9am = (Get-Date).Date.AddDays(1).AddHours(9)

$action = New-ScheduledTaskAction -Execute $Python -Argument "-m scripts.restore_emergency_flatten" -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -Once -At $TomorrowAt9am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

Get-ScheduledTask -TaskName "FundRestoreEmergencyFlatten" -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false

Register-ScheduledTask -TaskName "FundRestoreEmergencyFlatten" `
    -Description "Auto-restore -750 emergency_flatten level disabled by user on 2026-04-29." `
    -Trigger $trigger -Action $action -Settings $settings -Principal $principal | Out-Null

Write-Host ""
Write-Host "Scheduled FundRestoreEmergencyFlatten" -ForegroundColor Green
Write-Host "  Will fire at: $($TomorrowAt9am.ToString('yyyy-MM-dd HH:mm')) (local time)" -ForegroundColor Cyan
Write-Host ""
$info = Get-ScheduledTaskInfo -TaskName "FundRestoreEmergencyFlatten"
Write-Host "  Next run time: $($info.NextRunTime)" -ForegroundColor DarkGray
Write-Host "  Last result: not yet run" -ForegroundColor DarkGray
