# Token-spend report.
# Usage:
#   .\scripts\cost.ps1              # today
#   .\scripts\cost.ps1 2026-04-22   # a specific day
param([string]$day = (Get-Date -Format "yyyy-MM-dd"))

& ".\.venv\Scripts\python.exe" -c @"
import sqlite3
c = sqlite3.connect(r'.\state\fund.db')
c.row_factory = sqlite3.Row
rows = c.execute('SELECT agent, model, tokens_in, tokens_out, cached_in, usd_est FROM costs WHERE day = ? ORDER BY usd_est DESC', ('$day',)).fetchall()
if not rows:
    print(f'No cost data for {chr(39)}$day{chr(39)}.')
else:
    total = 0.0
    print(f'{chr(34)}Day{chr(34):>10} = $day')
    print(f'{chr(34)}Agent{chr(34):<30}{chr(34)}Model{chr(34):<32}{chr(34)}In{chr(34):>10}{chr(34)}Out{chr(34):>10}{chr(34)}Cached{chr(34):>10}{chr(34)}USD{chr(34):>10}')
    for r in rows:
        total += r['usd_est']
        print(f'{r[chr(34)+chr(97)+chr(103)+chr(101)+chr(110)+chr(116)+chr(34)]:<30}{r[chr(34)+chr(109)+chr(111)+chr(100)+chr(101)+chr(108)+chr(34)]:<32}{r[chr(34)+chr(116)+chr(111)+chr(107)+chr(101)+chr(110)+chr(115)+chr(95)+chr(105)+chr(110)+chr(34)]:>10,}{r[chr(34)+chr(116)+chr(111)+chr(107)+chr(101)+chr(110)+chr(115)+chr(95)+chr(111)+chr(117)+chr(116)+chr(34)]:>10,}{r[chr(34)+chr(99)+chr(97)+chr(99)+chr(104)+chr(101)+chr(100)+chr(95)+chr(105)+chr(110)+chr(34)]:>10,}{r[chr(34)+chr(117)+chr(115)+chr(100)+chr(95)+chr(101)+chr(115)+chr(116)+chr(34)]:>10.4f}')
    print(f'{chr(34)}TOTAL{chr(34):<62}\${total:>9.4f}')
"@
