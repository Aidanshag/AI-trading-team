# Install FundRoutineSummary scheduled task.
# Fires daily at 10:00 UTC = 5/6 AM ET depending on DST.
# Pings Discord with any non-session-auto-commit activity from the last 25h.
# Lets the user see what the cloud /improve-fund routine + cowork built.

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$TaskName = "FundRoutineSummary"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: python.exe not found at $Python" -ForegroundColor Red
    exit 1
}

# Remove any prior
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

$Action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "-m scripts.notify_routine_commits" `
    -WorkingDirectory $ProjectRoot

# Daily at 10:00 UTC. Local time on this Windows box is ET so we need to
# convert: 10:00 UTC = 06:00 EDT (summer) or 05:00 EST (winter).
# Schedule at 06:00 local; if DST changes the gap, we'll be ~5-6 AM ET which
# is still after the 09:00 UTC routine fire either way.
$Trigger = New-ScheduledTaskTrigger -Daily -At "6:00AM"

$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 3) `
    -MultipleInstances IgnoreNew `
    -WakeToRun

$Description = "Daily 06:00 ET: ping Discord with autonomous-routine + cowork commits from the last 25h. Filters out the user's session auto-commits."

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
