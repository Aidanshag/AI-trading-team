# Activate idle-work mode. Agents will start pulling from
# vault/_meta/idle_backlog.md during their normal idle cycles.
#
# Use when: you're stepping away from active development and want the
# agents to keep expanding the brain autonomously.
#
# Usage:  .\scripts\idle-mode-on.ps1

$fundYaml = ".\config\fund.yaml"
$backlog  = ".\vault\_meta\idle_backlog.md"
$protocol = ".\vault\_meta\idle_protocol.md"

if (-not (Test-Path $fundYaml))  { Write-Host "Missing $fundYaml"  -ForegroundColor Red; exit 1 }
if (-not (Test-Path $backlog))   { Write-Host "Missing $backlog"   -ForegroundColor Red; exit 1 }
if (-not (Test-Path $protocol))  { Write-Host "Missing $protocol"  -ForegroundColor Red; exit 1 }

# Flip config flag
(Get-Content $fundYaml -Raw) -replace "idle_work_enabled:\s*false", "idle_work_enabled: true" |
    Out-File -FilePath $fundYaml -Encoding utf8 -NoNewline

# Flip backlog + protocol status to active
foreach ($p in @($backlog, $protocol)) {
    (Get-Content $p -Raw) -replace "status:\s*dormant", "status: active" |
        Out-File -FilePath $p -Encoding utf8 -NoNewline
}

Write-Host ""
Write-Host "Idle-work mode: ACTIVE" -ForegroundColor Green
Write-Host "Agents will start expanding the vault during idle cycles." -ForegroundColor Green
Write-Host ""
Write-Host "Run .\scripts\idle-mode-off.ps1 to stop." -ForegroundColor Cyan
