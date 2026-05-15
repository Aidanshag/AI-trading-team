"""Walk-forward validation against RTH 1-min bars for every available
strategy × symbol combination. Phase 1 of the RTH expansion plan.

Reads `state/bars/<sym>_1m_*.parquet` (created by `scripts/pull_rth_bars.py`),
filters to session=RTH, runs each strategy in STRATEGY_REGISTRY, splits
75/25 train/OOS chronologically, computes OOS stats (n, hit, E in R,
t-stat) per (strategy, symbol, side) cell.

Output:
  1. Console-readable ranked table (top by OOS t-stat)
  2. Markdown report at `vault/research/analysis/2026-05-15_rth_walkforward.md`
  3. JSON dump at `state/strategy_validation_rth_proposals.json` for
     Phase 4 to load when staging cells into live_allowlist

Cells meeting (n >= 25 AND t >= 1.5 AND E > 0) are eligible for Phase 4
shadow deployment. Final decision is user-driven (Phase 4 direction call).

Usage:
    .venv/Scripts/python.exe -m scripts.walk_forward_rth
    .venv/Scripts/python.exe -m scripts.walk_forward_rth --symbols MGC,MNQ
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from tools.backtest import strategies as strats  # noqa: E402
from tools.backtest.engine import backtest_strategy  # noqa: E402


BAR_DIR = PROJECT_ROOT / "state" / "bars"
OUT_REPORT = PROJECT_ROOT / "vault" / "research" / "analysis" / "2026-05-15_rth_walkforward.md"
OUT_JSON = PROJECT_ROOT / "state" / "strategy_validation_rth_proposals.json"

# Cells meeting these gates after OOS are eligible for Phase 4 staging
GRADUATION_MIN_N = 25
GRADUATION_MIN_T = 1.5
GRADUATION_MIN_E = 0.0   # >= 0 in R

# Strategies that need a separate "context" symbol (cross-asset / divergence)
# — skip in this initial sweep. Worth a separate cycle once single-symbol works.
SKIP_STRATEGIES = {
    "cross_asset_divergence_zn",  # needs ZN context
}


def load_rth_bars(symbol: str) -> pd.DataFrame | None:
    """Find the latest parquet for `symbol`, load, filter to RTH, normalize
    columns for the backtest engine (which expects Open/High/Low/Close caps)."""
    pattern = str(BAR_DIR / f"{symbol}_1m_*.parquet")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        return None
    df = pd.read_parquet(files[0])
    # Filter to RTH session
    rth = df[df["session"] == "RTH"].copy()
    if len(rth) < 100:
        return None
    # Rename to capitalized columns the backtest engine expects
    rth = rth.rename(columns={
        "ts": "Date", "open": "Open", "high": "High",
        "low": "Low", "close": "Close", "volume": "Volume",
    })
    rth["Date"] = pd.to_datetime(rth["Date"], utc=True)
    rth = rth.set_index("Date").sort_index()
    return rth


def compute_stats(trades) -> dict:
    """OOS metrics: n, hit-rate, expectancy in R, t-stat."""
    closed = [t for t in trades if not t.is_open]
    if not closed:
        return {"n": 0, "hit": None, "E": None, "t": None}
    rs = [t.r_multiple for t in closed]
    n = len(rs)
    hit = sum(1 for r in rs if r > 0) / n
    e = mean(rs)
    if n < 2:
        t = None
    else:
        s = stdev(rs)
        t = (e / s) * (n ** 0.5) if s > 0 else None
    return {"n": n, "hit": hit, "E": e, "t": t}


def split_trades_by_oos_boundary(trades, oos_start_ts) -> list:
    """Return only trades whose entry_date is on or after `oos_start_ts`."""
    return [t for t in trades if t.entry_date >= oos_start_ts]


def evaluate_cell(strategy_name: str, strategy_fn, bars: pd.DataFrame,
                    symbol: str) -> dict:
    """Run one (strategy, symbol) combination. Returns a result dict per side."""
    if len(bars) < 200:
        return {"error": f"insufficient bars ({len(bars)} < 200)"}

    # 75/25 chronological split
    split_idx = int(len(bars) * 0.75)
    oos_start = bars.index[split_idx]

    try:
        result = backtest_strategy(strategy_fn, bars, symbol=symbol)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}

    # Bucket trades by side
    longs = [t for t in result.trades if t.side == "long"]
    shorts = [t for t in result.trades if t.side == "short"]

    return {
        "long": {
            "all": compute_stats(longs),
            "oos": compute_stats(split_trades_by_oos_boundary(longs, oos_start)),
        },
        "short": {
            "all": compute_stats(shorts),
            "oos": compute_stats(split_trades_by_oos_boundary(shorts, oos_start)),
        },
        "oos_start": oos_start.isoformat(),
        "bar_count": len(bars),
        "split_idx": split_idx,
    }


def is_graduation_eligible(oos_stats: dict) -> bool:
    """Cells eligible to stage in Phase 4 must clear all three gates."""
    n = oos_stats.get("n") or 0
    t = oos_stats.get("t")
    e = oos_stats.get("E")
    if n < GRADUATION_MIN_N:
        return False
    if t is None or t < GRADUATION_MIN_T:
        return False
    if e is None or e < GRADUATION_MIN_E:
        return False
    return True


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", type=str, default=None,
                     help="comma-separated symbols (default: all parquet files in state/bars)")
    p.add_argument("--strategies", type=str, default=None,
                     help="comma-separated strategy names (default: all in registry)")
    args = p.parse_args()

    available_symbols = sorted({
        Path(f).name.split("_")[0]
        for f in glob.glob(str(BAR_DIR / "*_1m_*.parquet"))
    })
    symbols = (args.symbols.split(",") if args.symbols
                else available_symbols)
    if not symbols:
        print(f"No bar files found in {BAR_DIR}/. Run pull_rth_bars.py first.")
        return 1

    strategy_names = (args.strategies.split(",") if args.strategies
                       else sorted(strats.STRATEGY_REGISTRY.keys()))
    strategy_names = [s for s in strategy_names if s not in SKIP_STRATEGIES]

    print(f"=== walk-forward RTH validation ===")
    print(f"symbols: {symbols}")
    print(f"strategies: {len(strategy_names)}")
    print(f"oos split: 75/25 chronological")
    print(f"graduation gates: n>={GRADUATION_MIN_N}, t>={GRADUATION_MIN_T}, E>{GRADUATION_MIN_E}")
    print()

    cells: list[dict] = []  # Each entry = one (strategy, symbol, side) cell
    errors: list[str] = []
    t0 = time.time()

    for sym in symbols:
        bars = load_rth_bars(sym)
        if bars is None:
            errors.append(f"{sym}: no bars or insufficient data")
            continue
        rth_first = bars.index[0]
        rth_last = bars.index[-1]
        print(f"[{sym}] {len(bars)} RTH bars "
               f"({rth_first.strftime('%Y-%m-%d')} -> {rth_last.strftime('%Y-%m-%d')})")

        for strat_name in strategy_names:
            strat_fn = strats.STRATEGY_REGISTRY[strat_name]
            t_strat = time.time()
            res = evaluate_cell(strat_name, strat_fn, bars, sym)
            elapsed = time.time() - t_strat
            if "error" in res:
                errors.append(f"{strat_name}/{sym}: {res['error']}")
                continue
            for side in ("long", "short"):
                oos = res[side]["oos"]
                if oos["n"] == 0:
                    continue  # no OOS trades — silent skip
                cells.append({
                    "strategy": strat_name,
                    "symbol": sym,
                    "side": side,
                    "oos_n": oos["n"],
                    "oos_hit": oos["hit"],
                    "oos_E": oos["E"],
                    "oos_t": oos["t"],
                    "all_n": res[side]["all"]["n"],
                    "oos_start": res["oos_start"],
                    "graduation_eligible": is_graduation_eligible(oos),
                })
            print(f"  {strat_name:30} done in {elapsed:.1f}s")

    elapsed_total = time.time() - t0
    print()
    print(f"=== DONE in {elapsed_total:.0f}s ===")
    print(f"cells evaluated: {len(cells)}")
    print(f"errors: {len(errors)}")

    # Rank by OOS t-stat
    ranked = sorted(
        [c for c in cells if c["oos_t"] is not None],
        key=lambda c: c["oos_t"], reverse=True,
    )

    # Console summary — top 30 by t-stat
    print()
    print(f"--- TOP 30 cells by OOS t-stat ---")
    print(f"{'strategy':28} {'symbol':6} {'side':5} {'n':>4} "
           f"{'hit':>6} {'E':>6} {'t':>6} {'elig':>5}")
    for c in ranked[:30]:
        elig = "yes" if c["graduation_eligible"] else "."
        hit_s = f"{c['oos_hit']*100:.0f}%" if c["oos_hit"] is not None else "-"
        e_s = f"{c['oos_E']:+.2f}" if c["oos_E"] is not None else "-"
        t_s = f"{c['oos_t']:+.2f}" if c["oos_t"] is not None else "-"
        print(f"  {c['strategy']:28} {c['symbol']:6} {c['side']:5} "
               f"{c['oos_n']:>4} {hit_s:>6} {e_s:>6} {t_s:>6} {elig:>5}")

    eligible = [c for c in ranked if c["graduation_eligible"]]
    print()
    print(f"Graduation-eligible cells: {len(eligible)}")
    for c in eligible:
        print(f"  {c['strategy']}/{c['symbol']}/{c['side']}: "
               f"n={c['oos_n']} t={c['oos_t']:+.2f} E={c['oos_E']:+.2f}")

    # Save JSON for Phase 4
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "symbols": symbols,
            "cells_evaluated": len(cells),
            "cells": ranked,
            "graduation_eligible": eligible,
            "errors": errors,
            "graduation_gates": {
                "min_n": GRADUATION_MIN_N,
                "min_t": GRADUATION_MIN_T,
                "min_E": GRADUATION_MIN_E,
            },
        }, f, indent=2, default=str)
    print(f"\nJSON: {OUT_JSON}")

    # Write the markdown report
    write_markdown_report(ranked, eligible, errors, symbols,
                            len(strategy_names), elapsed_total)
    print(f"Report: {OUT_REPORT}")

    return 0 if cells else 1


def write_markdown_report(ranked, eligible, errors, symbols,
                            n_strategies, elapsed_s):
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    lines.append("---")
    lines.append("type: analysis")
    lines.append("date: 2026-05-15")
    lines.append("phase: 1 (walk-forward) of RTH expansion plan")
    lines.append(f"symbols_evaluated: {len(symbols)}")
    lines.append(f"strategies_evaluated: {n_strategies}")
    lines.append(f"cells_total: {len(ranked)}")
    lines.append(f"graduation_eligible: {len(eligible)}")
    lines.append(f"runtime_seconds: {elapsed_s:.0f}")
    lines.append("---")
    lines.append("")
    lines.append("# RTH walk-forward validation — Phase 1 results")
    lines.append("")
    lines.append(f"**Universe:** {len(symbols)} symbols × {n_strategies} strategies × 2 sides")
    lines.append(f"**Window:** 75/25 chronological split per (strategy, symbol)")
    lines.append(f"**Graduation gates:** n>={GRADUATION_MIN_N}, t>={GRADUATION_MIN_T}, E>{GRADUATION_MIN_E}")
    lines.append("")
    lines.append(f"## Graduation-eligible cells ({len(eligible)})")
    lines.append("")
    lines.append("These cells cleared all three gates on the OOS slice and are")
    lines.append("the candidate pool for Phase 4 staged deployment.")
    lines.append("")
    if eligible:
        lines.append("| Strategy | Symbol | Side | OOS n | OOS hit | OOS E (R) | OOS t |")
        lines.append("|---|---|---|---|---|---|---|")
        for c in eligible:
            lines.append(f"| {c['strategy']} | {c['symbol']} | {c['side']} | "
                          f"{c['oos_n']} | {c['oos_hit']*100:.0f}% | "
                          f"{c['oos_E']:+.2f} | {c['oos_t']:+.2f} |")
    else:
        lines.append("_None._")
    lines.append("")
    lines.append(f"## Top 30 cells by OOS t-stat (all)")
    lines.append("")
    lines.append("| Strategy | Symbol | Side | OOS n | OOS hit | OOS E (R) | OOS t | Eligible |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for c in ranked[:30]:
        elig = "✓" if c["graduation_eligible"] else ""
        hit_s = f"{c['oos_hit']*100:.0f}%" if c["oos_hit"] is not None else "-"
        e_s = f"{c['oos_E']:+.2f}" if c["oos_E"] is not None else "-"
        t_s = f"{c['oos_t']:+.2f}" if c["oos_t"] is not None else "-"
        lines.append(f"| {c['strategy']} | {c['symbol']} | {c['side']} | "
                      f"{c['oos_n']} | {hit_s} | {e_s} | {t_s} | {elig} |")
    lines.append("")
    if errors:
        lines.append(f"## Errors / skipped ({len(errors)})")
        lines.append("")
        for e in errors[:30]:
            lines.append(f"- `{e}`")
        if len(errors) > 30:
            lines.append(f"- _(... {len(errors) - 30} more)_")
        lines.append("")
    lines.append("## Next: Phase 2 — parameter calibration")
    lines.append("")
    lines.append("For each graduation-eligible cell, sweep strategy parameters")
    lines.append("(stop ATR multiplier, target ATR multiplier, lookback) to find")
    lines.append("RTH-calibrated values. RTH has higher volume and wider intra-bar")
    lines.append("range than Asian; default params likely too tight.")
    lines.append("")
    lines.append("After Phase 2: review with user for sanity check before Phase 4.")
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
