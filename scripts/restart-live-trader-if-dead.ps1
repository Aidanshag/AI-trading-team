# Restart live_trader if it's not currently running.
#
# Fired by FundLiveTraderMonMorning scheduled task at Mon-Fri 06:30 ET.
# Idempotent: if live_trader is already alive (e.g. Sunday kickstart is still
# running cleanly), this script logs "alive, no action" and exits without
# launching a duplicate. live_trader has no PID lock, so the duplicate check
# is done here via process-table scan for the `scripts.live_trader` command.

$ErrorActionPreference = "Stop"

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogFile = Join-Path $ProjectRoot "logs\livetrader_morning_restart.log"
$StdoutLog = Join-Path $ProjectRoot "logs\livetrader_morning_stdout.log"
$StderrLog = Join-Path $ProjectRoot "logs\livetrader_morning_stderr.log"

function Write-Log($msg) {
    $stamp = Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz"
    Add-Content -Path $LogFile -Value "$stamp $msg" -Encoding utf8
}

if (-not (Test-Path $Python)) {
    Write-Log "ABORT: python.exe not found at $Python"
    exit 2
}

# Check whether live_trader is already running. Scan python.exe process
# command lines for the `scripts.live_trader` module string.
$alreadyRunning = $false
$runningPid = $null
try {
    $procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue
    foreach ($p in $procs) {
        if ($p.CommandLine -and $p.CommandLine -match "scripts\.live_trader") {
            $alreadyRunning = $true
            $runningPid = $p.ProcessId
            break
        }
    }
} catch {
    Write-Log "process-check error: $_; proceeding with launch attempt"
}

if ($alreadyRunning) {
    Write-Log "live_trader already running (PID $runningPid) -- no action"
    exit 0
}

Write-Log "live_trader NOT running -- launching"

# Detached launch via Start-Process. The scheduled-task powershell will exit
# after this call; the python process keeps running independently.
try {
    $proc = Start-Process -FilePath $Python `
        -ArgumentList "-m", "scripts.live_trader" `
        -WorkingDirectory $ProjectRoot `
        -RedirectStandardOutput $StdoutLog `
        -RedirectStandardError $StderrLog `
        -WindowStyle Hidden `
        -PassThru
    Write-Log "launched live_trader, PID $($proc.Id)"
    # Alert: a launch happening here means the trader was NOT running, which
    # is evidence of a prior crash or clean shutdown we didn't intend.
    try {
        & $Python -m tools.alert "Trader was not running -- launched new instance (PID $($proc.Id)). Check logs for prior shutdown reason." --level=warn | Out-Null
        Write-Log "alert dispatched"
    } catch {
        Write-Log "alert dispatch FAILED: $_"
    }
    exit 0
} catch {
    Write-Log "LAUNCH FAILED: $_"
    try {
        & $Python -m tools.alert "CRITICAL: morning restart task tried to launch live_trader but Start-Process FAILED. Trader is DOWN. Manual intervention required." --level=crit | Out-Null
    } catch { }
    exit 3
}
