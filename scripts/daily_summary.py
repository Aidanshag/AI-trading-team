"""Daily summary — text-mode dashboard.

The 95%-of-value, 1%-of-effort version of a Grafana dashboard. Writes a
markdown file you can read in Obsidian (or just `cat`) every morning to
see what happened, where you are, and what's diverging from prediction.

Sections:
1. Topline: balance, P&L today, P&L month-to-date, Combine progress
2. Trading: trades today, fills, working orders, open positions
3. Per-cell prediction vs actuals: hit rate, expectancy, sample size
4. Slippage: per-cell measured slippage in ticks
5. System health: snapshot freshness, scheduled task state, recent errors
6. Backlog status: P0 items open

Usage:
  python -m scripts.daily_summary           # writes today's summary
  python -m scripts.daily_summary --print   # also prints to stdout
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from statistics import mean

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Topstep Combine numbers
COMBINE_TARGET = 3000.0
COMBINE_DLL = 1000.0
COMBINE_TDD = 2000.0
STARTING_BALANCE = 50000.0

# Tick economics for slippage
TICK_BY_SYMBOL = {
    "ZN": 0.015625, "ZB": 0.03125, "ZT": 0.0078125, "ZF": 0.0078125,
    "NG": 0.001, "GC": 0.10, "6E": 0.00005,
    "ES": 0.25, "NQ": 0.25, "CL": 0.01,
}


def _connect():
    db = PROJECT_ROOT / "state" / "fund.db"
    if not db.exists():
        return None
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    return conn


def section_topline(conn):
    if conn is None:
        return "## 1. Topline\n_no DB available_\n"
    out = ["## 1. Topline\n"]

    # Latest snapshot
    row = conn.execute(
        "SELECT * FROM account_snapshots ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    if not row:
        return "## 1. Topline\n_no snapshot data yet_\n"
    bal = float(row["balance_usd"] or 0)
    realized_today = float(row["realized_pl_day_usd"] or 0)
    unrealized = float(row["unrealized_pl_usd"] or 0)
    trailing_dd = float(row["trailing_dd_usd"] or 0)
    can_trade = bool(row["can_trade"])

    cumulative_profit = bal - STARTING_BALANCE
    target_progress = cumulative_profit / COMBINE_TARGET * 100
    dll_distance = COMBINE_DLL + realized_today  # negative realized → smaller distance
    tdd_distance = COMBINE_TDD - trailing_dd

    out.append(f"| Metric | Value |")
    out.append(f"|---|---|")
    out.append(f"| Account balance | ${bal:,.2f} |")
    out.append(f"| Cumulative profit | ${cumulative_profit:+,.2f} |")
    out.append(f"| Combine target progress | {target_progress:.0f}% of $3,000 |")
    out.append(f"| Today's realized P&L | ${realized_today:+,.2f} |")
    out.append(f"| Unrealized P&L | ${unrealized:+,.2f} |")
    out.append(f"| Trailing drawdown | ${trailing_dd:.2f} |")
    out.append(f"| DLL distance | ${dll_distance:.2f} (breach at $-1,000) |")
    out.append(f"| TDD distance | ${tdd_distance:.2f} (breach at $2,000) |")
    out.append(f"| Can trade flag | {'✓' if can_trade else '✗ HALTED'} |")
    out.append("")
    return "\n".join(out)


def section_trading_today(conn):
    if conn is None:
        return "## 2. Trading\n_no DB_\n"
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    rows = conn.execute(
        """SELECT symbol, side, status, qty, limit_price, stop_price,
                  avg_fill_price, ts_proposed, client_order_id
           FROM orders
           WHERE date(ts_proposed) = ?
             AND agent IN ('live_trader', 'auto_trader')
           ORDER BY ts_proposed""",
        (today,),
    ).fetchall()

    out = ["## 2. Trading today\n"]
    if not rows:
        out.append("_no orders today_\n")
        return "\n".join(out)

    out.append(f"| Time | Symbol | Side | Qty | Status | Intent | Fill |")
    out.append(f"|---|---|---|---|---|---|---|")
    for r in rows:
        ts = r["ts_proposed"][11:19] if r["ts_proposed"] else "?"
        intent = r["limit_price"] or r["stop_price"] or "-"
        fill = r["avg_fill_price"] or "-"
        out.append(
            f"| {ts} | {r['symbol']} | {r['side']} | {r['qty']} | "
            f"{r['status']} | {intent} | {fill} |"
        )
    out.append("")
    return "\n".join(out)


def section_per_cell_predictions_vs_actuals(conn):
    if conn is None:
        return "## 3. Per-cell prediction vs actuals\n_no DB_\n"

    out = ["## 3. Per-cell prediction vs actuals\n"]

    # Load OOS predictions from validation file
    val_file = PROJECT_ROOT / "state" / "strategy_validation.json"
    if not val_file.exists():
        out.append("_no validation file_\n")
        return "\n".join(out)
    with open(val_file) as f:
        val_data = json.load(f)
    cells_oos = val_data.get("cells", {})
    allowlist = val_data.get("live_allowlist", [])

    # Compute live R-multiples per cell from filled orders
    live_pnl_per_cell = defaultdict(list)
    rows = conn.execute(
        """SELECT symbol, side, status, qty, limit_price, stop_price,
                  avg_fill_price, ts_proposed, client_order_id
           FROM orders
           WHERE agent = 'live_trader'
             AND avg_fill_price IS NOT NULL
             AND avg_fill_price > 0
           ORDER BY ts_proposed"""
    ).fetchall()

    if not rows:
        out.append("_no live fills yet — predictions only_\n")
        out.append("")
        out.append(f"Active allowlist cells: {len(allowlist)}")
        out.append("")
        out.append(f"| Cell | OOS n | OOS hit% | OOS E[R] |")
        out.append(f"|---|---|---|---|")
        for c in allowlist[:15]:
            key = f"{c['strategy']}|{c['symbol']}|{c['session']}|{c['side']}"
            cell_data = cells_oos.get(key, {})
            oos = cell_data.get("last_oos") or {}
            n = oos.get("n", 0)
            hit = (oos.get("hit") or 0) * 100
            e = oos.get("e") or 0
            out.append(f"| {key} | {n} | {hit:.0f}% | {e:+.2f} |")
        if len(allowlist) > 15:
            out.append(f"| ... | | | ({len(allowlist)-15} more) |")
        out.append("")
        return "\n".join(out)

    # We have fills — compute live vs OOS variance per cell (placeholder logic)
    out.append(f"_(N={len(rows)} fills available; per-cell live vs OOS analysis "
               f"not yet implemented — see scripts/live_vs_oos_tracker.py)_\n")
    return "\n".join(out)


def section_slippage(conn):
    if conn is None:
        return "## 4. Slippage\n_no DB_\n"

    out = ["## 4. Slippage\n"]

    rows = conn.execute(
        """SELECT symbol, side, order_type, limit_price, stop_price,
                  avg_fill_price, client_order_id
           FROM orders
           WHERE agent = 'live_trader'
             AND avg_fill_price IS NOT NULL
             AND avg_fill_price > 0"""
    ).fetchall()

    if not rows:
        out.append("_no live fills yet — slippage will populate after first fills_\n")
        return "\n".join(out)

    by_symbol = defaultdict(list)
    by_leg = defaultdict(list)
    for r in rows:
        sym = r["symbol"]
        tick = TICK_BY_SYMBOL.get(sym)
        if not tick:
            continue
        cid = r["client_order_id"] or ""
        if cid.endswith("_stop"):
            intent = r["stop_price"]; leg = "stop"
        elif cid.endswith("_target"):
            intent = r["limit_price"]; leg = "target"
        else:
            intent = r["limit_price"]; leg = "entry"
        if intent is None or intent <= 0:
            continue
        actual = r["avg_fill_price"]
        side = (r["side"] or "").lower()
        if side == "buy":
            slip = actual - intent
        else:
            slip = intent - actual
        slip_ticks = slip / tick
        by_symbol[sym].append(slip_ticks)
        by_leg[leg].append(slip_ticks)

    if not by_symbol:
        out.append("_could not compute (missing tick info)_\n")
        return "\n".join(out)

    out.append(f"| Symbol | n fills | Mean slip (ticks) | Median |")
    out.append(f"|---|---|---|---|")
    for sym, slips in sorted(by_symbol.items()):
        out.append(f"| {sym} | {len(slips)} | {mean(slips):+.2f} | "
                   f"{sorted(slips)[len(slips)//2]:+.2f} |")
    out.append("")
    out.append(f"| Leg type | n | Mean slip (ticks) |")
    out.append(f"|---|---|---|")
    for leg, slips in sorted(by_leg.items()):
        out.append(f"| {leg} | {len(slips)} | {mean(slips):+.2f} |")
    out.append("")
    return "\n".join(out)


def section_system_health(conn):
    out = ["## 5. System health\n"]

    # Snapshot freshness
    if conn:
        row = conn.execute(
            "SELECT ts FROM account_snapshots ORDER BY ts DESC LIMIT 1"
        ).fetchone()
        if row:
            try:
                last = datetime.fromisoformat(row[0].replace("Z", "+00:00"))
                age_min = (datetime.now(timezone.utc) - last).total_seconds() / 60
                fresh = "✓" if age_min < 30 else "⚠"
                out.append(f"- Snapshot age: {age_min:.0f} min {fresh}")
            except Exception:
                out.append("- Snapshot age: unparseable timestamp")

    # Scheduled task state (Windows only)
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             "Get-ScheduledTask | Where-Object {$_.TaskName -match 'Fund.*(Trader|Watchdog)'} | "
             "Select-Object TaskName,State | ConvertTo-Json"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            tasks = json.loads(result.stdout)
            if isinstance(tasks, dict):
                tasks = [tasks]
            # Numeric state codes → readable
            state_names = {0: "Unknown", 1: "Disabled", 2: "Queued",
                           3: "Ready", 4: "Running"}
            out.append("")
            out.append(f"| Task | State |")
            out.append(f"|---|---|")
            for t in tasks:
                state = t.get('State')
                state_str = state_names.get(state, str(state)) if isinstance(state, int) else str(state)
                out.append(f"| {t['TaskName']} | {state_str} |")
            out.append("")
    except Exception:
        pass

    # Cowork heartbeat
    try:
        result = subprocess.run(
            ["git", "log", "--since=36 hours ago", "--oneline"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        cw_result = subprocess.run(
            ["git", "log", "--since=36 hours ago", "--oneline", "--grep=cowork", "-i"],
            capture_output=True, text=True, timeout=10,
            cwd=str(PROJECT_ROOT),
        )
        any_count = len(result.stdout.strip().splitlines()) if result.stdout.strip() else 0
        cw_count = len(cw_result.stdout.strip().splitlines()) if cw_result.stdout.strip() else 0
        out.append(f"- Commits in last 36h: {any_count} total, {cw_count} from cowork")
        if cw_count == 0 and any_count <= 2:
            out.append("  ⚠ autonomous loop may be silent — check https://claude.ai/code/routines")
    except Exception:
        pass

    out.append("")
    return "\n".join(out)


def section_backlog_status():
    out = ["## 6. Backlog status (P0 items)\n"]
    backlog_file = PROJECT_ROOT / "vault" / "_meta" / "improvement_backlog.md"
    if not backlog_file.exists():
        return "## 6. Backlog status\n_no backlog file_\n"

    text = backlog_file.read_text()
    # Find P0 lines
    in_p0 = False
    p0_items = []
    for line in text.splitlines():
        if line.startswith("## P0"):
            in_p0 = True
            continue
        if in_p0 and line.startswith("## "):
            break
        if in_p0 and line.strip().startswith("- [P0]"):
            p0_items.append(line.strip())

    if not p0_items:
        out.append("_no P0 items_\n")
        return "\n".join(out)

    open_count = sum(1 for i in p0_items if "status: open" in i)
    merged_count = sum(1 for i in p0_items if "merged" in i)
    out.append(f"P0 items: {len(p0_items)} total ({open_count} open, {merged_count} merged)")
    out.append("")
    return "\n".join(out)


def main() -> int:
    p = argparse.ArgumentParser(prog="daily_summary")
    p.add_argument("--print", action="store_true",
                   help="also print to stdout (default writes to file only)")
    p.add_argument("--date", default=None,
                   help="override date (YYYY-MM-DD); default = today")
    args = p.parse_args()

    today = args.date or datetime.now().strftime("%Y-%m-%d")
    conn = _connect()

    sections = [
        f"# Daily summary — {today}\n",
        f"_Generated {datetime.now().strftime('%Y-%m-%d %H:%M %Z')}_\n",
        section_topline(conn),
        section_trading_today(conn),
        section_per_cell_predictions_vs_actuals(conn),
        section_slippage(conn),
        section_system_health(conn),
        section_backlog_status(),
    ]
    full = "\n".join(sections)

    out_dir = PROJECT_ROOT / "vault" / "_meta" / "daily_summaries"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{today}.md"
    out_file.write_text(full)
    print(f"Wrote {out_file.relative_to(PROJECT_ROOT)}")

    # Auto-stub the daily journal if missing — keeps the journal practice alive.
    # The journal is for narrative + decisions; this just ensures a file exists
    # for that date, pre-populated with mechanical fields. Agents/user fill in
    # the narrative. Journal practice died after 2026-04-29 — this prevents
    # silent gaps recurring.
    journal_dir = PROJECT_ROOT / "vault" / "journal"
    journal_dir.mkdir(parents=True, exist_ok=True)
    journal_file = journal_dir / f"{today}.md"
    if not journal_file.exists():
        weekday = datetime.strptime(today, "%Y-%m-%d").strftime("%A")
        journal_stub = f"""---
date: {today}
type: journal
session_kind: routine
---

# Journal — {today} ({weekday})

_Stub auto-created by daily_summary.py. Fill in narrative as the day unfolds._
_Mechanical state in: vault/_meta/daily_summaries/{today}.md_

## Cost ledger

See daily_summary for current state.

## Decisions made today

(append as decisions land)

## Setups taken / skipped

For each: symbol / strategy / entry-stop-target / conviction / outcome.
Skipped trades are equally important — patience IS a trade.

## Risk events today

From `risk_events`. Were they correct (saved a bad trade) or false-positive?

## Lessons (if any)

Pattern emerging 3+ times → draft to `vault/lessons/{today}_<slug>.md` with confidence tier.

## Timestamped entries

(agents append as the day unfolds)
"""
        journal_file.write_text(journal_stub)
        print(f"Created journal stub: {journal_file.relative_to(PROJECT_ROOT)}")

    if args.print:
        print()
        print(full)

    if conn:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
