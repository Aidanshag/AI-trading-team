"""Quick status check — broker positions, working orders, recent fund activity.

Run from PowerShell:
    .\.venv\Scripts\python.exe -m scripts.check_status

Shows:
  - Live Topstep account state (balance, positions, working orders)
  - Recent auto_trader activity from the local DB (orders, theses, blocks)

No order placement, no Claude API calls. Read-only safe to run anytime.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Pin cwd + load .env so credentials are present regardless of how invoked
HERE = Path(__file__).resolve().parent.parent
os.chdir(HERE)
from dotenv import load_dotenv
load_dotenv()

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from state.db import get_db

ET = ZoneInfo("America/New_York")


def to_et(ts_str: str) -> str:
    """Convert ISO-8601 UTC timestamp to a friendly ET string.
    Returns 'HH:MM:SS ET' for compact display in tables."""
    if not ts_str:
        return ""
    try:
        # Handle both 'Z' suffix and explicit +00:00 offset
        s = ts_str.replace("Z", "+00:00")
        dt_utc = datetime.fromisoformat(s)
        if dt_utc.tzinfo is None:
            dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        return dt_utc.astimezone(ET).strftime("%H:%M:%S ET")
    except Exception:
        return ts_str


def main() -> int:
    db = get_db()
    now = datetime.now(tz=timezone.utc)
    since = (now - timedelta(hours=2)).isoformat(timespec="seconds")

    # ── Broker side: live state from Topstep ─────────────────
    print("=" * 60)
    print("BROKER STATE (live from Topstep)")
    print("=" * 60)
    try:
        from tools.projectx_client import get_account_id, get_client
        client = get_client()
        aid = get_account_id()

        accts = client.get_accounts()
        for a in accts:
            if str(a.get("id")) == str(aid):
                print(f"  Account: {a.get('name', 'unknown')}")
                print(f"  Balance: ${a.get('balance', 0):,.2f}")
                print(f"  Can trade: {a.get('canTrade')}")
                print(f"  Simulated: {a.get('simulated')}")
                break

        positions = client.get_positions(aid)
        print(f"\n  Open positions: {len(positions)}")
        for p in positions:
            side = "LONG" if int(p.get("type", 0)) == 1 else "SHORT"
            print(f"    {p.get('contractId', '?'):30s} {side:5s} "
                  f"size={p.get('size')} avg={p.get('averagePrice') or p.get('avgPrice')}")

        orders = client.get_working_orders(aid)
        print(f"\n  Working orders: {len(orders)}")
        for o in orders:
            side = "BUY" if int(o.get("side", 0)) == 0 else "SELL"
            otype = {1: "MKT", 2: "LMT", 3: "STP", 4: "STP-LMT"}.get(
                int(o.get("type", 0)), str(o.get("type")))
            print(f"    oid={o.get('id')} {o.get('contractId', '?'):30s} "
                  f"{side:4s} {otype:8s} qty={o.get('size')} "
                  f"stop={o.get('stopPrice')} lmt={o.get('limitPrice')}")
    except Exception as e:
        print(f"  ERROR fetching broker state: {type(e).__name__}: {e}")

    # ── Local DB side: auto_trader activity ──────────────────
    print()
    print("=" * 60)
    print("AUTO_TRADER ACTIVITY (last 2h, from local DB)")
    print("=" * 60)

    orders = db.connect().execute(
        "SELECT ts_proposed, symbol, side, order_type, qty, status, "
        "broker_order_id, risk_reason FROM orders "
        "WHERE agent='auto_trader' AND ts_proposed >= ? "
        "ORDER BY id DESC LIMIT 20",
        (since,),
    ).fetchall()
    print(f"\n  Orders in last 2h: {len(orders)}")
    for o in orders:
        line = (f"    {to_et(o['ts_proposed']):13s} {o['symbol']:5s} "
                f"{o['side']:4s} {o['order_type']:9s} qty={o['qty']} "
                f"status={o['status']} broker={o['broker_order_id'] or '-'}")
        print(line)
        if o["risk_reason"]:
            print(f"      reason: {o['risk_reason'][:100]}")

    theses = db.connect().execute(
        "SELECT ts, symbol, summary FROM decisions "
        "WHERE agent='auto_trader' AND kind='thesis' AND ts >= ? "
        "ORDER BY ts DESC LIMIT 10",
        (since,),
    ).fetchall()
    print(f"\n  Triggers found: {len(theses)}")
    for t in theses:
        print(f"    {to_et(t['ts']):13s} {t['symbol']:5s} {t['summary'][:80]}")

    blocks = db.connect().execute(
        "SELECT ts, rule, detail FROM risk_events "
        "WHERE agent='auto_trader' AND severity='block' AND ts >= ? "
        "ORDER BY ts DESC LIMIT 10",
        (since,),
    ).fetchall()
    print(f"\n  Blocked attempts: {len(blocks)}")
    for b in blocks:
        print(f"    {to_et(b['ts']):13s} {b['rule']:25s} {(b['detail'] or '')[:60]}")

    # ── Fee accounting (added 2026-04-29) ─────────────────
    # Estimate session fees from recorded fills. Highlights when fee
    # bleed is dwarfing strategy edge — a critical signal to slow down.
    print()
    print("=" * 60)
    print("FEE ACCOUNTING (estimated, this session)")
    print("=" * 60)
    try:
        import yaml
        cfg = yaml.safe_load(open("config/risk_limits.yaml", encoding="utf-8")) or {}
        fees_table = cfg.get("fees_round_trip_usd", {}) or {}
        # Count DB orders with broker_order_id (those that actually hit broker)
        rows = db.connect().execute(
            "SELECT symbol, COUNT(*) FROM orders "
            "WHERE agent='auto_trader' AND broker_order_id IS NOT NULL "
            "AND DATE(ts_proposed) = DATE('now') "
            "GROUP BY symbol"
        ).fetchall()
        # Each fill is half a round trip (entry OR exit), so divide fee by 2
        total_fee_est = 0.0
        for r in rows:
            sym = r["symbol"]
            n_fills = int(r[1])
            rt_fee = float(fees_table.get(sym, fees_table.get("default", 5.0)))
            est = n_fills * (rt_fee / 2.0)
            total_fee_est += est
            print(f"  {sym:5s}: {n_fills:3d} fills × ${rt_fee/2:.2f}/side = ${est:.2f}")
        print(f"  {'TOTAL':5s}: ~${total_fee_est:.2f} estimated fees today")
    except Exception as e:
        print(f"  (fee tally failed: {e})")

    # ── Account snapshot ──────────────────────────────────
    snap = db.latest_account_snapshot()
    print()
    print("=" * 60)
    print("LATEST ACCOUNT SNAPSHOT (DB)")
    print("=" * 60)
    if snap:
        print(f"  ts: {to_et(snap['ts'])} (UTC: {snap['ts']})")
        print(f"  balance: ${snap['balance_usd']:,.2f}")
        print(f"  day P&L: ${snap['realized_pl_day_usd']:+,.2f}")
        print(f"  unrealized: ${snap['unrealized_pl_usd']:+,.2f}")
        print(f"  trailing DD: ${snap['trailing_dd_usd']:,.2f}")
        print(f"  open contracts: {snap['open_contracts_total']}")
    else:
        print("  (no snapshot recorded yet)")

    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
