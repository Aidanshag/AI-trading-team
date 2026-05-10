# Install / re-install FundLiveTraderMonMorning scheduled task.
#
# Fires Mon-Fri 06:30 ET. Runs restart-live-trader-if-dead.ps1 which
# checks for a running live_trader and launches one only if absent.
#
# Run once:
#   powershell.exe -ExecutionPolicy Bypass -File scripts\install-live-trader-morning.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$RestartScript = Join-Path $ProjectRoot "scripts\restart-live-trader-if-dead.ps1"
$TaskName = "FundLiveTraderMonMorning"

if (-not (Test-Path $RestartScript)) {
    Write-Host "ERROR: restart script not found at $RestartScript" -ForegroundColor Red
    exit 1
}

# Remove existing
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing $TaskName task..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$RestartScript`"" `
    -WorkingDirectory $ProjectRoot

# Trigger: weekly, Mon-Fri at 06:30 local time
$Trigger = New-ScheduledTaskTrigger `
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

$Description = "Mon-Fri 06:30 ET: restart scripts.live_trader if it's not currently running. Idempotent (duplicate-safe). Backup recovery for any overnight silent crash."

# Register without an explicit Principal — uses the current interactive user.
# We deliberately do NOT request RunLevel Highest (would need admin to register).
Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description $Description | Out-Null

Write-Host "Installed $TaskName" -ForegroundColor Green
$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "  State:    $($task.State)"
Write-Host "  Next run: $($info.NextRunTime)"
