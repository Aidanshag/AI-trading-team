# Installs the FundMacroBriefDaily Windows scheduled task.
#
# Schedule:
#   Mon-Fri at 06:00 local time — 30 min before the auto_trader's daily
#   start (06:30 via FundAutoTraderDaily). The brief lands in
#   vault/_meta/macro_brief_<date>.md and any agent that reads
#   vault/_meta/ on wake (CIO, Risk Manager, analysts) picks it up.
#
# What it runs:
#   python -m scripts.generate_macro_brief --refresh
#   This calls all three fetchers (FRED, TreasuryDirect, federalreserve.gov)
#   then composes the brief.
#
# Idempotent: re-running this script overwrites cleanly. Failures roll
# back to the previous task definition (same pattern as
# install-autotrader-daily.ps1).
#
# Usage (admin PowerShell):
#   & "C:\Users\Owner\OneDrive\Personal AI\AI Trading\scripts\install-macro-brief-daily.ps1"
#
# Test now (after install):
#   Start-ScheduledTask -TaskName FundMacroBriefDaily
#   # then check vault/_meta/macro_brief_<today>.md

$ErrorActionPreference = "Stop"

# Resolve project root from this script's location, not Get-Location.
# Admin PowerShell opens in C:\Windows\System32; using Get-Location would
# look for the launcher there. $PSScriptRoot is always this script's folder.
$ProjectRoot = $PSScriptRoot | Split-Path -Parent
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$BriefScript = Join-Path $ProjectRoot "scripts\generate_macro_brief.py"

if (-not (Test-Path $Python)) {
    Write-Host "  WARN: python.exe missing at $Python" -ForegroundColor Yellow
    Write-Host "        Brief task will fail until .venv exists." -ForegroundColor Yellow
}
if (-not (Test-Path $BriefScript)) {
    throw "Brief generator not found at $BriefScript"
}

Write-Host ""
Write-Host "=== Installing FundMacroBriefDaily ===" -ForegroundColor Cyan
Write-Host ""

$TaskName = "FundMacroBriefDaily"
$TaskDescription = "Daily macro brief: 06:00 Mon-Fri. Runs scripts.generate_macro_brief --refresh which pulls FRED levels, Treasury auctions, Fed speakers, then composes vault/_meta/macro_brief_<date>.md for the agent chain to read on wake."

# 5-min limit: the three fetchers each timeout at 30s; full pipeline
# typically completes in 10-20s. 5 min is generous safety.
$settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

# Run as the user (no admin needed for the fetchers; they only write
# to vault/ and call public HTTPS endpoints).
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:USERNAME `
    -LogonType Interactive `
    -RunLevel Limited

# Single trigger: weekdays 06:00 local. 30 min before FundAutoTraderDaily
# (06:30) so the brief is fresh when the trader starts.
$trigger = New-ScheduledTaskTrigger `
    -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday `
    -At "6:00AM"

# Direct python invocation; no nested powershell quoting needed.
# PYTHONUTF8=1 mirrors what the trader uses (see launcher: 'force PYTHONUTF8=1
# so YAML loads survive cp1252 default').
$action = New-ScheduledTaskAction `
    -Execute $Python `
    -Argument "-m scripts.generate_macro_brief --refresh" `
    -WorkingDirectory $ProjectRoot

# Backup + register-with-rollback (same pattern as install-autotrader-daily.ps1).
# 2026-05-04 incident: previous-style Unregister-then-Register left users
# with NO task if Register failed mid-flow. Use Register -Force atomic
# overwrite + restore from backup XML on failure.
$backupXml = $null
$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existing) {
    try {
        $backupXml = Export-ScheduledTask -TaskName $TaskName
        Write-Host "  existing task backed up for rollback" -ForegroundColor DarkGray
    } catch {
        Write-Host ("  warn: backup failed: " + $_.Exception.Message) -ForegroundColor Yellow
    }
}

try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $TaskDescription `
        -Trigger $trigger `
        -Action $action `
        -Settings $settings `
        -Principal $principal `
        -Force `
        -ErrorAction Stop | Out-Null
    Write-Host "  registered: Mon-Fri 06:00 local" -ForegroundColor Green
} catch {
    $errMsg = $_.Exception.Message
    Write-Host ("  FAILED to register: " + $errMsg) -ForegroundColor Red

    $stillThere = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $stillThere -and $backupXml) {
        Write-Host "  ROLLING BACK to previous task definition..." -ForegroundColor Yellow
        try {
            Register-ScheduledTask -TaskName $TaskName -Xml $backupXml -ErrorAction Stop | Out-Null
            Write-Host "  rollback OK" -ForegroundColor Green
        } catch {
            Write-Host ("  ROLLBACK ALSO FAILED: " + $_.Exception.Message) -ForegroundColor Red
            Write-Host "  Task is now MISSING. Re-run from an elevated shell to recover." -ForegroundColor Red
        }
    } elseif (-not $stillThere) {
        Write-Host "  No prior task to roll back to. Re-run from an elevated shell." -ForegroundColor Red
    } else {
        Write-Host "  Existing task is still present and untouched." -ForegroundColor Green
    }

    $accessDenied = ($errMsg -like '*Access is denied*') -or ($errMsg -like '*0x80070005*')
    if ($accessDenied) {
        Write-Host ""
        Write-Host "  CAUSE: this PowerShell window is not running as Administrator." -ForegroundColor Yellow
        Write-Host "  FIX:   right-click PowerShell -> Run as administrator, then re-run this script." -ForegroundColor Yellow
    }
    throw
}

Write-Host ""
Write-Host "=== FundMacroBriefDaily registered ===" -ForegroundColor Green

# Show registered task
Write-Host ""
Get-ScheduledTask | Where-Object { $_.TaskName -eq $TaskName } |
    Format-Table TaskName, State,
                 @{Label="Triggers";Expression={$_.Triggers.Count}},
                 @{Label="NextRun";Expression={(Get-ScheduledTaskInfo -TaskName $_.TaskName).NextRunTime}} `
    -AutoSize

Write-Host ""
Write-Host "Test now:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask -TaskName FundMacroBriefDaily"
Write-Host "  # Then check vault/_meta/macro_brief_<today>.md"
Write-Host ""
Write-Host "Run manually anytime:" -ForegroundColor Cyan
Write-Host "  python -m scripts.generate_macro_brief --refresh"
Write-Host ""
Write-Host "View latest brief:" -ForegroundColor Cyan
Write-Host "  Get-Content `"$ProjectRoot\vault\_meta\macro_brief_$(Get-Date -Format yyyy-MM-dd).md`""
