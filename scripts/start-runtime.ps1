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

# Launch detached. Output redirected so process is not tied to console.
$proc = Start-Process -FilePath $Python `
    -ArgumentList "-m", "runtime.main" `
    -WorkingDirectory $ProjectRoot `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -WindowStyle Hidden `
    -PassThru

Write-Host "Runtime launched. PID: $($proc.Id)" -ForegroundColor Green
Write-Host "  Stdout: $StdoutLog"
Write-Host "  Stderr: $StderrLog"
$proc.Id | Out-File (Join-Path $LogDir "runtime.pid")
