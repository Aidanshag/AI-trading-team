# Install two scheduled tasks for the universal shadow-discovery pipeline:
#   FundBarRefresh — daily 02:00 ET pulls latest bars for any new
#                    symbols + updates existing
#   FundUniversalSweep — weekly Sun 20:00 ET runs walk-forward sweep
#                        + stages new eligible cells in shadow mode
$ProjectRoot = 'C:\Users\Owner\OneDrive\Personal AI\AI Trading'
$Python = Join-Path $ProjectRoot '.venv\Scripts\python.exe'

# --- FundBarRefresh — daily incremental bar pull ---
try { schtasks.exe /delete /tn 'FundBarRefresh' /f 2>$null } catch {}
$action1 = New-ScheduledTaskAction -Execute $Python -Argument '-m scripts.pull_rth_bars --months 6 --threads 1' -WorkingDirectory $ProjectRoot
$trigger1 = New-ScheduledTaskTrigger -Daily -At 2am
$settings1 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 4)
$principal1 = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
Register-ScheduledTask -TaskName 'FundBarRefresh' -Action $action1 -Trigger $trigger1 -Settings $settings1 -Principal $principal1 -Description 'Daily refresh of bar history for all Topstep symbols (universal discovery)' | Out-Null
Write-Host 'Registered FundBarRefresh (daily 02:00 ET)'

# --- FundUniversalSweep — weekly walk-forward + stage shadow cells ---
try { schtasks.exe /delete /tn 'FundUniversalSweep' /f 2>$null } catch {}
$action2 = New-ScheduledTaskAction -Execute $Python -Argument '-c "import subprocess, sys; subprocess.check_call([sys.executable, \"-m\", \"scripts.universal_walk_forward\"]); subprocess.check_call([sys.executable, \"-m\", \"scripts.stage_shadow_cells\"])"' -WorkingDirectory $ProjectRoot
$trigger2 = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Sunday -At 8pm
$settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 2)
$principal2 = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Limited
Register-ScheduledTask -TaskName 'FundUniversalSweep' -Action $action2 -Trigger $trigger2 -Settings $settings2 -Principal $principal2 -Description 'Weekly universal walk-forward sweep + stage shadow cells' | Out-Null
Write-Host 'Registered FundUniversalSweep (Sun 20:00 ET)'
Write-Host ''
Write-Host 'Both tasks registered. Verify:'
Write-Host '  Get-ScheduledTask -TaskName FundBarRefresh,FundUniversalSweep'
