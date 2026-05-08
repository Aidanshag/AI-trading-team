# Install the `fund` command into your PowerShell profile.
#
# After running this once, you can type `fund <verb>` from ANY PowerShell
# window without first cd'ing or loading credentials. Your profile loads
# automatically every time PowerShell starts.
#
# USAGE:
#   .\scripts\install-fund-shortcuts.ps1
#
# UNINSTALL: edit your profile (run `notepad $PROFILE`) and delete the
# block between "# >>> AI Trading fund alias" and "# <<< AI Trading fund alias".

$ErrorActionPreference = "Stop"

$ProjectRoot = "C:\Users\Owner\OneDrive\Personal AI\AI Trading"
$FundScript = Join-Path $ProjectRoot "scripts\fund.ps1"

if (-not (Test-Path $FundScript)) {
    Write-Host "ERROR: fund.ps1 not found at $FundScript" -ForegroundColor Red
    exit 1
}

# Make sure the profile file exists
if (-not (Test-Path $PROFILE)) {
    New-Item -Path $PROFILE -ItemType File -Force | Out-Null
    Write-Host "Created profile at: $PROFILE" -ForegroundColor DarkGray
}

# Marker tags so we can install / re-install / uninstall safely
$startTag = "# >>> AI Trading fund alias"
$endTag   = "# <<< AI Trading fund alias"

$existing = Get-Content $PROFILE -ErrorAction SilentlyContinue
$kept = @()
$inBlock = $false
foreach ($line in $existing) {
    if ($line -eq $startTag) { $inBlock = $true; continue }
    if ($line -eq $endTag)   { $inBlock = $false; continue }
    if (-not $inBlock) { $kept += $line }
}

# Build the new block
$block = @(
    $startTag,
    "# Adds the 'fund' command pointing at scripts/fund.ps1",
    "function fund {",
    "    & '$FundScript' @args",
    "}",
    $endTag
) -join "`r`n"

# Write it back: kept lines + new block
Set-Content -Path $PROFILE -Value (($kept -join "`r`n") + "`r`n`r`n" + $block + "`r`n") -Encoding UTF8

Write-Host ""
Write-Host "Installed `fund` alias." -ForegroundColor Green
Write-Host ""
Write-Host "Profile updated: $PROFILE" -ForegroundColor DarkGray
Write-Host ""
Write-Host "TO USE IT NOW (without restarting PowerShell):" -ForegroundColor Cyan
Write-Host "  . `$PROFILE" -ForegroundColor White
Write-Host ""
Write-Host "Then try:" -ForegroundColor Cyan
Write-Host "  fund help" -ForegroundColor White
Write-Host "  fund status" -ForegroundColor White
Write-Host ""
Write-Host "Future PowerShell windows will load `fund` automatically." -ForegroundColor DarkGray
