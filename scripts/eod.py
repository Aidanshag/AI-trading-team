"""End-of-day report — the cost ledger every session is judged on.

Prints today's NET P&L (gross - Topstep fees - API spend), per-strategy
breakdown, and progress vs the monthly break-even pace ($575/mo ≈ $20/day).

Usage:
    python -m scripts.eod                # today
    python -m scripts.eod --date 2026-04-29
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)


def _load_yaml(name: str) -> dict:
    return yaml.safe_load(Path(f"config/{name}").read_text()) or {}


def _today_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _gross_pl_for_day(c: sqlite3.Connection, day: str) -> tuple[float, float]:
    """Returns (start_balance, end_balance, gross_pl). Uses first/last
    snapshots of the UTC day."""
    rows = c.execute(
        "SELECT balance_usd, ts FROM account_snapshots "
        "WHERE ts LIKE ? ORDER BY ts ASC",
        (f"{day}%",),
    ).fetchall()
    if not rows:
        return 0.0, 0.0
    return float(rows[0]["balance_usd"]), float(rows[-1]["balance_usd"])


def _fees_for_day(c: sqlite3.Connection, day: str, fee_schedule: dict) -> tuple[float, int]:
    """Sum estimated round-trip fees for entries placed today.
    Returns (total_fees, n_entries)."""
    rows = c.execute(
        "SELECT symbol, qty FROM orders "
        "WHERE ts_proposed LIKE ? AND agent='auto_trader' "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted', 'filled') ",
        (f"{day}%",),
    ).fetchall()
    default = float(fee_schedule.get("default", 5.00))
    total = 0.0
    for r in rows:
        total += float(fee_schedule.get(r["symbol"], default)) * int(r["qty"] or 0)
    return total, len(rows)


def _api_spend_for_day(c: sqlite3.Connection, day: str) -> float:
    row = c.execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day = ?",
        (day,),
    ).fetchone()
    return float(row[0] or 0.0)


def _per_strategy_summary(c: sqlite3.Connection, day: str) -> list[dict]:
    """Per-strategy thesis + outcome counts for the day."""
    # Pull thesis records (decisions table) joined to outcomes (risk_events)
    rows = c.execute(
        """SELECT symbol,
                  CASE
                      WHEN summary LIKE '%narrow_range_break%'      THEN 'narrow_range_break'
                      WHEN summary LIKE '%vwap_reversion%'          THEN 'vwap_reversion'
                      WHEN summary LIKE '%support_resistance_bounce%' THEN 'support_resistance_bounce'
                      WHEN summary LIKE '%bollinger_squeeze_break%' THEN 'bollinger_squeeze_break'
                      WHEN summary LIKE '%vol_regime_trend%'        THEN 'vol_regime_trend'
                      WHEN summary LIKE '%inside_bar_break%'        THEN 'inside_bar_break'
                      WHEN summary LIKE '%opening_range_breakout%'  THEN 'opening_range_breakout'
                      WHEN summary LIKE '%rsi2_extreme_reversion%'  THEN 'rsi2_extreme_reversion'
                      WHEN summary LIKE '%donchian_breakout%'       THEN 'donchian_breakout'
                      WHEN summary LIKE '%bollinger_mean_reversion%' THEN 'bollinger_mean_reversion'
                      WHEN summary LIKE '%volatility_breakout%'     THEN 'volatility_breakout'
                      WHEN summary LIKE '%pivot_reversal%'          THEN 'pivot_reversal'
                      WHEN summary LIKE '%volume_spike_reversal%'   THEN 'volume_spike_reversal'
                      WHEN summary LIKE '%vol_spike_fade%'          THEN 'vol_spike_fade'
                      WHEN summary LIKE '%pullback_in_trend%'       THEN 'pullback_in_trend'
                      WHEN summary LIKE '%keltner_breakout%'        THEN 'keltner_breakout'
                      WHEN summary LIKE '%range_mean_reversion%'    THEN 'range_mean_reversion'
                      WHEN summary LIKE '%gap_fill%'                THEN 'gap_fill'
                      ELSE 'other' END AS strategy,
                  COUNT(*) AS n
           FROM decisions
           WHERE agent='auto_trader' AND kind='thesis' AND ts LIKE ?
           GROUP BY symbol, strategy
           ORDER BY n DESC""",
        (f"{day}%",),
    ).fetchall()
    return [{"symbol": r["symbol"], "strategy": r["strategy"], "n": r["n"]}
            for r in rows]


def _risk_events_for_day(c: sqlite3.Connection, day: str) -> list[dict]:
    rows = c.execute(
        "SELECT severity, rule, COUNT(*) AS n FROM risk_events "
        "WHERE ts LIKE ? GROUP BY severity, rule ORDER BY n DESC",
        (f"{day}%",),
    ).fetchall()
    return [dict(r) for r in rows]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", default=_today_utc(),
                   help="UTC date YYYY-MM-DD (default: today)")
    args = p.parse_args()
    day = args.date

    risk = _load_yaml("risk_limits.yaml")
    fee_schedule = risk.get("fees_round_trip_usd") or {}
    starting = float(risk.get("account", {}).get("starting_balance", 50000))

    c = sqlite3.connect("state/fund.db")
    c.row_factory = sqlite3.Row

    print(f"\n{'='*60}")
    print(f"  END-OF-DAY REPORT — {day} UTC")
    print(f"{'='*60}\n")

    # COST LEDGER
    start_bal, end_bal = _gross_pl_for_day(c, day)
    gross = end_bal - start_bal if start_bal else 0.0
    fees, n_trades = _fees_for_day(c, day, fee_schedule)
    api = _api_spend_for_day(c, day)
    # Subscriptions cost ~$575/mo / ~22 trading days ≈ $26/day
    subs_per_day = 575.0 / 22.0
    net = gross - fees - api - subs_per_day

    print("COST LEDGER")
    print("-" * 60)
    print(f"  Gross trading P&L:    ${gross:>+10,.2f}")
    print(f"  Topstep fees:         ${-fees:>+10,.2f}  ({n_trades} entries)")
    print(f"  API spend:            ${-api:>+10,.2f}")
    print(f"  Subscriptions/day:    ${-subs_per_day:>+10,.2f}  (~$575/mo amortized)")
    print(f"  " + "-" * 28)
    color_n = "\033[92m" if net >= 0 else "\033[91m"
    end = "\033[0m"
    print(f"  {color_n}NET (the only KPI):   ${net:>+10,.2f}{end}")
    print()

    # POSITION + BALANCE
    print(f"  Start-of-day balance: ${start_bal:>10,.2f}")
    print(f"  End-of-day balance:   ${end_bal:>10,.2f}")
    print(f"  Cumulative from $50K: ${end_bal - starting:>+10,.2f}")
    print()

    # PROFITABILITY PACE
    target_per_day = 575.0 / 22.0   # break-even
    delta = net - target_per_day
    pace_color = "\033[92m" if delta >= 0 else "\033[91m"
    pace_msg = "ahead of break-even" if delta >= 0 else "behind break-even"
    print("PROFITABILITY PACE")
    print("-" * 60)
    print(f"  Today vs break-even:  {pace_color}${delta:>+10,.2f} {pace_msg}{end}")
    print(f"  (break-even pace is +$26/day = $575/mo)")
    print()

    # PER-STRATEGY
    summary = _per_strategy_summary(c, day)
    if summary:
        print("PER-STRATEGY ACTIVITY")
        print("-" * 60)
        print(f"  {'Symbol':6s} {'Strategy':30s} {'Theses':>8s}")
        for row in summary:
            print(f"  {row['symbol']:6s} {row['strategy']:30s} {row['n']:>8d}")
        print()

    # RISK EVENTS
    events = _risk_events_for_day(c, day)
    if events:
        print("RISK EVENTS")
        print("-" * 60)
        print(f"  {'Severity':10s} {'Rule':35s} {'Count':>6s}")
        for ev in events:
            color = "\033[91m" if ev["severity"] == "block" else (
                "\033[93m" if ev["severity"] == "warn" else "")
            print(f"  {color}{ev['severity']:10s} {ev['rule']:35s} {ev['n']:>6d}{end}")
        print()

    print(f"{'='*60}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
