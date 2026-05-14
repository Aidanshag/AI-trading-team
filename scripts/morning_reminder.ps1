# Morning reminder — fires Discord alert that the user's #1 priority
# (broker execution fix) is open and Claude needs to be invoked to work
# on it. Belt-and-suspenders alongside the autonomous Cloud routine.
# Created 2026-05-14 per user explicit direction "ensure this gets done."

$ErrorActionPreference = "Continue"
$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

# Load .env for DISCORD_WEBHOOK_URL
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

$msg = @"
URGENT MORNING REMINDER — execution fix is open. Invoke Claude and tell it: 'work on the morning investigation per vault/_meta/URGENT_MORNING_INVESTIGATION_2026-05-14.md'. Strategies validated overnight (10+ positive peaks) but execution layer was broken. P0 work: ProjectX type-code semantics + entry-fill anomaly. Nothing else gets done until this is fixed.
"@

try {
    & $Python -m tools.alert $msg --level=crit | Out-Null
    Write-Host "Morning reminder posted to Discord."
} catch {
    Write-Host "Discord post failed: $_" -ForegroundColor Red
}
