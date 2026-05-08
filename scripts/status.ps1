# Fund status dashboard.
# Run from project root:  .\scripts\status.ps1

$db = ".\state\fund.db"
if (-not (Test-Path $db)) {
    Write-Host "No DB at $db yet. Run: python -m state.db init" -ForegroundColor Yellow
    exit 1
}

function Q($sql) {
    & ".\.venv\Scripts\python.exe" -c @"
import sqlite3, json, sys
c = sqlite3.connect(r'$db')
c.row_factory = sqlite3.Row
rows = [dict(r) for r in c.execute('''$sql''').fetchall()]
print(json.dumps(rows, default=str, indent=2))
"@
}

Write-Host ""
Write-Host "=== Fund status  ===" -ForegroundColor Cyan
Write-Host ""

Write-Host "-- Latest account snapshot --" -ForegroundColor Yellow
Q "SELECT * FROM account_snapshots ORDER BY ts DESC LIMIT 1"

Write-Host ""
Write-Host "-- Open positions --" -ForegroundColor Yellow
Q "SELECT symbol, side, contracts, avg_price, stop_price, target_price FROM positions"

Write-Host ""
Write-Host "-- Working orders --" -ForegroundColor Yellow
Q "SELECT id, agent, symbol, side, qty, order_type, status FROM orders WHERE status IN ('proposed','submitted') ORDER BY id DESC LIMIT 20"

Write-Host ""
Write-Host "-- Today's risk events --" -ForegroundColor Yellow
Q "SELECT ts, severity, rule, agent FROM risk_events WHERE ts LIKE date('now')||'%' ORDER BY ts DESC LIMIT 30"

Write-Host ""
Write-Host "-- Today's token spend --" -ForegroundColor Yellow
Q "SELECT agent, model, tokens_in, tokens_out, ROUND(usd_est,4) AS usd FROM costs WHERE day = date('now') ORDER BY usd_est DESC"

Write-Host ""
Write-Host "-- Last 10 decisions --" -ForegroundColor Yellow
Q "SELECT ts, agent, kind, symbol, summary FROM decisions ORDER BY ts DESC LIMIT 10"
