# Removes the autonomous fund Task Scheduler entries.

$ErrorActionPreference = "Continue"

Write-Host "Removing autonomous fund tasks..." -ForegroundColor Yellow
foreach ($name in "FundCIOMorningWake","FundRuntimeBoot") {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Host "  Removed $name" -ForegroundColor Green
    } else {
        Write-Host "  $name not present" -ForegroundColor DarkGray
    }
}
Write-Host "Done." -ForegroundColor Cyan
