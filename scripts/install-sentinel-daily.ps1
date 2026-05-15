# Register FundSentinel — Windows scheduled task that runs every 10 min.
# Idempotent. Run from PowerShell in the project root.
$ProjectRoot = 'C:\Users\Owner\OneDrive\Personal AI\AI Trading'
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'
try { schtasks.exe /delete /tn 'FundSentinel' /f 2>$null } catch {}
$action = New-ScheduledTaskAction -Execute $Python -Argument '-m tools.sentinel --report' -WorkingDirectory $ProjectRoot
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 10)
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
Register-ScheduledTask -TaskName 'FundSentinel' -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description 'Run sentinel every 10 min' | Out-Null
Write-Host 'Registered FundSentinel'
