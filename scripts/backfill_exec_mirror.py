"""One-shot backfill: for shadow trades resolved before exec_mirror existed,
re-fetch bars and compute exec_mirror_outcome / exec_mirror_pnl_r.

Idempotent: skips rows that already have exec_mirror_outcome set.

Usage:
  python -m scripts.backfill_exec_mirror [--limit N] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone

from state.db import get_db
from tools.projectx_client import ProjectXError, get_client
from tools.exec_mirror import evaluate_exec_mirror

# Reuse the resolver's contract lookup helper. Importing keeps this script
# small and a single source of truth.
from scripts.resolve_shadow_trades import _front_contract_id  # noqa: E402


def _bar_ts(b: dict) -> datetime | None:
    ts = b.get("t") or b.get("ts") or b.get("time")
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    return ts


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=2000)
    p.add_argument("--max-window-hours", type=int, default=8)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    db = get_db()
    conn = db.connect()
    rows = conn.execute(
        """SELECT id, ts_signal, symbol, strategy, side,
                  entry_price, stop_price, target_price, risk_usd
             FROM shadow_trades
            WHERE outcome IS NOT NULL
              AND exec_mirror_outcome IS NULL
            ORDER BY ts_signal DESC
            LIMIT ?""",
        (args.limit,),
    ).fetchall()
    pending = [dict(r) for r in rows]
    print(f"Pending backfill: {len(pending)}")
    if not pending:
        return 0

    try:
        client = get_client()
    except Exception as e:
        print(f"ERROR: ProjectX client unavailable: {e}", file=sys.stderr)
        return 2

    by_symbol: dict[str, list[dict]] = {}
    for r in pending:
        by_symbol.setdefault(r["symbol"], []).append(r)

    n_done = 0
    for sym, srows in by_symbol.items():
        try:
            cid = _front_contract_id(client, sym)
        except ProjectXError as e:
            print(f"  skip {sym} (x{len(srows)}): contract lookup failed ({e})")
            continue
        if not cid:
            print(f"  skip {sym} (x{len(srows)}): no front-month")
            continue

        min_ts = min(datetime.fromisoformat(r["ts_signal"].replace("Z", "+00:00"))
                      for r in srows)
        max_ts = max(datetime.fromisoformat(r["ts_signal"].replace("Z", "+00:00"))
                      for r in srows)
        end_ts = max_ts + timedelta(hours=args.max_window_hours)
        if end_ts > datetime.now(tz=timezone.utc):
            end_ts = datetime.now(tz=timezone.utc)

        try:
            all_bars = client.get_bars(
                contract_id=cid,
                start_time=min_ts.isoformat(),
                end_time=end_ts.isoformat(),
                unit=2, unit_number=1, limit=5000, live=False,
            )
        except ProjectXError as e:
            print(f"  skip {sym} (x{len(srows)}): bars failed ({e})")
            continue
        if not all_bars:
            print(f"  skip {sym} (x{len(srows)}): empty bars")
            continue

        parsed = []
        for b in all_bars:
            try:
                parsed.append((_bar_ts(b), b))
            except Exception:
                continue
        parsed = [p for p in parsed if p[0] is not None]
        parsed.sort(key=lambda p: p[0])

        for r in srows:
            sig_ts = datetime.fromisoformat(r["ts_signal"].replace("Z", "+00:00"))
            row_bars = [b for ts, b in parsed if ts >= sig_ts]
            try:
                em_outcome, em_pnl_r, em_note = evaluate_exec_mirror(
                    row_bars, symbol=sym, side=r["side"],
                    entry=float(r["entry_price"]),
                    stop=float(r["stop_price"]),
                    risk_usd=(float(r["risk_usd"]) if r["risk_usd"] else None),
                )
            except Exception as e:
                em_outcome, em_pnl_r, em_note = "invalidated", 0.0, f"err: {e}"

            print(f"  {sym} #{r['id']} {r['strategy']:25s} "
                  f"{r['side']:5s} → exec={em_outcome:13s} {em_pnl_r:+.2f}R")
            if not args.dry_run:
                conn.execute(
                    """UPDATE shadow_trades
                          SET exec_mirror_outcome=?, exec_mirror_pnl_r=?,
                              exec_mirror_notes=?
                        WHERE id=?""",
                    (em_outcome, em_pnl_r, em_note[:160], r["id"]),
                )
                conn.commit()
            n_done += 1

    print(f"\nBackfilled {n_done}/{len(pending)} rows.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
