# Registers a one-shot scheduled task to launch live_trader at Sunday 17:00 ET
# (Globex reopen) so the Asian session is captured even when the user is away.
#
# Does NOT require admin — uses RunLevel Limited so it runs as the current user.
# Idempotent: re-running deletes any prior version.
#
# Run via:
#   powershell.exe -ExecutionPolicy Bypass -File scripts\register-sunday-kickstart.ps1

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$TaskName = "FundLiveTraderSundayKickstart"
$LogPath = Join-Path $ProjectRoot "logs\livetrader_sunday_kickstart.log"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: python.exe not found at $Python" -ForegroundColor Red
    exit 1
}

# Compute the next Sunday 17:00 in local time (machine is ET so this is ET)
$now = Get-Date
$daysUntilSunday = (7 - [int]$now.DayOfWeek) % 7
if ($daysUntilSunday -eq 0 -and $now.Hour -ge 17) {
    # It's Sunday evening already — set for next Sunday
    $daysUntilSunday = 7
}
$target = $now.Date.AddDays($daysUntilSunday).AddHours(17)
Write-Host "Target launch time: $target (in $([math]::Round(($target - $now).TotalHours, 1)) hours)" -ForegroundColor Cyan

# Remove any existing task with this name (idempotent)
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing $TaskName task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Action: launch live_trader, log all output. No preflight (user-initiated overnight run).
$psArg = @"
"`$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffzzz') Sunday kickstart firing -- launching live_trader" |
    Out-File -FilePath '$LogPath' -Append
& "$Python" -m scripts.live_trader 2>&1 |
    Out-File -FilePath '$LogPath' -Append
"@

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command $psArg" `
    -WorkingDirectory $ProjectRoot

# One-time trigger at the computed Sunday 17:00 local time
$Trigger = New-ScheduledTaskTrigger -Once -At $target

# Settings: wake from sleep, retry on miss, battery-tolerant, run for up to 24h
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 24) `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -WakeToRun

# Run as current user with limited (non-admin) privileges
$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType Interactive `
    -RunLevel Limited

$Description = "One-shot launch of live_trader at next Sunday 17:00 ET (Globex reopen / Asian session start). Captures Sunday-night Asian session signals when user is away. Replaced or re-armed by re-running register-sunday-kickstart.ps1."

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description $Description | Out-Null

# Verify
$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName

Write-Host ""
Write-Host "Registered $TaskName" -ForegroundColor Green
Write-Host "  State:        $($task.State)" -ForegroundColor Green
Write-Host "  Next run:     $($info.NextRunTime)" -ForegroundColor Green
Write-Host "  Action:       $Python -m scripts.live_trader" -ForegroundColor Green
Write-Host "  Log:          $LogPath" -ForegroundColor Green
Write-Host ""
Write-Host "To verify later:" -ForegroundColor Cyan
Write-Host "  Get-ScheduledTask -TaskName $TaskName | Format-List"
Write-Host "To cancel before it fires:" -ForegroundColor Cyan
Write-Host "  Unregister-ScheduledTask -TaskName $TaskName -Confirm:`$false"
