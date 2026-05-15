"""Stage graduation-eligible cells from the universal walk-forward into
the live_allowlist as `experimental: true` (shadow mode).

The existing brain + shadow_trades + resolve_shadow_trades pipeline then:
  1. Brain emits signals for these cells when conditions match
  2. Signals route to `shadow_trades` table (never to broker)
  3. Nightly `resolve_shadow_trades.py` grades each signal's outcome
  4. `cell_auto_promote.py` flags cells whose live shadow performance
     matches walk-forward predictions, for user review

THIS DOES NOT TRIGGER REAL FILLS. Shadow mode only. Real-money is
explicit user decision after weeks of live data per cell.

Usage:
    .venv/Scripts/python.exe -m scripts.stage_shadow_cells
    .venv/Scripts/python.exe -m scripts.stage_shadow_cells --top 30
    .venv/Scripts/python.exe -m scripts.stage_shadow_cells --dry  # preview only
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_JSON = PROJECT_ROOT / "state" / "universal_walkforward_results.json"
ALLOWLIST_FILE = PROJECT_ROOT / "state" / "strategy_validation.json"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--top", type=int, default=None,
                     help="cap on cells to stage (default: all eligible)")
    p.add_argument("--dry", action="store_true",
                     help="print what would change, don't write")
    p.add_argument("--source", type=str,
                     default="universal discovery 2026-05-15",
                     help="shadow_reason value")
    args = p.parse_args()

    if not INPUT_JSON.exists():
        print(f"ERROR: {INPUT_JSON} not found. Run universal_walk_forward first.")
        return 1
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        sweep = json.load(f)

    eligible = sweep.get("cells_all") or []
    eligible = [c for c in eligible if c.get("graduation_eligible")]
    if not eligible:
        print(f"No graduation-eligible cells in {INPUT_JSON}.")
        return 0

    if args.top:
        eligible = eligible[:args.top]

    print(f"=== stage_shadow_cells ===")
    print(f"source: {args.source}")
    print(f"eligible cells: {len(eligible)}")
    print()

    with open(ALLOWLIST_FILE, "r", encoding="utf-8") as f:
        validation = json.load(f)
    allow = validation.get("live_allowlist", []) or []

    existing_keys = {
        f"{c.get('strategy')}/{c.get('symbol')}/{c.get('session')}/{c.get('side')}"
        for c in allow
    }

    added = 0
    skipped_existing = 0
    now_iso = datetime.now(tz=timezone.utc).isoformat()
    for cell in eligible:
        key = (f"{cell['strategy']}/{cell['symbol']}/"
                f"{cell['session']}/{cell['side']}")
        if key in existing_keys:
            skipped_existing += 1
            continue
        new_entry = {
            "strategy": cell["strategy"],
            "symbol": cell["symbol"],
            "session": cell["session"],
            "side": cell["side"],
            "experimental": True,
            "shadow_reason": args.source,
            "promoted_at": now_iso,
            "walkforward_oos": {
                "n": cell["oos_n"],
                "hit": cell["oos_hit"],
                "E": cell["oos_E"],
                "t": cell["oos_t"],
            },
        }
        allow.append(new_entry)
        existing_keys.add(key)
        added += 1
        print(f"  STAGED: {key:55} "
               f"n={cell['oos_n']:>3} t={cell['oos_t']:+.2f} E={cell['oos_E']:+.2f}")

    print()
    print(f"Added: {added} new cells")
    print(f"Skipped (already in allowlist): {skipped_existing}")

    if args.dry:
        print(f"\n(--dry mode: not writing changes)")
        return 0

    validation["live_allowlist"] = allow
    validation["live_allowlist_generated_at"] = now_iso
    src = validation.get("live_allowlist_source") or ""
    if "universal discovery" not in src:
        validation["live_allowlist_source"] = (
            (src + " + " if src else "")
            + args.source
        )
    with open(ALLOWLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(validation, f, indent=2, default=str)
    print(f"\nWrote {ALLOWLIST_FILE}")
    print(f"Added cells start firing in next brain scan (shadow mode).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
