# Install Windows Scheduled Task for the simplified Layer 1 live trader.
#
# This installs `FundLiveTraderDaily` — runs the simplified scripts/live_trader.py
# with the same scheduling pattern as the v1 `FundAutoTraderDaily` but pointing
# at the new minimal-knife trader.
#
# Both can coexist briefly during deployment cutover. To switch:
#   1. Run this installer to register FundLiveTraderDaily
#   2. Verify FundLiveTraderDaily starts cleanly (test --once)
#   3. Disable FundAutoTraderDaily:
#        Disable-ScheduledTask -TaskName FundAutoTraderDaily
#   4. Sunday 5 PM ET Globex reopen → FundLiveTraderDaily picks up
#
# To roll back: re-enable FundAutoTraderDaily and disable FundLiveTraderDaily.
# v1 trader file (auto_trader.py) is preserved unchanged.
#
# Run as admin if modifying an existing task with RunLevel=Highest.
#
#   powershell.exe -ExecutionPolicy Bypass -File scripts\install-livetrader-daily.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$TaskName = "FundLiveTraderDaily"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: python.exe not found at $Python" -ForegroundColor Red
    Write-Host "Run install-autotrader-daily.ps1 first to create .venv." -ForegroundColor Red
    exit 1
}

# Remove existing task if present (idempotent re-install)
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    Write-Host "Removing existing $TaskName task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

# Action: launch via the same launcher pattern as v1, but pointing at live_trader
# Step 1: preflight (existing — validates env/broker/halt before trading)
# Step 2: launch live_trader continuous loop
$psArg = @"
& "$Python" -m scripts.preflight
if (`$LASTEXITCODE -ne 0) {
    `"$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffzzz') preflight FAILED -- aborting live_trader launch`" |
        Out-File -FilePath '$ProjectRoot\logs\livetrader_$(Get-Date -Format yyyyMMdd).log' -Append
    exit 1
}
`"$(Get-Date -Format 'yyyy-MM-ddTHH:mm:ss.fffzzz') preflight OK -- launching live_trader`" |
    Out-File -FilePath '$ProjectRoot\logs\livetrader_$(Get-Date -Format yyyyMMdd).log' -Append
& "$Python" -m scripts.live_trader 2>&1 |
    Out-File -FilePath '$ProjectRoot\logs\livetrader_$(Get-Date -Format yyyyMMdd).log' -Append
"@

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -Command $psArg" `
    -WorkingDirectory $ProjectRoot

# Trigger: same Mon-Fri 06:30 ET pattern as v1 (effectively 06:30 local time
# since this is a personal machine in ET). Repetition handled by the trader's
# internal continuous loop, so we just need the daily start.
$Trigger = New-ScheduledTaskTrigger `
    -Daily `
    -At "06:30" `
    -DaysInterval 1

# Settings: robust mode (battery tolerant, retry on miss, wake-from-sleep)
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 24) `
    -MultipleInstances IgnoreNew `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -WakeToRun

# Run as current user with highest privileges
$Principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType S4U `
    -RunLevel Highest

$Description = "Layer 1 simplified live trader (~480 lines). Replaces FundAutoTraderDaily (v1 was 2929 lines). Reads validated cells from state/strategy_validation.json:live_allowlist (the brain's output). Preserves all brain infrastructure (agents, vault, validation pipeline). Installed 2026-05-08 simplification."

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description $Description | Out-Null

Write-Host "Installed $TaskName" -ForegroundColor Green
Write-Host "  Trigger: daily 06:30 local time" -ForegroundColor Green
Write-Host "  Action:  $Python -m scripts.live_trader" -ForegroundColor Green
Write-Host ""

# Verification
$task = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName
Write-Host "Verification:" -ForegroundColor Cyan
Write-Host "  State:        $($task.State)"
Write-Host "  Next run:     $($info.NextRunTime)"
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Test single scan:  $Python -m scripts.live_trader --once --dry-run"
Write-Host "  2. Test paper-mode:   $Python -m scripts.live_trader --once --paper"
Write-Host "  3. When ready, disable v1:  Disable-ScheduledTask -TaskName FundAutoTraderDaily"
Write-Host "  4. Sunday 5 PM ET Globex reopen → live_trader takes over"
