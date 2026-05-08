# Preflight - check the fund can start.
# Run from project root:  .\scripts\verify.ps1

$ok = $true

function Ok   ($msg) { Write-Host ("[ OK   ] " + $msg) -ForegroundColor Green }
function Fail ($msg) { Write-Host ("[ FAIL ] " + $msg) -ForegroundColor Red; $script:ok = $false }
function Warn ($msg) { Write-Host ("[ WARN ] " + $msg) -ForegroundColor Yellow }

# 1. Python version
try {
    $pyv = (python --version) 2>&1
    if ($pyv -match "Python 3\.(1[1-9]|[2-9]\d)") { Ok "Python: $pyv" }
    else { Fail "Need Python 3.11+, got: $pyv" }
} catch { Fail "python not on PATH" }

# 2. venv exists
if (Test-Path ".\.venv\Scripts\python.exe") { Ok "venv present" }
else { Warn "No venv - create with: python -m venv .venv" }

# 3. .env present
if (Test-Path ".\.env") { Ok ".env present" }
else { Fail "Missing .env - copy .env.example and fill in" }

# 4. Critical env vars
if (Test-Path ".\.env") {
    $envText = Get-Content ".\.env" -Raw
    foreach ($key in @("ANTHROPIC_API_KEY", "FUND_MODE")) {
        if ($envText -match "(?m)^\s*$key\s*=\s*\S") { Ok ".env: $key set" }
        else { Fail ".env: $key missing or empty" }
    }
    if ($envText -match "(?m)^\s*PROJECTX_API_KEY\s*=\s*\S") { Ok ".env: PROJECTX_API_KEY set" }
    else { Warn ".env: PROJECTX_API_KEY not set (OK in stub phase)" }
}

# 5. DB initialized
if (Test-Path ".\state\fund.db") { Ok "state/fund.db exists" }
else { Warn "state/fund.db missing - run: python -m state.db init" }

# 6. Vault writable
try {
    $probe = ".\vault\_meta\.write_probe"
    "ok" | Out-File -FilePath $probe -Encoding utf8 -NoNewline
    Remove-Item $probe
    Ok "vault writable"
} catch { Fail "vault not writable: $_" }

# 7. Logs dir writable
if (-not (Test-Path ".\logs")) { New-Item -ItemType Directory ".\logs" | Out-Null }
try {
    $probe = ".\logs\.write_probe"
    "ok" | Out-File -FilePath $probe -Encoding utf8 -NoNewline
    Remove-Item $probe
    Ok "logs/ writable"
} catch { Fail "logs/ not writable: $_" }

# 8. Power settings - laptop sleep-never on AC?
$sleepAc = (powercfg /query SCHEME_CURRENT SUB_SLEEP STANDBYIDLE | Select-String "Current AC" | ForEach-Object { ($_ -split ":")[1].Trim() })
if ($sleepAc -eq "0x00000000") { Ok "Power: sleep-never on AC" }
else { Warn "Power: AC sleep is $sleepAc - disable for 24/5 running" }

# 9. Claude Agent SDK installed in venv
if (Test-Path ".\.venv\Scripts\python.exe") {
    $sdkCheck = & ".\.venv\Scripts\python.exe" -c "import claude_agent_sdk; print(claude_agent_sdk.__name__)" 2>&1
    if ($LASTEXITCODE -eq 0) { Ok "claude-agent-sdk installed" }
    else { Warn "claude-agent-sdk not installed - run: pip install -e ." }
}

# 10. Orchestrator can load agent specs
if (Test-Path ".\.venv\Scripts\python.exe") {
    $specs = & ".\.venv\Scripts\python.exe" -c "from runtime.orchestrator import Orchestrator; o = Orchestrator(); print(len(o.specs))" 2>&1
    if ($LASTEXITCODE -eq 0) { Ok "orchestrator loads $specs agent specs" }
    else { Fail "orchestrator instantiation failed: $specs" }
}

Write-Host ""
if ($ok) { Write-Host "Preflight PASSED." -ForegroundColor Green }
else     { Write-Host "Preflight FAILED - address items above." -ForegroundColor Red }
