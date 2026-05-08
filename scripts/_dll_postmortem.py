"""One-shot post-mortem helper. Pulls broker order history + DB state."""
import httpx, json, os, sqlite3
from datetime import datetime, timezone, timedelta

api = os.environ['PROJECTX_API_KEY']
user = os.environ['PROJECTX_USERNAME']
aid = int(os.environ['PROJECTX_ACCOUNT_ID'])

r = httpx.post('https://api.topstepx.com/api/Auth/loginKey',
               json={'userName': user, 'apiKey': api}, timeout=15)
t = r.json()['token']
H = {'Authorization': f'Bearer {t}'}
start = (datetime.now(tz=timezone.utc) - timedelta(hours=24)).isoformat(timespec='seconds')
hist = httpx.post(
    'https://api.topstepx.com/api/Order/search',
    headers=H, json={'accountId': aid, 'startTimestamp': start}, timeout=15
).json().get('orders', [])

print(f'=== ORDERS LAST 24H: {len(hist)} ===')
type_map = {1: 'mkt', 2: 'lmt', 3: 'stp', 4: 'stp_lmt', 5: 'trail'}
side_map = {0: 'BUY', 1: 'SELL'}
status_map = {1: 'open', 2: 'filled', 3: 'cancelled', 4: 'expired', 5: 'rejected', 6: 'pending'}

for o in sorted(hist, key=lambda x: x.get('updateTimestamp') or x.get('creationTimestamp', '')):
    ts = o.get('updateTimestamp') or o.get('creationTimestamp')
    cid = o.get('contractId', '?')
    cid_short = '.'.join(cid.split('.')[-2:]) if '.' in cid else cid
    typ = type_map.get(o.get('type'), o.get('type'))
    side = side_map.get(o.get('side'), o.get('side'))
    status = status_map.get(o.get('status'), o.get('status'))
    qty = o.get('size')
    fp = o.get('fillVolume') or o.get('filledQty') or 0
    fill_px = o.get('filledPrice') or o.get('avgPrice')
    stop = o.get('stopPrice')
    limit = o.get('limitPrice')
    print(f'{ts} | {typ:<7} {side:<4} qty={qty} fill={fp} status={status:<9} {cid_short:<10} fillPx={fill_px} stop={stop} limit={limit}')

print()
print('=== DB DECISIONS LAST 24H ===')
c = sqlite3.connect('state/fund.db')
c.row_factory = sqlite3.Row
since = (datetime.now(tz=timezone.utc) - timedelta(hours=24)).isoformat(timespec='seconds')
for r in c.execute("SELECT ts, agent, kind, symbol, summary FROM decisions WHERE ts >= ? ORDER BY ts", (since,)):
    print(f'{r["ts"]} | {r["agent"]:<22} | {r["kind"]:<25} | {r["symbol"] or "":<5} | {r["summary"][:80]}')

print()
print('=== RISK EVENTS LAST 24H ===')
for r in c.execute("SELECT ts, severity, rule, agent FROM risk_events WHERE ts >= ? ORDER BY ts", (since,)):
    print(f'{r["ts"]} | {r["severity"]:<6} | {r["rule"]:<30} | {r["agent"]}')
