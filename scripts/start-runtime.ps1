# Launches runtime/main.py as a detached background Python process.
# Triggered by FundRuntimeBoot scheduled task (or manually).
#
# The runtime contains the scheduler that emits SESSION_OPEN, TICK,
# SESSION_CLOSE events on Globex hours. CIO + analyst chain run
# automatically on those events when autonomous_mode: true.
#
# Logs:
#   logs/runtime_stdout.log
#   logs/runtime_stderr.log
#
# To check status:    Get-Process python -ErrorAction SilentlyContinue
# To stop:            scripts/stop-runtime.ps1

$ErrorActionPreference = "Stop"

$ProjectRoot = $PSScriptRoot | Split-Path -Parent
Set-Location $ProjectRoot

$Python    = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$LogDir    = Join-Path $ProjectRoot "logs"
$StdoutLog = Join-Path $LogDir "runtime_stdout.log"
$StderrLog = Join-Path $LogDir "runtime_stderr.log"

if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

# Load .env into process env BEFORE launching the child
Get-Content (Join-Path $ProjectRoot ".env") | ForEach-Object {
    if ($_ -match "^\s*([A-Z_]+)\s*=\s*(.+)$") {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), "Process")
    }
}

# Check if already running
$existing = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -eq $Python
}
if ($existing) {
    Write-Host "Runtime already running (PID $($existing.Id))" -ForegroundColor Yellow
    exit 0
}

# Launch in a NEW visible PowerShell window with full console handles.
# Background detached launch (Start-Process -RedirectStandardOutput
# -WindowStyle Hidden) broke the Claude Agent SDK's anyio.open_process
# call - the SDK could not fork the claude.exe subprocess and every wake
# failed with FileNotFoundError. Solution: give python a real console.
#
# Tee-Object writes to both the screen and the log file so you can:
#   (a) watch live activity in the runtime window
#   (b) review logs/runtime_stdout.log later
#
# To stop: close the runtime window, or run scripts/stop-runtime.ps1.
$psCmd = @'
$Host.UI.RawUI.WindowTitle = 'Fund Runtime - LIVE'
Set-Location 'PROJECT_ROOT_PLACEHOLDER'
Get-Content '.env' | ForEach-Object {
    if ($_ -match '^\s*([A-Z_]+)\s*=\s*(.+)$') {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), 'Process')
    }
}
& 'PYTHON_PATH_PLACEHOLDER' -m runtime.main 2>&1 | Tee-Object -FilePath 'STDOUT_LOG_PLACEHOLDER' -Append
Read-Host 'Runtime exited. Press Enter to close this window'
'@
$psCmd = $psCmd.Replace('PROJECT_ROOT_PLACEHOLDER', $ProjectRoot)
$psCmd = $psCmd.Replace('PYTHON_PATH_PLACEHOLDER', $Python)
$psCmd = $psCmd.Replace('STDOUT_LOG_PLACEHOLDER', $StdoutLog)

$proc = Start-Process -FilePath "powershell.exe" `
    -ArgumentList "-NoProfile", "-NoExit", "-Command", $psCmd `
    -WorkingDirectory $ProjectRoot `
    -PassThru

Write-Host "Runtime launched in new window. PID: $($proc.Id)" -ForegroundColor Green
Write-Host "  A 'Fund Runtime - LIVE' window is now open showing live activity."
Write-Host "  Logs also tee'd to: $StdoutLog"
Write-Host "  To stop: close that window, or run scripts/stop-runtime.ps1"
$proc.Id | Out-File (Join-Path $LogDir "runtime.pid")
