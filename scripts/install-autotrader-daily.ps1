# Installs the FundAutoTraderDaily Windows scheduled task.
#
# Schedule:
#   1) Mon-Fri at 06:30 local time - normal pre-market start
#   2) AtStartup - covers reboots mid-session (e.g., forced OS upgrade)
#   3) AtLogOn (current user) - covers reboots that auto-login after
#
# The launcher's PID lock + preflight idempotency make duplicate-fire safe.
#
# Usage (admin PowerShell):
#   & "C:\Users\Owner\OneDrive\Personal AI\AI Trading\scripts\install-autotrader-daily.ps1"

$ErrorActionPreference = "Stop"

# Resolve project root from this script's location, not Get-Location.
# Admin PowerShell opens in C:\Windows\System32; using Get-Location would
# look for the launcher there. $PSScriptRoot is always this script's folder.
$ProjectRoot = $PSScriptRoot | Split-Path -Parent
$Launcher = Join-Path $ProjectRoot "scripts\start-autotrader-daily.ps1"

if (-not (Test-Path $Launcher)) {
    throw "Launcher script not found at $Launcher"
}

Write-Host ""
Write-Host "=== Installing FundAutoTraderDaily ===" -ForegroundColor Cyan
Write-Host ""

$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Hours 12)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

$triggerWeekly  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "6:30AM"
$triggerStartup = New-ScheduledTaskTrigger -AtStartup
$triggerLogon   = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger = @($triggerWeekly, $triggerStartup, $triggerLogon)

$psArg = '-NoProfile -ExecutionPolicy Bypass -File "' + $Launcher + '"'
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $psArg -WorkingDirectory $ProjectRoot

$TaskName = "FundAutoTraderDaily"
$TaskDescription = "Auto-starts fund auto_trader. Triggers: Mon-Fri 06:30 local + AtStartup + AtLogOn. Runs preflight first; aborts on failure."

# Idempotent install with rollback safety.
# 2026-05-04 incident: previous version did Unregister then Register. If the
# Register failed (e.g., access denied), the user was left with NO task at all.
# New flow: back up XML, use Register -Force (atomic overwrite), restore from
# XML if Register fails after the task was somehow removed.
$backupXml = $null
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    try {
        $backupXml = Export-ScheduledTask -TaskName $TaskName
        Write-Host "  existing task backed up for rollback" -ForegroundColor DarkGray
    } catch {
        Write-Host ("  warn: backup failed: " + $_.Exception.Message) -ForegroundColor Yellow
    }
}

$registerOk = $false
try {
    Register-ScheduledTask -TaskName $TaskName -Description $TaskDescription -Trigger $trigger -Action $action -Settings $settings -Principal $principal -Force -ErrorAction Stop | Out-Null
    $registerOk = $true
    Write-Host "  registered: Mon-Fri 06:30 + AtStartup + AtLogOn" -ForegroundColor Green
} catch {
    $errMsg = $_.Exception.Message
    Write-Host ("  FAILED to register: " + $errMsg) -ForegroundColor Red

    $stillThere = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $stillThere -and $backupXml) {
        Write-Host "  ROLLING BACK to previous task definition..." -ForegroundColor Yellow
        try {
            Register-ScheduledTask -TaskName $TaskName -Xml $backupXml -ErrorAction Stop | Out-Null
            Write-Host "  rollback OK" -ForegroundColor Green
        } catch {
            Write-Host ("  ROLLBACK ALSO FAILED: " + $_.Exception.Message) -ForegroundColor Red
            Write-Host "  Task is now MISSING. Re-run from an elevated shell to recover." -ForegroundColor Red
        }
    } elseif (-not $stillThere) {
        Write-Host "  No prior task to roll back to. Re-run from an elevated shell." -ForegroundColor Red
    } else {
        Write-Host "  Existing task is still present and untouched." -ForegroundColor Green
    }

    $accessDenied = ($errMsg -like '*Access is denied*') -or ($errMsg -like '*0x80070005*')
    if ($accessDenied) {
        Write-Host ""
        Write-Host "  CAUSE: this PowerShell window is not running as Administrator." -ForegroundColor Yellow
        Write-Host "  FIX:   right-click PowerShell -> Run as administrator, then re-run this script." -ForegroundColor Yellow
    }
    throw
}

Write-Host ""
Write-Host "=== FundAutoTraderDaily registered ===" -ForegroundColor Green

# ============================================================
# FundTraderWatchdog — runs every 5 min, restarts dead trader
# ============================================================
Write-Host ""
Write-Host "=== Installing FundTraderWatchdog ===" -ForegroundColor Cyan

$WatchdogTaskName = "FundTraderWatchdog"
$WatchdogDescription = "Runs every 5 min. Detects dead/stuck trader via DB heartbeat (account_snapshots age > 12 min) and auto-restarts via FundAutoTraderDaily. Sends Discord alert if DISCORD_WEBHOOK_URL is set."

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$WatchdogScript = Join-Path $ProjectRoot "scripts\trader_watchdog.py"

if (-not (Test-Path $Python)) {
    Write-Host "  WARN: python.exe missing - watchdog wont work until .venv exists" -ForegroundColor Yellow
}
if (-not (Test-Path $WatchdogScript)) {
    throw "Watchdog script not found at $WatchdogScript"
}

# Trigger: once at install+2min, then repeat every 5 min indefinitely.
# Standard Windows pattern for periodic tasks.
$wTriggerStart = (Get-Date).AddMinutes(2)
$wTrigger = New-ScheduledTaskTrigger -Once -At $wTriggerStart -RepetitionInterval (New-TimeSpan -Minutes 5) -RepetitionDuration (New-TimeSpan -Days 9999)

# Action: invoke python directly (no nested powershell quoting). Pass
# PYTHONUTF8 via env-var prefix syntax that schtasks understands.
$wAction = New-ScheduledTaskAction -Execute $Python -Argument "-m scripts.trader_watchdog" -WorkingDirectory $ProjectRoot

$wSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2) `
    -MultipleInstances IgnoreNew

$wPrincipal = New-ScheduledTaskPrincipal -UserId $env:USERNAME `
    -LogonType Interactive -RunLevel Limited

# Backup + register-with-rollback (same pattern as FundAutoTraderDaily)
$wBackup = $null
$wExisting = Get-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
if ($wExisting) {
    try { $wBackup = Export-ScheduledTask -TaskName $WatchdogTaskName } catch {}
}

try {
    Register-ScheduledTask -TaskName $WatchdogTaskName `
        -Description $WatchdogDescription `
        -Trigger $wTrigger -Action $wAction -Settings $wSettings -Principal $wPrincipal `
        -Force -ErrorAction Stop | Out-Null
    Write-Host "  registered: every 5 min, starting $($wTriggerStart.ToString('HH:mm'))" -ForegroundColor Green
} catch {
    $errMsg = $_.Exception.Message
    Write-Host ("  FAILED to register watchdog: " + $errMsg) -ForegroundColor Red
    $stillThere = Get-ScheduledTask -TaskName $WatchdogTaskName -ErrorAction SilentlyContinue
    if (-not $stillThere -and $wBackup) {
        try { Register-ScheduledTask -TaskName $WatchdogTaskName -Xml $wBackup -ErrorAction Stop | Out-Null
              Write-Host "  rollback OK" -ForegroundColor Green } catch {
              Write-Host "  rollback failed: $($_.Exception.Message)" -ForegroundColor Red }
    }
    throw
}

Write-Host ""
Write-Host "=== Installation complete (both tasks) ===" -ForegroundColor Green
Write-Host ""
Write-Host "Tasks registered:"
Get-ScheduledTask | Where-Object { $_.TaskName -in @($TaskName, $WatchdogTaskName) } |
    Format-Table TaskName, State, @{Label="Triggers";Expression={$_.Triggers.Count}},
                 @{Label="NextRun";Expression={(Get-ScheduledTaskInfo -TaskName $_.TaskName).NextRunTime}} -AutoSize

Write-Host ""
Write-Host "Test now:        Start-ScheduledTask -TaskName FundAutoTraderDaily"
Write-Host "Watchdog status: python -m scripts.trader_watchdog --status"
Write-Host "Force-restart:   python -m scripts.trader_watchdog --force"
