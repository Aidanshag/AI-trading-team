"""One-time backfill for daily_pl rows from existing account_snapshots.

WHY THIS EXISTS:
The orchestrator's `session_close_workflow` and `_backfill_missing_daily_pl`
own writes to `daily_pl`. The orchestrator is currently dormant (per
CLAUDE.md), so daily_pl has not been populated since 2026-05-01 even
though account_snapshots has been written every 5 min by the auto_trader.

This script reads account_snapshots, finds UTC days that don't have a
finalized daily_pl row, and fills them in — including trade_count, which
the orchestrator's existing call sites omit.

USAGE:
    python -m scripts.backfill_daily_pl              # backfill all missing
    python -m scripts.backfill_daily_pl --dry-run    # show what would change
    python -m scripts.backfill_daily_pl --since 2026-05-02  # bound the window

This does NOT alter today's row (today is still in flux until session
close). Idempotent on `day` — safe to re-run.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)

from state.db import get_db


def _today_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _trade_count_for_day(c, day: str) -> int:
    """Count of entry orders (excluding _stop / _target legs) submitted/filled
    on `day` UTC by the auto_trader."""
    row = c.execute(
        "SELECT COUNT(*) FROM orders "
        "WHERE ts_proposed LIKE ? "
        "  AND agent='auto_trader' "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted', 'filled') ",
        (f"{day}%",),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _last_snapshot_for_day(c, day: str) -> tuple[float, float] | None:
    """Returns (realized_pl_day_usd, peak_realized_pl_day_usd) from the
    final snapshot of `day`. Peak is approximated as the max realized
    over the day (intraday high-water).

    Returns None if no snapshots exist for the day.
    """
    row = c.execute(
        """SELECT realized_pl_day_usd,
                  MAX(realized_pl_day_usd) AS peak
             FROM account_snapshots
            WHERE substr(ts, 1, 10) = ?
            ORDER BY ts DESC LIMIT 1""",
        (day,),
    ).fetchone()
    if not row or row[0] is None:
        return None
    return (float(row[0]), float(row[1]) if row[1] is not None else 0.0)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would change; do not write.")
    p.add_argument("--since", default=None,
                   help="UTC date YYYY-MM-DD lower bound (inclusive). "
                        "Default: backfill all missing days.")
    p.add_argument("--include-today", action="store_true",
                   help="Also write/overwrite today's row. By default today "
                        "is left to the live process to finalize at close.")
    args = p.parse_args()

    db = get_db()
    c = db.connect()

    today = _today_utc()
    # Distinct days present in account_snapshots
    snap_days = sorted({
        r[0] for r in c.execute(
            "SELECT DISTINCT substr(ts, 1, 10) FROM account_snapshots"
        ) if r[0]
    })
    if args.since:
        snap_days = [d for d in snap_days if d >= args.since]
    if not args.include_today:
        snap_days = [d for d in snap_days if d < today]

    if not snap_days:
        print("No candidate days to backfill.")
        return 0

    # Days that already have a daily_pl row
    existing = {r[0] for r in c.execute("SELECT day FROM daily_pl")}

    plan: list[tuple[str, float, float, int, str]] = []  # (day, real, peak, trades, action)
    for day in snap_days:
        snap = _last_snapshot_for_day(c, day)
        if snap is None:
            plan.append((day, 0.0, 0.0, 0, "skip — no snapshots"))
            continue
        realized, peak = snap
        n_trades = _trade_count_for_day(c, day)
        action = "update" if day in existing else "insert"
        plan.append((day, realized, peak, n_trades, action))

    print(f"Backfill plan ({len(plan)} day(s)):")
    print(f"  {'day':12s}  {'realized':>10s}  {'peak':>10s}  {'trades':>6s}  action")
    print("  " + "-" * 60)
    for day, realized, peak, n, action in plan:
        print(f"  {day:12s}  ${realized:>+9,.2f}  ${peak:>+9,.2f}  {n:>6d}  {action}")

    if args.dry_run:
        print("\n--dry-run: no rows written.")
        return 0

    written = 0
    for day, realized, peak, n_trades, action in plan:
        if action.startswith("skip"):
            continue
        db.upsert_daily_pl(
            day=day,
            realized_pl_usd=realized,
            peak_realized_pl_usd=peak,
            trade_count=n_trades,
        )
        written += 1
    print(f"\nWrote {written} row(s) to daily_pl.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
