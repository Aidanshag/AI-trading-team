"""Cost ledger — daily NET P&L automation.

Per cowork_coordination.md 2026-05-08 priority #4. Pulls all the cost
inputs into one rolling tally so the team can answer the only KPI that
matters: are we actually making money after all costs?

NET = gross trading P&L − Topstep fees − slippage − fixed costs

Sources:
  state/fund.db:orders                          — gross + fees + fills
  vault/research/live_slippage/<latest>.json    — measured slippage (when present)
  config/risk_limits.yaml                       — fee schedule per symbol
  vault/_meta/economics.md (constant)           — $26/day fixed-cost equivalent

Output:
  vault/_meta/cost_ledger_<YYYY-MM>.md          — rolling monthly ledger
  vault/_meta/cost_ledger.json                  — machine-readable summary

USAGE:
  python -m scripts.cost_ledger                 # current month
  python -m scripts.cost_ledger --month 2026-05
  python -m scripts.cost_ledger --since 2026-04-29
  python -m scripts.cost_ledger --print

This is the document the EOD report opens with. The whole point of the
fund's economics is that fees + subscriptions + slippage are real costs
that have to be subtracted from gross before claiming a green day.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)

DB_PATH = PROJECT_ROOT / "state" / "fund.db"
RISK_LIMITS = PROJECT_ROOT / "config" / "risk_limits.yaml"
SLIPPAGE_DIR = PROJECT_ROOT / "vault" / "research" / "live_slippage"
META_DIR = PROJECT_ROOT / "vault" / "_meta"

# ── Constants from vault/_meta/economics.md ─────────────────────
# Monthly fixed cost ~$575: Topstep $175 + Claude sub $100 + API $250 + buffer $50
# Amortized over ~22 trading days/month
FIXED_COST_PER_DAY_USD = 575.0 / 22.0  # ≈ $26.14


# ── helpers ────────────────────────────────────────────────────

def load_fee_schedule() -> dict:
    """Per-symbol round-trip fee in USD from risk_limits.yaml."""
    if not RISK_LIMITS.exists():
        return {"default": 5.00}
    try:
        cfg = yaml.safe_load(RISK_LIMITS.read_text(encoding="utf-8")) or {}
        fees = cfg.get("fees_round_trip_usd") or {}
        if "default" not in fees:
            fees["default"] = 5.00
        return fees
    except Exception:
        return {"default": 5.00}


def fee_for(symbol: str, fees: dict) -> float:
    return float(fees.get(symbol, fees.get("default", 5.00)))


def latest_slippage() -> dict | None:
    """Find the newest live_slippage JSON if any. Returns parsed payload or None."""
    if not SLIPPAGE_DIR.exists():
        return None
    files = sorted(SLIPPAGE_DIR.glob("*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:
        return None


def daily_gross_from_snapshots(c: sqlite3.Connection, day: str) -> float | None:
    """Use first/last snapshot of UTC day to compute gross (Δ balance).
    Returns None if insufficient data."""
    rows = c.execute(
        "SELECT balance_usd, ts FROM account_snapshots "
        "WHERE substr(ts, 1, 10) = ? ORDER BY ts ASC",
        (day,),
    ).fetchall()
    if len(rows) < 2:
        return None
    first = float(rows[0][0])
    last = float(rows[-1][0])
    return last - first


def daily_fee_count(c: sqlite3.Connection, day: str, fees: dict) -> tuple[float, int]:
    """Sum estimated fees on entry orders today. Returns (total_fees, n_entries)."""
    rows = c.execute(
        "SELECT symbol, qty FROM orders "
        "WHERE substr(ts_proposed, 1, 10) = ? "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted','filled')",
        (day,),
    ).fetchall()
    total = 0.0
    for r in rows:
        total += fee_for(r["symbol"], fees) * int(r["qty"] or 0)
    return total, len(rows)


def daily_slippage(c: sqlite3.Connection, day: str, fees: dict,
                   slippage_per_cell: dict | None) -> float:
    """Estimate slippage cost for the day's fills.

    If we have a per-cell slippage tracker output, use it (preferred).
    Otherwise estimate ~$2 per round-trip per contract — a placeholder
    that's plausible but should be replaced with measured slippage."""
    rows = c.execute(
        "SELECT symbol, qty FROM orders "
        "WHERE substr(ts_proposed, 1, 10) = ? "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted','filled')",
        (day,),
    ).fetchall()
    if slippage_per_cell:
        # Try to extract a global average slippage per contract.
        # Schema TBD until the tracker fills with real data; use $2/contract
        # as a fallback for now.
        avg = 2.0
        for cell, stats in slippage_per_cell.get("by_cell", {}).items():
            if "mean_slippage_usd" in stats:
                avg = float(stats["mean_slippage_usd"])
                break
        total = sum(int(r["qty"] or 0) for r in rows) * avg
    else:
        total = sum(int(r["qty"] or 0) for r in rows) * 2.0
    return total


def list_days_in_window(since: str, until: str) -> list[str]:
    s = datetime.fromisoformat(since).date()
    u = datetime.fromisoformat(until).date()
    out = []
    cur = s
    while cur <= u:
        # weekdays only — markets closed Sat/Sun
        if cur.weekday() < 5:
            out.append(cur.isoformat())
        cur += timedelta(days=1)
    return out


# ── ledger build ───────────────────────────────────────────────

def build_ledger(since: str, until: str) -> dict:
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    fees = load_fee_schedule()
    slip_data = latest_slippage()
    days = list_days_in_window(since, until)

    rows: list[dict] = []
    for day in days:
        gross = daily_gross_from_snapshots(c, day)
        fee_total, n_entries = daily_fee_count(c, day, fees)
        slip = daily_slippage(c, day, fees, slip_data)
        net = (gross or 0) - fee_total - slip - FIXED_COST_PER_DAY_USD
        rows.append({
            "day": day, "gross_usd": gross,
            "fees_usd": fee_total, "slippage_usd": slip,
            "fixed_cost_usd": FIXED_COST_PER_DAY_USD,
            "net_usd": net, "n_entries": n_entries,
            "gross_known": gross is not None,
        })
    c.close()

    cum_net = sum(r["net_usd"] for r in rows)
    cum_gross = sum(r["gross_usd"] or 0 for r in rows)
    cum_fees = sum(r["fees_usd"] for r in rows)
    cum_slip = sum(r["slippage_usd"] for r in rows)
    cum_fixed = sum(r["fixed_cost_usd"] for r in rows)
    n_trade_days = sum(1 for r in rows if r["n_entries"] > 0)
    n_trades = sum(r["n_entries"] for r in rows)

    return {
        "since": since, "until": until,
        "rows": rows,
        "summary": {
            "n_calendar_days": len(rows),
            "n_trading_days": n_trade_days,
            "n_entries_total": n_trades,
            "gross_usd": cum_gross,
            "fees_usd": cum_fees,
            "slippage_usd": cum_slip,
            "fixed_cost_usd": cum_fixed,
            "net_usd": cum_net,
            "avg_net_per_day_usd": cum_net / max(len(rows), 1),
        },
    }


# ── output ─────────────────────────────────────────────────────

def write_md(ledger: dict, month_tag: str) -> Path:
    out = META_DIR / f"cost_ledger_{month_tag}.md"
    s = ledger["summary"]
    L = ["---", "type: cost_ledger",
         f"month: {month_tag}",
         f"since: {ledger['since']}",
         f"until: {ledger['until']}",
         f"generated_at: {datetime.now(timezone.utc).isoformat()}",
         "---", "",
         f"# Cost ledger — {month_tag}",
         "",
         "> NET = gross trading P&L − Topstep fees − slippage − fixed cost.",
         "> The only KPI that matters per `vault/_meta/economics.md`.",
         "",
         "## Summary", "",
         f"- **Trading days**: {s['n_trading_days']} of {s['n_calendar_days']} ({s['n_entries_total']} entries)",
         f"- **Gross trading**: ${s['gross_usd']:+,.2f}",
         f"- **Topstep fees**:  ${-s['fees_usd']:+,.2f}",
         f"- **Slippage**:      ${-s['slippage_usd']:+,.2f}",
         f"- **Fixed cost**:    ${-s['fixed_cost_usd']:+,.2f}  ($"
         f"{FIXED_COST_PER_DAY_USD:.2f}/day × {s['n_calendar_days']} days)",
         f"- **NET**:           **${s['net_usd']:+,.2f}**",
         f"- Avg NET/day:       ${s['avg_net_per_day_usd']:+,.2f}",
         "",
         "## Per-day breakdown", "",
         "| Day | Gross | Fees | Slip | Fixed | NET | Entries | Note |",
         "|---|---:|---:|---:|---:|---:|---:|---|"]
    for r in ledger["rows"]:
        gross = (f"${r['gross_usd']:+,.2f}" if r['gross_known'] else "—")
        note = "" if r["gross_known"] else "no snapshots"
        L.append(f"| {r['day']} | {gross} "
                 f"| ${-r['fees_usd']:+,.2f} | ${-r['slippage_usd']:+,.2f} "
                 f"| ${-r['fixed_cost_usd']:+,.2f} "
                 f"| **${r['net_usd']:+,.2f}** | {r['n_entries']} | {note} |")
    L += ["",
          "## Notes",
          "",
          "- Gross is approximated from `account_snapshots` first/last balance.",
          "  Days without snapshots show '—'. The 4/29-5/1 window had a broken",
          "  snapshot pipeline — see `vault/lessons/2026-04-29_*.md`.",
          "- Slippage uses measured per-cell averages from",
          "  `vault/research/live_slippage/<latest>.json` when available; a",
          "  $2/contract placeholder otherwise. Per the slippage finding",
          "  (cowork_coordination.md 2026-05-08), real slippage is the",
          "  difference between paper edge and live edge.",
          "- Fixed cost is $575/mo amortized over 22 trading days = "
          f"${FIXED_COST_PER_DAY_USD:.2f}/day. A flat (no-trade) day still",
          "  costs the fixed amount."]
    out.write_text("\n".join(L) + "\n", encoding="utf-8")
    return out


def write_json(ledger: dict) -> Path:
    out = META_DIR / "cost_ledger.json"
    out.write_text(json.dumps(ledger, indent=2, default=str),
                   encoding="utf-8")
    return out


# ── main ───────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--month", default=None,
                   help="YYYY-MM (default: current month UTC).")
    p.add_argument("--since", default=None,
                   help="Lower bound date (YYYY-MM-DD). Overrides --month.")
    p.add_argument("--until", default=None,
                   help="Upper bound date (YYYY-MM-DD). Default: today.")
    p.add_argument("--print", dest="do_print", action="store_true",
                   help="Print summary to stdout.")
    args = p.parse_args()

    today = datetime.now(timezone.utc).date()

    if args.since and args.until:
        since = args.since
        until = args.until
        month_tag = since[:7]
    else:
        if args.month:
            year, month = (int(x) for x in args.month.split("-"))
            month_tag = args.month
        else:
            year, month = today.year, today.month
            month_tag = f"{year:04d}-{month:02d}"
        from calendar import monthrange
        since = f"{year:04d}-{month:02d}-01"
        last_day = min(today.day, monthrange(year, month)[1]) if (
            year == today.year and month == today.month
        ) else monthrange(year, month)[1]
        until = f"{year:04d}-{month:02d}-{last_day:02d}"

    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found", file=sys.stderr)
        return 2

    print(f"Building ledger {since} → {until} (month tag {month_tag})")
    ledger = build_ledger(since, until)
    md_path = write_md(ledger, month_tag)
    json_path = write_json(ledger)
    print(f"Wrote {md_path.relative_to(PROJECT_ROOT)}")
    print(f"Wrote {json_path.relative_to(PROJECT_ROOT)}")

    if args.do_print:
        s = ledger["summary"]
        print()
        print(f"  Days {s['n_trading_days']}/{s['n_calendar_days']} active "
              f"({s['n_entries_total']} entries)")
        print(f"  Gross: ${s['gross_usd']:+,.2f}  Fees: ${-s['fees_usd']:+,.2f} "
              f"Slip: ${-s['slippage_usd']:+,.2f}  Fixed: ${-s['fixed_cost_usd']:+,.2f}")
        print(f"  NET: ${s['net_usd']:+,.2f}  ({'+' if s['net_usd'] >= 0 else ''}"
              f"${s['avg_net_per_day_usd']:+.2f}/day)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
