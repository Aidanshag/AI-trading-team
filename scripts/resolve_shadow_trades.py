"""Resolve unresolved shadow trades.

For each open shadow trade older than `min_age_minutes` (default 30 min),
fetch 1-minute bars from signal time forward and determine whether the
trade would have hit target, stop, or timed out.

Outcomes:
  target_hit    — high (long) or low (short) reached target → +rr_planned R
  stop_hit      — low (long) or high (short) reached stop → -1.0 R
  time_stopped  — neither hit within `time_window_hours` (default 8h) →
                  marked-to-market as +/- (last - entry) / |entry - stop|
  invalidated   — no bars returned (data gap or symbol unsupported)

Usage:
  python -m scripts.resolve_shadow_trades [--min-age 30] [--max-window-hours 8]

Run from cron (Task Scheduler) every 30 min during market hours, plus
once at session close to clean up the day's signals.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from state.db import get_db
from tools.projectx_client import ProjectXError, get_client


def _front_contract_id(client, symbol: str) -> str | None:
    """Resolve symbol → ProjectX front-month contractId."""
    contracts = client.search_contracts(symbol, live=False)
    if not contracts:
        return None
    front = sorted(
        contracts,
        key=lambda c: c.get("expiryDate") or c.get("lastTradeDate") or "",
    )[0]
    return front.get("id") or front.get("contractId")


def _evaluate_path(
    bars: list[dict],
    *,
    side: str,
    entry: float,
    stop: float,
    target: float,
) -> tuple[str, float, str]:
    """Walk forward through bars, return (outcome, pnl_r, note).

    pnl_r:  target_hit → +R (where R = abs(target-entry)/abs(entry-stop))
            stop_hit   → -1.0
            time_stopped → mark-to-market R against last close
    """
    if not bars:
        return ("invalidated", 0.0, "no bars returned")

    risk_per_unit = abs(entry - stop)
    if risk_per_unit == 0:
        return ("invalidated", 0.0, "zero risk distance (stop=entry)")
    rr = abs(target - entry) / risk_per_unit

    # ProjectX bars: list of {t, o, h, l, c, v}. First entry is oldest.
    entry_filled = False
    for bar in bars:
        try:
            high = float(bar.get("h") or bar.get("high"))
            low  = float(bar.get("l") or bar.get("low"))
        except (TypeError, ValueError):
            continue

        # First, has price reached the entry level (so the order would fill)?
        # Edge Hunter triggers are stop-entry or breakout style; we treat
        # them all as marketable on first touch.
        if not entry_filled:
            if side == "long" and high >= entry:
                entry_filled = True
            elif side == "short" and low <= entry:
                entry_filled = True
            else:
                continue
            # Fall through into the same bar to check stop/target

        if side == "long":
            # If both stop and target hit in same bar, assume stop first
            # (conservative). Real fill ambiguity gets resolved this way.
            if low <= stop:
                return ("stop_hit", -1.0, f"stop hit @ {stop}")
            if high >= target:
                return ("target_hit", +rr, f"target hit @ {target}, R={rr:.2f}")
        else:  # short
            if high >= stop:
                return ("stop_hit", -1.0, f"stop hit @ {stop}")
            if low <= target:
                return ("target_hit", +rr, f"target hit @ {target}, R={rr:.2f}")

    # Time-stopped: neither hit. Mark-to-market against last close.
    if not entry_filled:
        return ("invalidated", 0.0, "entry never reached")

    last_close = float(bars[-1].get("c") or bars[-1].get("close") or entry)
    if side == "long":
        unrealized_r = (last_close - entry) / risk_per_unit
    else:
        unrealized_r = (entry - last_close) / risk_per_unit
    return ("time_stopped", float(unrealized_r),
            f"time-stopped @ {last_close} ({unrealized_r:+.2f}R)")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--min-age", type=int, default=30,
                   help="only resolve trades older than N minutes (default 30)")
    p.add_argument("--max-window-hours", type=int, default=8,
                   help="bars retrieved up to N hours past signal (default 8)")
    p.add_argument("--limit", type=int, default=200,
                   help="max trades to resolve in one run")
    p.add_argument("--dry-run", action="store_true",
                   help="print outcomes but don't write to DB")
    args = p.parse_args()

    db = get_db()
    pending = db.unresolved_shadow_trades(age_min_minutes=args.min_age)[:args.limit]
    if not pending:
        print(f"No shadow trades older than {args.min_age} min are unresolved.")
        return 0

    try:
        client = get_client()
    except Exception as e:
        print(f"ERROR: ProjectX client unavailable: {e}", file=sys.stderr)
        return 2

    resolved = 0
    for row in pending:
        sym = row["symbol"]
        try:
            cid = _front_contract_id(client, sym)
        except ProjectXError as e:
            print(f"  skip {sym}: contract lookup failed ({e})")
            continue
        if not cid:
            print(f"  skip {sym}: no front-month contract")
            db.resolve_shadow_trade(
                row["id"], outcome="invalidated", pnl_r=0.0,
                notes="no front-month contract found",
            )
            continue

        signal_ts = datetime.fromisoformat(row["ts_signal"].replace("Z", "+00:00"))
        end_ts = signal_ts + timedelta(hours=args.max_window_hours)
        # Don't fetch bars from the future
        if end_ts > datetime.now(tz=timezone.utc):
            end_ts = datetime.now(tz=timezone.utc)

        try:
            bars = client.get_bars(
                contract_id=cid,
                start_time=signal_ts.isoformat(),
                end_time=end_ts.isoformat(),
                unit=2, unit_number=1, limit=1000, live=False,
            )
        except ProjectXError as e:
            print(f"  skip {sym} #{row['id']}: bars failed ({e})")
            continue

        outcome, pnl_r, note = _evaluate_path(
            bars,
            side=row["side"],
            entry=float(row["entry_price"]),
            stop=float(row["stop_price"]),
            target=float(row["target_price"]),
        )

        print(f"  {sym} #{row['id']} {row['strategy']:25s} "
              f"{row['side']:5s} → {outcome:14s} {pnl_r:+.2f}R  ({note})")

        if not args.dry_run:
            db.resolve_shadow_trade(row["id"], outcome=outcome, pnl_r=pnl_r,
                                    notes=note)
        resolved += 1

    print(f"\nResolved {resolved}/{len(pending)} shadow trades.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
