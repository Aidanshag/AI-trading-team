# Install / re-install FundLiveTraderEnsureRunning scheduled task.
#
# Fires:
#   - Sunday 17:00 ET (weekly) - Globex Sunday reopen kickoff
#   - Mon-Fri 06:30 ET (weekly) - morning recovery if overnight crashed
#
# Both triggers invoke the same idempotent script
# (restart-live-trader-if-dead.ps1), which only launches live_trader
# if no live_trader process is currently running. Safe to fire when
# the trader is already alive.
#
# Replaces the prior two-task split (FundLiveTraderSundayKickstart +
# FundLiveTraderMonMorning) which did the same work via separate tasks
# for historical reasons.
#
# Run once:
#   powershell.exe -ExecutionPolicy Bypass -File scripts\install-live-trader-ensure-running.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$RestartScript = Join-Path $ProjectRoot "scripts\restart-live-trader-if-dead.ps1"
$TaskName = "FundLiveTraderEnsureRunning"

if (-not (Test-Path $RestartScript)) {
    Write-Host "ERROR: restart script not found at $RestartScript" -ForegroundColor Red
    exit 1
}

# Remove existing single-purpose tasks (cleanup of the prior split).
$priorTasks = @(
    "FundLiveTraderSundayKickstart",
    "FundLiveTraderMonMorning",
    $TaskName
)
foreach ($t in $priorTasks) {
    $existing = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    if ($existing) {
        Write-Host "Removing existing $t..."
        Unregister-ScheduledTask -TaskName $t -Confirm:$false
    }
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RestartScript`"" `
    -WorkingDirectory $ProjectRoot

# Trigger 1: Sunday 17:00 ET weekly (Globex reopen / Asian session start)
$SundayTrigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Sunday `
    -At "5:00PM"

# Trigger 2: Mon-Fri 06:30 ET weekly (morning recovery if overnight crashed)
$WeekdayTrigger = New-ScheduledTaskTrigger `
    -Weekly `
    -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "6:30AM"

# Settings: survive battery / sleep, retry on missed schedule
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -WakeToRun

$Description = "Idempotent live_trader launcher. Fires Sun 17:00 ET (Globex reopen) and Mon-Fri 06:30 ET (overnight recovery). Calls restart-live-trader-if-dead.ps1 -- launches live_trader only if not already running. Replaces FundLiveTraderSundayKickstart + FundLiveTraderMonMorning."

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger @($SundayTrigger, $WeekdayTrigger) `
    -Settings $Settings `
    -Description $Description | Out-Null

Write-Host "Installed $TaskName" -ForegroundColor Green
$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "  State:    $($task.State)"
Write-Host "  Next run: $($info.NextRunTime)"
Write-Host "  Triggers: Sun 17:00 ET + Mon-Fri 06:30 ET"
