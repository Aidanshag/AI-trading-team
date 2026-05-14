# Cutover to brain/trader queue architecture.
#
# Fires from FundQueueCutover scheduled task (tomorrow morning before RTH).
# Steps:
#   1. Kill any existing live_trader and dry-mode brain_signaler
#   2. Start brain_signaler in REAL mode (emits signals to queue)
#   3. Start live_trader with --use-queue (consumes from queue)
#   4. Discord alert
#
# Idempotent + reversible: the legacy `scan_once` code remains in
# live_trader.py for one more session. Rollback is:
#   schtasks /Run /TN FundLiveTraderEnsureRunning
# which launches live_trader WITHOUT --use-queue and a script restarts.

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogFile = Join-Path $ProjectRoot "logs\queue_cutover.log"

function Write-Log($msg) {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
    Add-Content -Path $LogFile -Value "$stamp $msg" -Encoding utf8
    Write-Host "$stamp $msg"
}

Write-Log "=== queue cutover starting ==="

if (-not (Test-Path $Python)) {
    Write-Log "ABORT: python.exe not found at $Python"
    exit 2
}

# Load .env so PROJECTX_* + DISCORD_WEBHOOK_URL etc. are present
$envFile = Join-Path $ProjectRoot ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+)$') {
            $val = $Matches[2].Trim().Split('#')[0].Trim()
            [Environment]::SetEnvironmentVariable($Matches[1], $val, 'Process')
        }
    }
}
$env:PYTHONUTF8 = "1"
$env:PYTHONUNBUFFERED = "1"

# 1. Kill existing live_trader + brain_signaler processes
try {
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -match "scripts\.live_trader" -or
                       $_.CommandLine -match "scripts\.brain_signaler" }
    foreach ($p in $procs) {
        Write-Log "killing PID $($p.ProcessId) ($($p.CommandLine -replace '.*python\.exe[" ]+(-[uU])?',''))"
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds 3
} catch {
    Write-Log "process kill phase error (continuing): $_"
}

# 2. Start brain_signaler in REAL mode (emits actual signals)
$brainLog = Join-Path $ProjectRoot "logs\brain_signaler.log"
try {
    $brain = Start-Process -FilePath $Python `
        -ArgumentList @("-u", "-m", "scripts.brain_signaler") `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $brainLog `
        -RedirectStandardError ($brainLog + ".err") `
        -WindowStyle Hidden `
        -PassThru
    Write-Log "brain_signaler launched PID $($brain.Id)"
} catch {
    Write-Log "ERROR launching brain_signaler: $_"
    try {
        & $Python -m tools.alert "CRITICAL: Queue cutover FAILED — brain_signaler did not start. Manual intervention needed." --level=crit | Out-Null
    } catch { }
    exit 3
}

# 3. Start live_trader with --use-queue
$traderLog = Join-Path $ProjectRoot "logs\live_trader_queue.log"
try {
    $trader = Start-Process -FilePath $Python `
        -ArgumentList @("-u", "-m", "scripts.live_trader", "--use-queue") `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $traderLog `
        -RedirectStandardError ($traderLog + ".err") `
        -WindowStyle Hidden `
        -PassThru
    Write-Log "live_trader --use-queue launched PID $($trader.Id)"
} catch {
    Write-Log "ERROR launching live_trader: $_"
    try {
        & $Python -m tools.alert "CRITICAL: Queue cutover FAILED — live_trader did not start after brain. Manual intervention needed." --level=crit | Out-Null
    } catch { }
    exit 4
}

# 4. Verify both are alive after 10 seconds
Start-Sleep -Seconds 10
$brainAlive = Get-Process -Id $brain.Id -ErrorAction SilentlyContinue
$traderAlive = Get-Process -Id $trader.Id -ErrorAction SilentlyContinue
if (-not $brainAlive -or -not $traderAlive) {
    Write-Log "POST-LAUNCH CHECK FAILED: brain alive=$($null -ne $brainAlive) trader alive=$($null -ne $traderAlive)"
    try {
        & $Python -m tools.alert "CRITICAL: Queue cutover post-launch check FAILED. Check logs. Falling back to legacy trader via FundLiveTraderEnsureRunning." --level=crit | Out-Null
    } catch { }
    # Rollback: trigger the standard ensure-running task which runs WITHOUT --use-queue
    try { schtasks /Run /TN "FundLiveTraderEnsureRunning" | Out-Null } catch { }
    exit 5
}

Write-Log "cutover SUCCESS -- brain PID $($brain.Id), trader PID $($trader.Id)"
try {
    $alertMsg = "Queue cutover complete. brain_signaler PID $($brain.Id), live_trader queue mode PID $($trader.Id). Watch logs/live_trader_queue.log and logs/brain_signaler.log."
    & $Python -m tools.alert $alertMsg --level=info | Out-Null
} catch { }
exit 0
