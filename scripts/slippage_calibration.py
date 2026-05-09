"""Slippage calibration loop — feed measured live slippage back into
backtests. Closes the feedback loop between live fills and the
slippage parameter the backtests assume.

Per cowork_coordination.md weekly queue #8: 'extend slippage_tracker.py
to feed measured slippage back into backtests automatically.'

═══════════════════════════════════════════════════════════════════
PREDICTION + MEASUREMENT + VARIANCE (per 2026-05-08 coordination rule)
═══════════════════════════════════════════════════════════════════

PREDICTION:
  After 30+ live fills accumulate, this script will write per-symbol
  measured slippage that's:
    ZN: ~0.18 ticks/side (close to predicted 0.20)
    ZT: ~0.12 ticks/side (close to predicted 0.15)
    ZF: ~0.18 ticks/side (close to predicted 0.20)
    ZB: ~0.30 ticks/side (close to predicted 0.30)
  Subsequent param sweeps reading state/measured_slippage.json will
  produce dollar metrics consistent with live behavior to within ±10%.

MEASUREMENT:
  Two ways to verify:
  1. Compare backtest-output dollars BEFORE this calibration update
     vs AFTER (same period, same params). The delta is the slippage
     correction. Expected: 5-25% reduction in mean_$ per trade for
     gap_fill family; smaller change for wide-stop strategies like
     wide_session_drive.
  2. Run param_sweep.py with `--slippage-from-calibration` flag (or
     equivalent). The output's $@slip column should match historical
     live $/trade within ±15% on cells with n≥10 fills.

VARIANCE TRIGGER:
  If calibration moves backtest dollars by > 50% in dollar terms vs
  the previous gross-only run, the prior gross-only backtests were
  severely misleading and ALL prior cell promotion decisions should
  be re-reviewed. (Specifically: any cell currently in
  state/strategy_validation.json:live_allowlist that was promoted
  based on gross R-multiples needs to be re-evaluated against
  measured-slippage net dollars.)

═══════════════════════════════════════════════════════════════════

INPUTS:
  state/fund.db:orders                      — filled live_trader orders
  vault/research/live_slippage/<latest>     — existing per-cell slippage

OUTPUT:
  state/measured_slippage.json              — schema documented below

OUTPUT SCHEMA:
  {
    "generated_at": "ISO timestamp",
    "n_fills_total": N,
    "min_fills_per_cell_for_use": 5,
    "per_symbol_ticks_per_side": {
      "ZN": {"mean": 0.18, "median": 0.10, "n": 23, "use": true},
      "ZB": {"mean": 0.45, "median": 0.30, "n": 8, "use": true},
      "ZT": {"mean": 0.05, "median": 0.00, "n": 3, "use": false},  // n<5
      ...
    },
    "per_cell_ticks_per_side": {
      "gap_fill|ZN|Asian|long":  {"mean": 0.20, "n": 8},
      "gap_fill|ZN|Asian|short": {"mean": 0.15, "n": 7},
      ...
    },
    "fallback_default_ticks_per_side": 0.25
  }

CONSUMER PATTERN (to be wired into param_sweep.py + backtest engine
later):
  from scripts.slippage_calibration import load_measured_slippage
  slip = load_measured_slippage()
  ticks = slip.lookup_for_cell(strategy, symbol, session, side,
                                fallback="symbol")  # then global default

USAGE:
  python -m scripts.slippage_calibration              # read+write
  python -m scripts.slippage_calibration --print
  python -m scripts.slippage_calibration --dry-run    # don't write file
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "state" / "fund.db"
OUT_PATH = PROJECT_ROOT / "state" / "measured_slippage.json"

# Mirrors slippage_tracker.py and slippage_tracker_extended.py
TICK_BY_SYMBOL = {
    "ZN": 0.015625, "ZB": 0.03125, "ZT": 0.0078125, "ZF": 0.0078125,
    "NG": 0.001, "GC": 0.10, "6E": 0.00005,
    "MES": 0.25, "MNQ": 0.25, "MCL": 0.01,
    "ES": 0.25, "NQ": 0.25, "CL": 0.01,
}

# Minimum fills required before we trust measured slippage. Below this,
# fall back to predicted/default.
MIN_FILLS_FOR_USE = 5
# Default fallback when no measurement available — tracks CC's
# slippage finding (gap_fill_wide deployment baseline).
FALLBACK_DEFAULT_TICKS_PER_SIDE = 0.25


def load_fills() -> list[dict]:
    """Load filled live_trader entry orders from state/fund.db."""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT client_order_id, symbol, side, limit_price, stop_price, "
        "  ts_proposed, ts_filled, avg_fill_price, qty "
        "FROM orders "
        "WHERE agent = 'live_trader' "
        "  AND avg_fill_price IS NOT NULL "
        "  AND avg_fill_price > 0"
    ).fetchall()
    return [dict(r) for r in rows]


def session_for_hour_utc(h: int) -> str:
    """Map UTC hour to session (rough ET conversion). Mirrors regime_classifier."""
    et_h = (h - 4) % 24   # rough ET (DST-ignorant; close enough for sessions)
    if 18 <= et_h or et_h < 4:    return "Asian"
    if 4 <= et_h < 9.5:           return "London"
    if 9.5 <= et_h < 16:          return "RTH"
    return "PostClose"


def compute_slip_ticks(row: dict) -> float | None:
    """Compute per-fill slippage in ticks (positive = adverse to us).
    Returns None if uncomputable."""
    sym = row.get("symbol")
    tick = TICK_BY_SYMBOL.get(sym)
    if not tick:
        return None
    cid = row.get("client_order_id") or ""
    if cid.endswith("_stop"):
        intent = row.get("stop_price")
    else:
        intent = row.get("limit_price")   # entry or target
    if intent is None or intent <= 0:
        return None
    actual = float(row["avg_fill_price"])
    side = (row.get("side") or "").lower()
    slip_price = (actual - float(intent)) if side == "buy" else (float(intent) - actual)
    return slip_price / tick


def derive_cell_key(row: dict, strategy: str = "?") -> str:
    """Build (strategy, symbol, session, side) cell key. Strategy is
    not in the orders table directly — defaults to '?' for now. Future
    enhancement: join via decisions table to attribute strategy."""
    sym = row.get("symbol", "?")
    side = (row.get("side") or "?").lower()
    # Map buy/sell back to long/short for entries (stops/targets reverse)
    cid = row.get("client_order_id") or ""
    if cid.endswith("_stop") or cid.endswith("_target"):
        # Reverse — stop on a long is a sell; we want the original side
        side = "long" if side == "sell" else "short"
    elif side == "buy":
        side = "long"
    elif side == "sell":
        side = "short"
    # Session from ts_filled or ts_proposed
    ts = row.get("ts_filled") or row.get("ts_proposed") or ""
    sess = "?"
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        sess = session_for_hour_utc(dt.astimezone(timezone.utc).hour)
    except Exception:
        pass
    return f"{strategy}|{sym}|{sess}|{side}"


def calibrate(rows: list[dict]) -> dict:
    """Compute per-symbol and per-cell measured slippage.

    Only considers ENTRY legs (cid not ending in _stop or _target) —
    those are where the trader actually crosses the spread.
    """
    per_sym: dict[str, list[float]] = defaultdict(list)
    per_cell: dict[str, list[float]] = defaultdict(list)
    n_total = 0
    for r in rows:
        cid = r.get("client_order_id") or ""
        if cid.endswith("_stop") or cid.endswith("_target"):
            continue
        slip = compute_slip_ticks(r)
        if slip is None:
            continue
        n_total += 1
        sym = r.get("symbol")
        per_sym[sym].append(slip)
        cell = derive_cell_key(r)
        per_cell[cell].append(slip)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_fills_total": n_total,
        "min_fills_per_cell_for_use": MIN_FILLS_FOR_USE,
        "fallback_default_ticks_per_side": FALLBACK_DEFAULT_TICKS_PER_SIDE,
        "per_symbol_ticks_per_side": {},
        "per_cell_ticks_per_side": {},
    }
    for sym, slips in per_sym.items():
        n = len(slips)
        out["per_symbol_ticks_per_side"][sym] = {
            "mean": mean(slips),
            "median": median(slips),
            "n": n,
            "use": n >= MIN_FILLS_FOR_USE,
        }
    for cell, slips in per_cell.items():
        n = len(slips)
        out["per_cell_ticks_per_side"][cell] = {
            "mean": mean(slips),
            "median": median(slips),
            "n": n,
            "use": n >= MIN_FILLS_FOR_USE,
        }
    return out


# ── Consumer API ───────────────────────────────────────────────

class MeasuredSlippage:
    """Read-only accessor for the calibration output. Use this from
    param_sweep.py / backtest harness to inject measured slippage into
    sweeps."""

    def __init__(self, payload: dict):
        self.payload = payload
        self.fallback = float(payload.get("fallback_default_ticks_per_side",
                                           FALLBACK_DEFAULT_TICKS_PER_SIDE))

    @classmethod
    def load(cls, path: Path = OUT_PATH) -> "MeasuredSlippage":
        if not path.exists():
            return cls({"per_symbol_ticks_per_side": {},
                        "per_cell_ticks_per_side": {}})
        try:
            return cls(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return cls({"per_symbol_ticks_per_side": {},
                        "per_cell_ticks_per_side": {}})

    def lookup_for_cell(self, strategy: str, symbol: str,
                        session: str, side: str,
                        fallback: str = "symbol") -> float:
        """Look up per-cell measured slippage. If cell n < min, fall
        back to per-symbol (or "default" → global fallback).

        Returns ticks per side (positive number; means adverse).
        """
        cell_key = f"{strategy}|{symbol}|{session}|{side}"
        cell = self.payload.get("per_cell_ticks_per_side", {}).get(cell_key)
        if cell and cell.get("use"):
            return float(cell["mean"])
        if fallback == "symbol":
            sym = self.payload.get("per_symbol_ticks_per_side", {}).get(symbol)
            if sym and sym.get("use"):
                return float(sym["mean"])
        return self.fallback


def load_measured_slippage(path: Path = OUT_PATH) -> MeasuredSlippage:
    return MeasuredSlippage.load(path)


# ── main ───────────────────────────────────────────────────────

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--print", dest="do_print", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="Compute + print but don't write the JSON file.")
    args = p.parse_args()

    rows = load_fills()
    n_fills = len(rows)
    print(f"Loaded {n_fills} filled live_trader orders.")

    payload = calibrate(rows)

    if args.do_print or args.dry_run:
        print()
        print("Per-symbol measured slippage (entries only):")
        for sym, s in payload["per_symbol_ticks_per_side"].items():
            flag = " [usable]" if s["use"] else " [n<min, falls back]"
            print(f"  {sym}: mean={s['mean']:+.3f} median={s['median']:+.3f} "
                  f"n={s['n']}{flag}")
        if payload["per_cell_ticks_per_side"]:
            print()
            print("Per-cell measured slippage:")
            for cell, s in payload["per_cell_ticks_per_side"].items():
                flag = " [usable]" if s["use"] else ""
                print(f"  {cell}: mean={s['mean']:+.3f} n={s['n']}{flag}")

    if args.dry_run:
        print()
        print("(--dry-run — no file written)")
        return 0

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH.relative_to(PROJECT_ROOT)}  "
          f"(n_fills={n_fills}, "
          f"per-symbol entries={len(payload['per_symbol_ticks_per_side'])}, "
          f"per-cell entries={len(payload['per_cell_ticks_per_side'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
