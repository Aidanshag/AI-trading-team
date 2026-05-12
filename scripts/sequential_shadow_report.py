"""Report: shadow P&L after applying production sequential gates.

Loads resolved shadow_trades, groups by trading-day-key (17:00 CT
boundary), runs the sequential simulator on each day, and prints:
  * how many signals fired vs were blocked, by reason
  * realistic day P&L if production had taken the fired ones

This is the closest single number we have to "what would the system
have done if it had been live every day". See:
  tools/sequential_shadow_sim.py  — gate logic
  tools/exec_mirror.py            — per-signal P&L

Usage:
  python -m scripts.sequential_shadow_report [--days 7]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from state.db import get_db
from tools.sequential_shadow_sim import (
    ShadowSignal, simulate_day, aggregate_results, trading_day_key,
)


def _parse_ts(s: str) -> datetime:
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=7,
                   help="how many days back to report on (default 7)")
    p.add_argument("--combine", action="store_true", default=True,
                   help="apply Combine-stage daily profit cap (+$600)")
    args = p.parse_args()

    db = get_db()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=args.days)
              ).isoformat(timespec="seconds")
    rows = db.connect().execute(
        """SELECT id, ts_signal, symbol, strategy, side, risk_usd,
                  exec_mirror_outcome, exec_mirror_pnl_r
             FROM shadow_trades
            WHERE outcome IS NOT NULL
              AND exec_mirror_pnl_r IS NOT NULL
              AND ts_signal >= ?
            ORDER BY ts_signal""",
        (cutoff,),
    ).fetchall()
    if not rows:
        print("No resolved shadows in window.")
        return 0

    # Group by trading day key
    by_day: dict[str, list[ShadowSignal]] = defaultdict(list)
    for r in rows:
        ts = _parse_ts(r["ts_signal"])
        sig = ShadowSignal(
            id=r["id"], ts_signal=ts, symbol=r["symbol"],
            strategy=r["strategy"], side=r["side"],
            risk_usd=float(r["risk_usd"] or 0.0),
            exec_mirror_outcome=r["exec_mirror_outcome"],
            exec_mirror_pnl_r=(float(r["exec_mirror_pnl_r"])
                                if r["exec_mirror_pnl_r"] is not None else None),
        )
        by_day[trading_day_key(ts)].append(sig)

    print(f"=== Sequential-gated shadow simulation (last {args.days} days) ===\n")
    print(f"  Gates: 15-min post-stop cooldown | 8-trade daily cap | "
          f"$600 daily profit cap (Combine)\n")
    print(f"  {'day':<12} {'total':>5} {'fired':>5} {'blocked':>7} "
          f"{'day_pnl_usd':>12}  blocked_by")

    grand_total = 0
    grand_fired = 0
    grand_blocked = 0
    grand_pnl = 0.0
    blocked_totals: dict[str, int] = {}

    for day in sorted(by_day.keys()):
        shadows = by_day[day]
        gated = simulate_day(shadows)
        summary = aggregate_results(gated)
        grand_total += summary["n_total"]
        grand_fired += summary["n_fired"]
        grand_blocked += summary["n_blocked"]
        grand_pnl += summary["realistic_day_pnl_usd"]
        for k, v in summary["blocked_by"].items():
            blocked_totals[k] = blocked_totals.get(k, 0) + v

        block_str = ", ".join(f"{k}={v}" for k, v in
                                sorted(summary["blocked_by"].items(),
                                        key=lambda kv: -kv[1])[:3])
        print(f"  {day:<12} {summary['n_total']:>5} {summary['n_fired']:>5} "
              f"{summary['n_blocked']:>7} ${summary['realistic_day_pnl_usd']:>+11.2f}"
              f"  {block_str}")

    print()
    print(f"  {'TOTAL':<12} {grand_total:>5} {grand_fired:>5} {grand_blocked:>7} "
          f"${grand_pnl:>+11.2f}")
    print()
    print(f"  Average per day:")
    n_days = max(1, len(by_day))
    print(f"    signals:      {grand_total/n_days:.1f}")
    print(f"    fired:        {grand_fired/n_days:.1f}")
    print(f"    day pnl:      ${grand_pnl/n_days:+.2f}")
    print()
    print(f"  Block-reason breakdown across all days:")
    for k, v in sorted(blocked_totals.items(), key=lambda kv: -kv[1]):
        pct = (v / grand_blocked * 100) if grand_blocked else 0
        print(f"    {k:<35} n={v:<4} ({pct:.0f}%)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
