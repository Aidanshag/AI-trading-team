"""Audit the live_allowlist against exec_mirror evidence; recommend or
apply demotions for structurally-broken cells.

WHY:
Theoretical strategy validation (param_sweep + walk-forward) can pass
cells that production WILL NOT realize edge on because:

  1. The strategy's average target is below the profit_lock first-tier
     floor ($30). Production exit clamps at break-even (then friction
     pulls it negative). The strategy literally cannot profit at the
     intended target size.

  2. Friction (slippage + fees) exceeds 30% of typical risk_usd.
     The cell is friction-poisoned regardless of edge.

  3. Empirical exec_mirror_pnl_r over a recent window is meaningfully
     negative. Whatever the theory, production reality is bleeding.

This validator catches all three and demotes failing cells. Mirrors
the cull pattern that's worked historically (gap_fill demotion 5/11,
vwap_reversion deletion 5/4) but encodes the rule so a human doesn't
need to re-derive it each time.

Built 2026-05-12 per user direction "back-end infrastructure to ensure
this doesn't become a pattern".

USAGE:
  python -m scripts.validate_live_filter                 # dry-run report
  python -m scripts.validate_live_filter --apply         # demote in place
  python -m scripts.validate_live_filter --min-n 20      # require >=20
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from tools.shadow_realism import (
    TICK_ECONOMICS, FEES_PER_ROUND_TRIP, DEFAULT_SLIPPAGE_TICKS_ROUND_TRIP,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ALLOWLIST_PATH = PROJECT_ROOT / "state" / "strategy_validation.json"
DB_PATH = PROJECT_ROOT / "state" / "fund.db"
DEMOTION_LOG = PROJECT_ROOT / "vault" / "research" / "live_filter_demotions.md"


# ── Gate thresholds ────────────────────────────────────────────
# These encode the "structurally broken" definition. Tunable; conservative.

MIN_N_FOR_DECISION = 15          # need >=15 resolved shadows to demote
MIN_EXEC_AVG_R = -0.30           # below this → DROP
MIN_TARGET_USD_FLOOR = 80.0      # below this → DROP (above 2nd-tier floor)
MAX_FRICTION_FRACTION = 0.30     # friction > 30% of risk → DROP
RECENT_WINDOW_DAYS = 12          # how far back to look


def _friction_usd(symbol: str) -> float:
    """Round-trip slippage + fees for a 1-lot, no stop slippage."""
    _, tick_value = TICK_ECONOMICS.get(symbol, (0.0, 0.0))
    return (DEFAULT_SLIPPAGE_TICKS_ROUND_TRIP * tick_value
            + FEES_PER_ROUND_TRIP.get(symbol, 4.0))


def _query_cell_stats(con: sqlite3.Connection, cell: dict,
                       cutoff_iso: str) -> dict:
    """Pull exec_mirror summary stats for one (strategy, symbol, side) cell."""
    cur = con.cursor()
    cur.execute(
        """SELECT COUNT(*) AS n,
                  AVG(exec_mirror_pnl_r) AS exec_avg_r,
                  AVG(pnl_r)             AS theo_avg_r,
                  AVG(risk_usd)          AS avg_risk_usd,
                  AVG(ABS(target_price - entry_price)
                      / NULLIF(ABS(entry_price - stop_price), 0)) AS avg_rr
             FROM shadow_trades
            WHERE strategy=? AND symbol=? AND side=?
              AND exec_mirror_pnl_r IS NOT NULL
              AND ts_signal >= ?""",
        (cell["strategy"], cell["symbol"], cell["side"], cutoff_iso),
    )
    row = cur.fetchone()
    return {
        "n": int(row[0] or 0),
        "exec_avg_r": float(row[1] or 0.0),
        "theo_avg_r": float(row[2] or 0.0),
        "avg_risk_usd": float(row[3] or 0.0),
        "avg_rr": float(row[4] or 0.0),
    }


def _classify(cell: dict, stats: dict,
              *, min_n: int, min_exec_r: float,
              min_target_usd: float, max_fric_frac: float) -> tuple[str, str]:
    """Return (verdict, reason). verdict ∈ KEEP, DROP, GATHER."""
    if stats["n"] < min_n:
        return "GATHER", f"low n ({stats['n']} < {min_n})"

    if stats["exec_avg_r"] < min_exec_r:
        return "DROP", (f"exec_avg_r={stats['exec_avg_r']:+.2f}R "
                        f"< floor {min_exec_r:+.2f}R (n={stats['n']})")

    target_usd = stats["avg_rr"] * stats["avg_risk_usd"]
    if (target_usd > 0 and target_usd < min_target_usd
            and stats["exec_avg_r"] < 0):
        return "DROP", (f"target=${target_usd:.0f} < ${min_target_usd:.0f} "
                        f"first-tier floor AND exec_avg negative")

    sym = cell["symbol"]
    risk = stats["avg_risk_usd"]
    if risk > 0:
        fric = _friction_usd(sym)
        fric_frac = fric / risk
        if fric_frac > max_fric_frac:
            return "DROP", (f"friction ${fric:.2f} / risk ${risk:.0f} "
                            f"= {fric_frac:.0%} > {max_fric_frac:.0%} floor")

    return "KEEP", (f"exec_avg_r={stats['exec_avg_r']:+.2f}R "
                    f"(n={stats['n']})")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true",
                   help="actually demote cells; otherwise dry-run report only")
    p.add_argument("--min-n", type=int, default=MIN_N_FOR_DECISION)
    p.add_argument("--min-exec-r", type=float, default=MIN_EXEC_AVG_R)
    p.add_argument("--min-target-usd", type=float, default=MIN_TARGET_USD_FLOOR)
    p.add_argument("--max-friction-fraction", type=float, default=MAX_FRICTION_FRACTION)
    p.add_argument("--days", type=int, default=RECENT_WINDOW_DAYS)
    args = p.parse_args()

    if not ALLOWLIST_PATH.exists():
        print(f"ERROR: {ALLOWLIST_PATH} not found", file=sys.stderr)
        return 2
    sv = json.loads(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    allowlist = sv.get("live_allowlist") or []
    if not allowlist:
        print("live_allowlist empty; nothing to validate.")
        return 0

    cutoff = (datetime.now(tz=timezone.utc).timestamp()
              - args.days * 24 * 3600)
    cutoff_iso = datetime.fromtimestamp(cutoff, tz=timezone.utc).isoformat()

    con = sqlite3.connect(str(DB_PATH))

    decisions: list[dict] = []
    keep: list[dict] = []
    drop: list[dict] = []
    gather: list[dict] = []

    for cell in allowlist:
        stats = _query_cell_stats(con, cell, cutoff_iso)
        verdict, reason = _classify(
            cell, stats,
            min_n=args.min_n, min_exec_r=args.min_exec_r,
            min_target_usd=args.min_target_usd,
            max_fric_frac=args.max_friction_fraction,
        )
        record = {**cell, **stats, "verdict": verdict, "reason": reason}
        decisions.append(record)
        if verdict == "KEEP":
            keep.append(cell)
        elif verdict == "GATHER":
            gather.append(cell)
        else:  # DROP
            drop.append(record)

    # ── Print report ──
    print(f"=== validate_live_filter ({args.days}d window, "
          f"n>={args.min_n}, exec_r>={args.min_exec_r:+.2f}) ===\n")
    print(f"  {'strategy':25s} {'sym':4s} {'ses':>9s} {'side':5s} "
          f"{'n':>3} {'execR':>7} {'verdict':<8} reason")
    print("  " + "-" * 110)
    for d in decisions:
        print(f"  {d['strategy']:25s} {d['symbol']:4s} {d['session']:>9s} "
              f"{d['side']:5s} {d['n']:3d} {d['exec_avg_r']:+7.2f} "
              f"{d['verdict']:<8} {d['reason']}")
    print()
    print(f"Summary: KEEP={len(keep)}  GATHER={len(gather)}  DROP={len(drop)}")

    if not drop:
        print("\nNo cells to demote. Live filter is clean.")
        return 0

    if not args.apply:
        print(f"\nDRY RUN — re-run with --apply to demote {len(drop)} cells.")
        return 0

    # ── Apply demotions ──
    keep_plus_gather = keep + gather
    sv["live_allowlist"] = keep_plus_gather
    # Track demotion history in the JSON itself for auditability
    history = sv.get("demotion_history", [])
    history.append({
        "ts": datetime.now(tz=timezone.utc).isoformat(),
        "agent": "validate_live_filter",
        "cells_dropped": [
            {k: v for k, v in d.items()
             if k in ("strategy", "symbol", "session", "side", "reason",
                      "n", "exec_avg_r")}
            for d in drop
        ],
    })
    sv["demotion_history"] = history
    ALLOWLIST_PATH.write_text(
        json.dumps(sv, indent=2, sort_keys=False),
        encoding="utf-8",
    )

    # ── Audit log to vault ──
    DEMOTION_LOG.parent.mkdir(parents=True, exist_ok=True)
    log_entry = [
        f"\n## {datetime.now(tz=timezone.utc).isoformat()} — "
        f"validate_live_filter demoted {len(drop)} cells\n",
    ]
    for d in drop:
        log_entry.append(
            f"- `{d['strategy']}/{d['symbol']}/{d['session']}/{d['side']}` "
            f"— {d['reason']}"
        )
    log_entry.append("")
    if DEMOTION_LOG.exists():
        existing = DEMOTION_LOG.read_text(encoding="utf-8")
    else:
        existing = (
            "# Live-filter demotion log\n\n"
            "Audit trail of cells demoted from `live_allowlist` by "
            "`scripts/validate_live_filter.py`. Each entry is a structural "
            "breakdown (negative exec_mirror, target below first tier, or "
            "friction-poisoned).\n"
        )
    DEMOTION_LOG.write_text(existing + "\n".join(log_entry), encoding="utf-8")
    print(f"\nApplied. Live allowlist now has {len(keep_plus_gather)} cells.")
    print(f"Audit logged to {DEMOTION_LOG.relative_to(PROJECT_ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
