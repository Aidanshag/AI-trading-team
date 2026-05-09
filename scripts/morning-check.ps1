# One-command morning preflight before the trading session.
# Usage:  .\scripts\morning-check.ps1
#
# Verifies:
#   1. Trading halt timestamp + time-to-expiry
#   2. Topstep account state (balance, can-trade, positions, working orders)
#   3. Test suite (116/116 should pass)
#   4. Today's calendar of agent-relevant events
#   5. API spend so far today + all-time

Write-Host ""
Write-Host "=== Morning Preflight ===" -ForegroundColor Cyan
Write-Host ""

# Load .env
if (-not (Test-Path ".\.env")) {
    Write-Host "[FAIL] No .env present" -ForegroundColor Red
    exit 1
}
Get-Content ".\.env" | ForEach-Object {
    if ($_ -match "^\s*([A-Z_]+)\s*=\s*(.+)$") {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), "Process")
    }
}

# 1. Halt timestamp + account state via Python (uses live ProjectX auth)
Write-Host "Step 1/4: Halt + account state" -ForegroundColor Yellow
Write-Host ("-" * 60)
& ".\.venv\Scripts\python.exe" -c @'
import os, sys, yaml, httpx
from datetime import datetime, timezone
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

cfg = yaml.safe_load(Path('config/risk_limits.yaml').read_text())
hu = cfg['hard_rules'].get('trading_halt_until')
now = datetime.now(tz=timezone.utc)
if hu:
    parsed = datetime.fromisoformat(str(hu).replace('Z', '+00:00'))
    delta = (parsed - now).total_seconds() / 3600
    if now < parsed:
        print(f'  Halt active. Expires in {delta:+.1f} hours: {hu}')
    else:
        print(f'  Halt EXPIRED {-delta:.1f} hours ago — trading allowed.')
else:
    print('  Halt: not set (trading allowed).')

api = os.environ.get('PROJECTX_API_KEY','')
user = os.environ.get('PROJECTX_USERNAME','')
acct_id = int(os.environ.get('PROJECTX_ACCOUNT_ID','0'))
if not (api and user and acct_id):
    print('  [WARN] ProjectX env vars missing; skipping account check')
else:
    r = httpx.post('https://api.topstepx.com/api/Auth/loginKey',
                   json={'userName':user,'apiKey':api}, timeout=15)
    t = r.json().get('token')
    if not t:
        print(f'  [FAIL] auth: {r.json()}')
    else:
        H = {'Authorization': f'Bearer {t}'}
        r = httpx.post('https://api.topstepx.com/api/Account/search', headers=H,
                       json={'onlyActiveAccounts': True}, timeout=15)
        acct = next((a for a in r.json().get('accounts',[]) if a.get('id')==acct_id), None)
        if acct:
            print(f"  Account: {acct.get('name')}")
            print(f"  Balance: ${acct.get('balance',0):,.2f}  canTrade: {acct.get('canTrade')}")
        r = httpx.post('https://api.topstepx.com/api/Position/searchOpen', headers=H,
                       json={'accountId': acct_id}, timeout=15)
        n_pos = len(r.json().get('positions',[]))
        r = httpx.post('https://api.topstepx.com/api/Order/searchOpen', headers=H,
                       json={'accountId': acct_id}, timeout=15)
        n_ord = len(r.json().get('orders',[]))
        print(f'  Open positions: {n_pos}  Working orders: {n_ord}')
'@
Write-Host ""

# 2. Test suite
Write-Host "Step 2/4: Test suite" -ForegroundColor Yellow
Write-Host ("-" * 60)
& ".\.venv\Scripts\python.exe" -m pytest tests/ -q --tb=no | Select-Object -Last 3
Write-Host ""

# 3. Spend
Write-Host "Step 3/4: API spend" -ForegroundColor Yellow
Write-Host ("-" * 60)
& ".\.venv\Scripts\python.exe" -c @'
import sqlite3, sys
from datetime import datetime, timezone
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
c = sqlite3.connect('state/fund.db')
today = datetime.now(tz=timezone.utc).strftime('%Y-%m-%d')
t = c.execute("SELECT COALESCE(SUM(usd_est),0) FROM costs WHERE day=?",(today,)).fetchone()[0]
m = c.execute("SELECT COALESCE(SUM(usd_est),0) FROM costs WHERE day LIKE ?",(today[:7]+'%',)).fetchone()[0]
a = c.execute('SELECT COALESCE(SUM(usd_est),0) FROM costs').fetchone()[0]
print(f'  Today:    ${t:.2f}')
print(f'  MTD:      ${m:.2f}')
print(f'  All-time: ${a:.2f}')
'@
Write-Host ""

# 4. Agent count
Write-Host "Step 4/4: Agent registry" -ForegroundColor Yellow
Write-Host ("-" * 60)
& ".\.venv\Scripts\python.exe" -c @'
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from pathlib import Path
for line in Path('.env').read_text().splitlines():
    if '=' in line and not line.strip().startswith('#'):
        k,_,v = line.partition('='); os.environ.setdefault(k.strip(), v.strip())
from runtime.orchestrator import Orchestrator
o = Orchestrator()
print(f'  Total agents: {len(o.specs)}')
print(f'  MCP servers:  {len(o.mcp_servers)}')
'@
Write-Host ""

Write-Host "=== Preflight complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "If halt has expired and balance/canTrade look right, you're cleared to start the session."
Write-Host "Say 'start session' to Claude to wake CIO."
