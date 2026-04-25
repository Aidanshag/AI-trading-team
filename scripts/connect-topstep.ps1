# Connect the fund to your Topstep Combine account.
# Walks you through authentication and account discovery.
# Run from project root:  .\scripts\connect-topstep.ps1

Write-Host ""
Write-Host "=== Topstep / ProjectX connection wizard ===" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".\.env")) {
    Write-Host "[FAIL] .env does not exist. Run:  Copy-Item .env.example .env" -ForegroundColor Red
    exit 1
}

# Load .env into process env so the Python client can read it
Get-Content ".\.env" | ForEach-Object {
    if ($_ -match "^\s*([A-Z_]+)\s*=\s*(.+)$") {
        $k = $Matches[1]
        $v = $Matches[2].Trim()
        if ($v) { [Environment]::SetEnvironmentVariable($k, $v, "Process") }
    }
}

if (-not $env:PROJECTX_USERNAME) {
    Write-Host "[FAIL] PROJECTX_USERNAME not set in .env" -ForegroundColor Red
    exit 1
}

$hasKey = [bool]$env:PROJECTX_API_KEY
$hasApp = ([bool]$env:PROJECTX_APP_ID) -and ([bool]$env:PROJECTX_VERIFY_KEY) -and ([bool]$env:PROJECTX_PASSWORD) -and ([bool]$env:PROJECTX_DEVICE_ID)

if (-not $hasKey -and -not $hasApp) {
    Write-Host "[FAIL] No auth credentials in .env." -ForegroundColor Red
    Write-Host "  Set EITHER:"
    Write-Host "    PROJECTX_API_KEY  (key flow)"
    Write-Host "  OR:"
    Write-Host "    PROJECTX_PASSWORD, PROJECTX_DEVICE_ID, PROJECTX_APP_ID, PROJECTX_VERIFY_KEY  (app flow)"
    exit 1
}

Write-Host "[ OK ] Credentials present in .env" -ForegroundColor Green
Write-Host "Authenticating against ProjectX..." -ForegroundColor Cyan

$pyOut = & ".\.venv\Scripts\python.exe" ".\scripts\_connect_topstep_probe.py" 2>&1
$joined = ($pyOut | Out-String)

if ($joined -match "AUTH_OK") {
    Write-Host "[ OK ] Authenticated." -ForegroundColor Green
    Write-Host ""
    Write-Host "Your accounts:" -ForegroundColor Cyan
    $jsonLine = ($pyOut | Where-Object { $_ -match "^ACCOUNTS_JSON::" }) -replace "^ACCOUNTS_JSON::", ""
    try {
        $accounts = $jsonLine | ConvertFrom-Json
        foreach ($a in $accounts) {
            $id = $a.id
            $name = $a.name
            $bal = $a.balance
            Write-Host ("  id={0}   name={1}   balance=`${2}" -f $id, $name, $bal)
        }
        Write-Host ""
        Write-Host "Next step:" -ForegroundColor Cyan
        Write-Host "  Edit .env and set PROJECTX_ACCOUNT_ID=<the id above>"
        Write-Host "  Then run:  .\scripts\verify.ps1"
    } catch {
        Write-Host "(Could not parse account JSON. Raw output:)"
        Write-Host $joined
    }
} else {
    Write-Host "[FAIL] Authentication did not succeed." -ForegroundColor Red
    Write-Host ""
    Write-Host $joined
    Write-Host ""
    Write-Host "Common fixes:"
    Write-Host "  - PROJECTX_USERNAME should be your TopstepX login (email or handle),"
    Write-Host "    not a token/hash."
    Write-Host "  - Regenerate API key at the ProjectX dashboard."
    Write-Host "  - Check for typos; no quotes around values in .env."
}
