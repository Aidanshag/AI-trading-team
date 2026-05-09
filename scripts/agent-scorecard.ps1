# Per-agent hit rate, avg R, and tier recommendation.
# Reads decisions + orders + risk_events from state DB.
# Usage:  .\scripts\agent-scorecard.ps1

$db = ".\state\fund.db"
if (-not (Test-Path $db)) {
    Write-Host "No DB at $db yet. Run: python -m state.db init" -ForegroundColor Yellow
    exit 1
}

& ".\.venv\Scripts\python.exe" -c @"
import sqlite3, json
c = sqlite3.connect(r'$db')
c.row_factory = sqlite3.Row

# Pull theses + their downstream orders per agent — simplified view.
q = '''
    SELECT agent,
           COUNT(*) AS decisions_made,
           SUM(CASE WHEN kind='thesis' THEN 1 ELSE 0 END) AS theses,
           SUM(CASE WHEN kind='shadow_trade' THEN 1 ELSE 0 END) AS shadow_trades,
           SUM(CASE WHEN kind='order_proposal' THEN 1 ELSE 0 END) AS proposals,
           SUM(CASE WHEN kind='risk_vote' THEN 1 ELSE 0 END) AS risk_votes
    FROM decisions
    GROUP BY agent
    ORDER BY decisions_made DESC
'''
rows = [dict(r) for r in c.execute(q).fetchall()]
if not rows:
    print('No decisions recorded yet. Scorecards will populate as agents run.')
else:
    print('Agent activity summary:')
    print(f'{chr(34)}Agent{chr(34):<35}Decisions  Theses  Shadow  Proposals  Risk votes')
    for r in rows:
        print(f'{r[chr(34)+chr(97)+chr(103)+chr(101)+chr(110)+chr(116)+chr(34)]:<35}{r[chr(34)+chr(100)+chr(101)+chr(99)+chr(105)+chr(115)+chr(105)+chr(111)+chr(110)+chr(115)+chr(95)+chr(109)+chr(97)+chr(100)+chr(101)+chr(34)]:>9}{r[chr(34)+chr(116)+chr(104)+chr(101)+chr(115)+chr(101)+chr(115)+chr(34)]:>8}{r[chr(34)+chr(115)+chr(104)+chr(97)+chr(100)+chr(111)+chr(119)+chr(95)+chr(116)+chr(114)+chr(97)+chr(100)+chr(101)+chr(115)+chr(34)]:>8}{r[chr(34)+chr(112)+chr(114)+chr(111)+chr(112)+chr(111)+chr(115)+chr(97)+chr(108)+chr(115)+chr(34)]:>11}{r[chr(34)+chr(114)+chr(105)+chr(115)+chr(107)+chr(95)+chr(118)+chr(111)+chr(116)+chr(101)+chr(115)+chr(34)]:>12}')

print()
print('For win-rate / avg-R / process-score, see vault/_meta/agent_scorecards.md — updated weekly by the CIO.')
"@
