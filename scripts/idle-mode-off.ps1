# Deactivate idle-work mode. Agents stop pulling from the backlog and
# return to normal operating mode.
#
# Usage:  .\scripts\idle-mode-off.ps1

$fundYaml = ".\config\fund.yaml"
$backlog  = ".\vault\_meta\idle_backlog.md"
$protocol = ".\vault\_meta\idle_protocol.md"

(Get-Content $fundYaml -Raw) -replace "idle_work_enabled:\s*true", "idle_work_enabled: false" |
    Out-File -FilePath $fundYaml -Encoding utf8 -NoNewline

foreach ($p in @($backlog, $protocol)) {
    (Get-Content $p -Raw) -replace "status:\s*active", "status: dormant" |
        Out-File -FilePath $p -Encoding utf8 -NoNewline
}

Write-Host ""
Write-Host "Idle-work mode: DORMANT" -ForegroundColor Yellow
Write-Host "Agents will not pull from the backlog until reactivated." -ForegroundColor Yellow
