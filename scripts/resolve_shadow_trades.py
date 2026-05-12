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
from tools.exec_mirror import evaluate_exec_mirror


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

    # Group rows by symbol so we only fetch the contract id + bars once per
    # symbol. Per-row fetches hit ProjectX 429 rate limits quickly (the v1
    # implementation did ~2 API calls per shadow row → 100+ rows = throttled).
    by_symbol: dict[str, list[dict]] = {}
    for row in pending:
        by_symbol.setdefault(row["symbol"], []).append(row)

    resolved = 0
    for sym, rows in by_symbol.items():
        try:
            cid = _front_contract_id(client, sym)
        except ProjectXError as e:
            print(f"  skip {sym} (x{len(rows)}): contract lookup failed ({e})")
            continue
        if not cid:
            print(f"  skip {sym} (x{len(rows)}): no front-month contract")
            if not args.dry_run:
                for row in rows:
                    db.resolve_shadow_trade(
                        row["id"], outcome="invalidated", pnl_r=0.0,
                        notes="no front-month contract found",
                    )
            continue

        # One bars fetch covering ALL signals for this symbol
        min_signal = min(
            datetime.fromisoformat(r["ts_signal"].replace("Z", "+00:00"))
            for r in rows
        )
        max_signal = max(
            datetime.fromisoformat(r["ts_signal"].replace("Z", "+00:00"))
            for r in rows
        )
        end_ts = max_signal + timedelta(hours=args.max_window_hours)
        if end_ts > datetime.now(tz=timezone.utc):
            end_ts = datetime.now(tz=timezone.utc)

        try:
            all_bars = client.get_bars(
                contract_id=cid,
                start_time=min_signal.isoformat(),
                end_time=end_ts.isoformat(),
                unit=2, unit_number=1, limit=5000, live=False,
            )
        except ProjectXError as e:
            print(f"  skip {sym} (x{len(rows)}): bars failed ({e})")
            continue

        if not all_bars:
            print(f"  skip {sym} (x{len(rows)}): empty bars")
            continue

        # Bars come ordered by time; walk per-row through the slice >= signal_ts
        # Pre-parse bar timestamps once
        def _bar_ts(b: dict) -> datetime:
            ts = b.get("t") or b.get("ts") or b.get("time")
            if isinstance(ts, str):
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return ts  # already datetime

        parsed_bars = []
        for b in all_bars:
            try:
                parsed_bars.append((_bar_ts(b), b))
            except Exception:
                continue
        parsed_bars.sort(key=lambda p: p[0])

        for row in rows:
            sig_ts = datetime.fromisoformat(row["ts_signal"].replace("Z", "+00:00"))
            row_bars = [b for ts, b in parsed_bars if ts >= sig_ts]
            outcome, pnl_r, note = _evaluate_path(
                row_bars,
                side=row["side"],
                entry=float(row["entry_price"]),
                stop=float(row["stop_price"]),
                target=float(row["target_price"]),
            )
            # Also compute the execution-mirror outcome (what production
            # would have actually realized given SKIP_TARGET_LEG + profit_lock
            # tiers + hard-flatten clock). Same bars; different exit logic.
            try:
                em_outcome, em_pnl_r, em_note = evaluate_exec_mirror(
                    row_bars,
                    symbol=sym,
                    side=row["side"],
                    entry=float(row["entry_price"]),
                    stop=float(row["stop_price"]),
                    risk_usd=(float(row["risk_usd"]) if row["risk_usd"] else None),
                )
            except Exception as e:
                em_outcome, em_pnl_r, em_note = "invalidated", 0.0, f"exec_mirror err: {e}"

            print(f"  {sym} #{row['id']} {row['strategy']:25s} "
                  f"{row['side']:5s} → theo={outcome:12s} {pnl_r:+.2f}R "
                  f"| exec={em_outcome:13s} {em_pnl_r:+.2f}R")
            if not args.dry_run:
                db.resolve_shadow_trade(
                    row["id"], outcome=outcome, pnl_r=pnl_r, notes=note,
                    exec_mirror_outcome=em_outcome,
                    exec_mirror_pnl_r=em_pnl_r,
                    exec_mirror_notes=em_note,
                )
            resolved += 1

    print(f"\nResolved {resolved}/{len(pending)} shadow trades.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
