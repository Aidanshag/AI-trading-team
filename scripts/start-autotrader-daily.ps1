# Daily auto_trader launcher — invoked by the FundAutoTraderDaily scheduled task.
#
# 1. Loads .env into process env
# 2. Runs preflight; aborts if any check fails (canTrade=false, snapshot
#    pipeline broken, halt timestamp set, tests broken, etc.)
# 3. Launches auto_trader in a NEW visible PowerShell window so the user
#    can see live activity if they're at the keyboard
#
# The auto_trader itself respects:
#   - autonomous_restrictions.rth_only window (07:30-14:30 ET)
#   - regime_gates.thin_tape (21:00-04:00 ET)
#   - block_first_n_minutes_after_globex_reopen
# So it's safe to start before RTH; it'll wait quietly until the window opens.
#
# The PID lock (logs/auto_trader.pid) prevents duplicate instances if this
# script fires while a previous run is still alive.

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot | Split-Path -Parent
Set-Location $ProjectRoot

$Python  = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDir  = Join-Path $ProjectRoot "logs"
$LogFile = Join-Path $LogDir ("autotrader_" + (Get-Date -Format "yyyyMMdd") + ".log")

# Force Python's default file encoding to UTF-8. Without this, `read_text()`
# without an explicit encoding falls back to Windows cp1252 and crashes on
# any non-ASCII char in YAML configs (e.g. the em-dashes / arrows in
# config/fund.yaml comments). Caught 2026-05-01 when the auto_trader died on
# its first scan with UnicodeDecodeError at byte 391 of fund.yaml.
$env:PYTHONUTF8 = "1"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# Load .env
if (Test-Path ".\.env") {
    Get-Content ".\.env" | ForEach-Object {
        if ($_ -match "^\s*([A-Z_]+)\s*=\s*(.+)$") {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), "Process")
        }
    }
}

# Run preflight; abort on any failure
"$(Get-Date -Format o) preflight start" | Out-File $LogFile -Append -Encoding utf8
$preflight = & $Python -m scripts.preflight 2>&1
$preflight | Out-File $LogFile -Append -Encoding utf8
if ($LASTEXITCODE -ne 0) {
    "$(Get-Date -Format o) preflight FAILED — aborting auto_trader launch" | Out-File $LogFile -Append -Encoding utf8
    exit 1
}
"$(Get-Date -Format o) preflight OK — launching auto_trader" | Out-File $LogFile -Append -Encoding utf8

# Launch auto_trader in a new visible PowerShell window. The user can see it
# live if they're at the keyboard; otherwise it logs to autotrader_<date>.log
# via Tee-Object inside the spawned window.
$psCmd = @'
$Host.UI.RawUI.WindowTitle = 'Fund Auto-Trader (auto-started)'
Set-Location 'PROJECT_ROOT_PLACEHOLDER'
$env:PYTHONUTF8 = '1'
Get-Content '.env' | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), 'Process')
    }
}
& 'PYTHON_PATH_PLACEHOLDER' -m scripts.auto_trader --interval-minutes 5 2>&1 | Tee-Object -FilePath 'LOG_FILE_PLACEHOLDER' -Append
Read-Host 'Auto-trader exited. Press Enter to close this window'
'@
$psCmd = $psCmd.Replace('PROJECT_ROOT_PLACEHOLDER', $ProjectRoot)
$psCmd = $psCmd.Replace('PYTHON_PATH_PLACEHOLDER', $Python)
$psCmd = $psCmd.Replace('LOG_FILE_PLACEHOLDER', $LogFile)

$proc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoProfile", "-NoExit", "-Command", $psCmd `
    -WorkingDirectory $ProjectRoot `
    -PassThru
"$(Get-Date -Format o) auto_trader launched, PID $($proc.Id)" | Out-File $LogFile -Append -Encoding utf8
