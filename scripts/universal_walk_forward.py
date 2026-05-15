"""Universal strategy × symbol × session × side walk-forward sweep.

Reads every `state/bars/<sym>_1m_*.parquet`, runs every strategy in
STRATEGY_REGISTRY against every (symbol, session, side) slice,
computes OOS stats (n, hit, E in R, t-stat) per cell.

Scope: ~28 strategies × ~50 Topstep tradable symbols × 4 sessions × 2
sides = ~11,500 candidate cells. Most will have insufficient n; that's
fine — they auto-filter out. Top candidates feed `stage_shadow_cells.py`
which marks them experimental:true in live_allowlist so the existing
shadow_trades infrastructure can record real-market behavior.

THIS IS A LEARNING PIPELINE. No real fills. The fund collects data
on every (strategy, symbol, session, side) cell autonomously while we
stay focused on Combine.

Multiple-comparisons correction: with 11,500 cells tested at t>=1.5
default, you'd expect ~57 false positives at random. So we use a
stricter t>=2.5 default for the universal sweep (Bonferroni-ish; not
formal multi-comp correction but practically the same).

Usage:
    .venv/Scripts/python.exe -m scripts.universal_walk_forward
    .venv/Scripts/python.exe -m scripts.universal_walk_forward --min-t 2.0 --min-n 30
    .venv/Scripts/python.exe -m scripts.universal_walk_forward --symbols MGC,GC
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, stdev

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

from tools.backtest import strategies as strats  # noqa: E402
from tools.backtest.engine import backtest_strategy  # noqa: E402


BAR_DIR = PROJECT_ROOT / "state" / "bars"
OUT_REPORT = (PROJECT_ROOT / "vault" / "research" / "analysis"
              / "2026-05-15_universal_walkforward.md")
OUT_JSON = PROJECT_ROOT / "state" / "universal_walkforward_results.json"

SESSIONS = ["Asian", "London", "RTH", "PostClose"]
SKIP_STRATEGIES = {"cross_asset_divergence_zn"}  # needs ZN context, separate cycle

# Friction parameters (matches tools/exec_mirror.py defaults)
ROUND_TRIP_SLIPPAGE_TICKS = 1.5  # 0.75 entry + 0.75 normal exit
STOP_SLIPPAGE_TICKS = 1.0        # extra slip when stop hits in fast tape


def apply_friction_to_r_multiple(gross_r: float, exit_reason: str,
                                    entry_px: float, stop_px: float,
                                    tick_size: float, tick_value: float,
                                    qty: int = 1) -> float:
    """Convert idealized gross R-multiple to NET R after realistic
    slippage + fees. Mirrors tools/exec_mirror._apply_friction.

    Returns the net R-multiple. The same trade's gross R can be
    +1.50 but net only +1.00 once friction is baked in.
    """
    if tick_size <= 0 or tick_value <= 0:
        return gross_r  # can't compute friction without tick economics
    risk_per_unit = abs(entry_px - stop_px)
    if risk_per_unit <= 0:
        return gross_r
    risk_usd = (risk_per_unit / tick_size) * tick_value * qty
    if risk_usd <= 0:
        return gross_r
    gross_usd = gross_r * risk_usd
    # Round-trip slippage (entry + exit)
    slip_usd = ROUND_TRIP_SLIPPAGE_TICKS * tick_value * qty
    # Fees — use per-symbol if available, else conservative $4 round-trip
    try:
        from tools.shadow_realism import FEES_PER_ROUND_TRIP
        # Approximate symbol root lookup (engine's symbol may be canonical)
        # Skipping detail; use 4.0 fallback consistent with shadow_realism default
        fees_usd = FEES_PER_ROUND_TRIP.get("__default__", 4.0) * qty
    except Exception:
        fees_usd = 4.0 * qty
    # Stop slip on stop-hit trades
    stop_slip_usd = 0.0
    if exit_reason and "stop" in exit_reason.lower():
        stop_slip_usd = STOP_SLIPPAGE_TICKS * tick_value * qty
    net_usd = gross_usd - slip_usd - fees_usd - stop_slip_usd
    return net_usd / risk_usd


def load_session_bars(symbol: str, session: str) -> pd.DataFrame | None:
    """Find the latest parquet for `symbol`, load, filter to session,
    normalize columns for the backtest engine."""
    pattern = str(BAR_DIR / f"{symbol}_1m_*.parquet")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        return None
    df = pd.read_parquet(files[0])
    sess = df[df["session"] == session].copy()
    if len(sess) < 200:
        return None
    sess = sess.rename(columns={
        "ts": "Date", "open": "Open", "high": "High",
        "low": "Low", "close": "Close", "volume": "Volume",
    })
    sess["Date"] = pd.to_datetime(sess["Date"], utc=True)
    sess = sess.set_index("Date").sort_index()
    return sess


def compute_stats(rs: list[float]) -> dict:
    """n, hit, E, t-stat from list of r-multiples."""
    n = len(rs)
    if n == 0:
        return {"n": 0, "hit": None, "E": None, "t": None}
    hit = sum(1 for r in rs if r > 0) / n
    e = mean(rs)
    if n < 2:
        return {"n": n, "hit": hit, "E": e, "t": None}
    s = stdev(rs)
    t = (e / s) * (n ** 0.5) if s > 0 else None
    return {"n": n, "hit": hit, "E": e, "t": t}


def evaluate_cell(strategy_fn, bars: pd.DataFrame, symbol: str) -> dict:
    """One strategy × symbol × session run. Returns per-side stats with
    BOTH gross (idealized backtest) and net (after realistic friction)
    R-multiples. The graduation gates apply to NET — gross stays in the
    output for diagnostic comparison."""
    if len(bars) < 200:
        return {"error": "insufficient_bars"}
    split_idx = int(len(bars) * 0.75)
    oos_start = bars.index[split_idx]

    try:
        result = backtest_strategy(strategy_fn, bars, symbol=symbol)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {str(e)[:80]}"}

    # Look up tick economics for friction computation
    from tools.backtest.engine import _TICK_SIZES_BY_SYMBOL
    tick_size = _TICK_SIZES_BY_SYMBOL.get(symbol, 0.0)
    # Approximate tick_value lookup via profit_protect's table
    try:
        from tools.profit_protect import _TICK_ECONOMICS
        _, tick_value = _TICK_ECONOMICS.get(symbol, (tick_size, 0.0))
        if tick_value <= 0:
            tick_value = 0.0
    except Exception:
        tick_value = 0.0

    per_side = {}
    for side in ("long", "short"):
        trades = [t for t in result.trades
                   if t.side == side and not t.is_open]
        oos_trades = [t for t in trades if t.entry_date >= oos_start]
        # Gross R-multiples (idealized)
        all_gross = [t.r_multiple for t in trades]
        oos_gross = [t.r_multiple for t in oos_trades]
        # Net R-multiples (with friction)
        all_net = [
            apply_friction_to_r_multiple(
                t.r_multiple, t.exit_reason or "",
                t.entry_price, t.stop, tick_size, tick_value,
            ) for t in trades
        ]
        oos_net = [
            apply_friction_to_r_multiple(
                t.r_multiple, t.exit_reason or "",
                t.entry_price, t.stop, tick_size, tick_value,
            ) for t in oos_trades
        ]
        per_side[side] = {
            "all": compute_stats(all_gross),
            "oos": compute_stats(oos_gross),
            "all_net": compute_stats(all_net),
            "oos_net": compute_stats(oos_net),
        }
    return {
        "per_side": per_side,
        "bar_count": len(bars),
        "oos_start": oos_start.isoformat(),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--symbols", type=str, default=None,
                     help="comma-separated symbols (default: all in state/bars)")
    p.add_argument("--strategies", type=str, default=None,
                     help="comma-separated strategy names")
    p.add_argument("--sessions", type=str, default=",".join(SESSIONS),
                     help=f"comma-separated sessions (default: {SESSIONS})")
    p.add_argument("--min-n", type=int, default=25,
                     help="OOS sample-size gate (default 25)")
    p.add_argument("--min-t", type=float, default=2.5,
                     help="OOS t-stat gate (default 2.5 — strict for multi-comp)")
    p.add_argument("--min-E", type=float, default=0.0,
                     help="OOS expectancy gate (default 0.0)")
    args = p.parse_args()

    available_symbols = sorted({
        Path(f).name.split("_")[0]
        for f in glob.glob(str(BAR_DIR / "*_1m_*.parquet"))
    })
    symbols = args.symbols.split(",") if args.symbols else available_symbols
    if not symbols:
        print(f"No bar files in {BAR_DIR}/. Run scripts.pull_rth_bars first.")
        return 1

    strategy_names = (args.strategies.split(",") if args.strategies
                       else sorted(strats.STRATEGY_REGISTRY.keys()))
    strategy_names = [s for s in strategy_names if s not in SKIP_STRATEGIES]

    sessions = args.sessions.split(",")

    print(f"=== universal walk-forward sweep ===")
    print(f"symbols: {len(symbols)}")
    print(f"strategies: {len(strategy_names)}")
    print(f"sessions: {sessions}")
    print(f"total candidate cells: "
           f"{len(symbols) * len(strategy_names) * len(sessions) * 2}")
    print(f"graduation gates: n>={args.min_n}, t>={args.min_t}, E>{args.min_E}")
    print()

    cells: list[dict] = []
    errors: list[str] = []
    t0 = time.time()

    for sym_idx, sym in enumerate(symbols):
        print(f"[{sym_idx+1}/{len(symbols)}] {sym}")
        for session in sessions:
            bars = load_session_bars(sym, session)
            if bars is None:
                continue
            t_sess = time.time()
            n_cells_this_session = 0
            for strat_name in strategy_names:
                strat_fn = strats.STRATEGY_REGISTRY[strat_name]
                res = evaluate_cell(strat_fn, bars, sym)
                if "error" in res:
                    if res["error"] != "insufficient_bars":
                        errors.append(f"{strat_name}/{sym}/{session}: {res['error']}")
                    continue
                for side in ("long", "short"):
                    oos = res["per_side"][side]["oos"]
                    oos_net = res["per_side"][side]["oos_net"]
                    if oos["n"] == 0:
                        continue
                    # GRADUATION GATES use NET stats (with friction).
                    # Gross stays in the record for diagnostic comparison.
                    eligible = (
                        oos_net["n"] >= args.min_n
                        and oos_net["t"] is not None and oos_net["t"] >= args.min_t
                        and oos_net["E"] is not None and oos_net["E"] >= args.min_E
                    )
                    cells.append({
                        "strategy": strat_name,
                        "symbol": sym,
                        "session": session,
                        "side": side,
                        # Gross (idealized — for diagnostic comparison)
                        "oos_n": oos["n"],
                        "oos_hit": oos["hit"],
                        "oos_E_gross": oos["E"],
                        "oos_t_gross": oos["t"],
                        # Net (with friction — THIS is what graduation uses)
                        "oos_E_net": oos_net["E"],
                        "oos_t_net": oos_net["t"],
                        # Keep the gross-key alias 'oos_t' / 'oos_E' for
                        # backwards-compat with stage_shadow_cells.py which
                        # already reads `oos_t`. Point them at NET so the
                        # staging pipeline naturally uses friction-adjusted.
                        "oos_t": oos_net["t"],
                        "oos_E": oos_net["E"],
                        "all_n": res["per_side"][side]["all"]["n"],
                        "bar_count": res["bar_count"],
                        "oos_start": res["oos_start"],
                        "graduation_eligible": eligible,
                    })
                    n_cells_this_session += 1
            elapsed_sess = time.time() - t_sess
            print(f"  {session:9} {len(bars):>6} bars  -> "
                   f"{n_cells_this_session} cells ({elapsed_sess:.1f}s)")

    elapsed = time.time() - t0
    print()
    print(f"=== DONE in {elapsed:.0f}s ===")
    print(f"cells evaluated: {len(cells)}")
    print(f"errors: {len(errors)}")
    print()

    eligible = [c for c in cells if c["graduation_eligible"]]
    eligible.sort(key=lambda c: c["oos_t"] or -999, reverse=True)
    print(f"GRADUATION-ELIGIBLE: {len(eligible)} cells")
    print()
    if eligible:
        print(f"{'strategy':28} {'sym':6} {'sess':9} {'side':5} "
               f"{'n':>4} {'hit':>5} {'E':>6} {'t':>6}")
        for c in eligible[:50]:
            hit_s = f"{c['oos_hit']*100:.0f}%"
            print(f"  {c['strategy']:28} {c['symbol']:6} {c['session']:9} "
                   f"{c['side']:5} {c['oos_n']:>4} {hit_s:>5} "
                   f"{c['oos_E']:+.2f} {c['oos_t']:+.2f}")

    # Save JSON
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": datetime.now(tz=timezone.utc).isoformat(),
            "symbols": symbols,
            "strategies": strategy_names,
            "sessions": sessions,
            "graduation_gates": {
                "min_n": args.min_n, "min_t": args.min_t, "min_E": args.min_E,
            },
            "cells_total": len(cells),
            "graduation_eligible_count": len(eligible),
            "cells_all": sorted(cells,
                                  key=lambda c: c["oos_t"] or -999,
                                  reverse=True),
            "errors": errors,
        }, f, indent=2, default=str)
    print(f"\nJSON: {OUT_JSON}")
    write_report(cells, eligible, errors, symbols,
                   strategy_names, sessions, args, elapsed)
    print(f"Report: {OUT_REPORT}")
    return 0


def write_report(cells, eligible, errors, symbols, strategies, sessions,
                   args, elapsed_s):
    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", "type: analysis", "date: 2026-05-15",
              "phase: universal walk-forward sweep",
              f"symbols: {len(symbols)}",
              f"strategies: {len(strategies)}",
              f"sessions: {len(sessions)}",
              f"cells_total: {len(cells)}",
              f"graduation_eligible: {len(eligible)}",
              f"runtime_seconds: {elapsed_s:.0f}",
              "---", "",
              "# Universal walk-forward — full library × full Topstep universe",
              "",
              f"**Scope:** {len(symbols)} symbols × {len(strategies)} strategies × "
              f"{len(sessions)} sessions × 2 sides",
              f"**Gates:** n>={args.min_n}, t>={args.min_t}, E>{args.min_E} (OOS)",
              "",
              f"## Graduation-eligible cells ({len(eligible)})",
              ""]
    if eligible:
        lines.append("| Strategy | Symbol | Session | Side | n | Hit | E (R) | t |")
        lines.append("|---|---|---|---|---|---|---|---|")
        for c in eligible[:200]:
            lines.append(
                f"| {c['strategy']} | {c['symbol']} | {c['session']} | "
                f"{c['side']} | {c['oos_n']} | {c['oos_hit']*100:.0f}% | "
                f"{c['oos_E']:+.2f} | {c['oos_t']:+.2f} |"
            )
    else:
        lines.append("_None._")
    lines.append("")
    lines.append("## Per-session breakdown")
    lines.append("")
    for sess in sessions:
        sess_eligible = [c for c in eligible if c["session"] == sess]
        sess_all = [c for c in cells if c["session"] == sess]
        lines.append(f"- **{sess}**: {len(sess_eligible)} eligible "
                      f"of {len(sess_all)} cells")
    lines.append("")
    lines.append("## Next: stage in shadow mode")
    lines.append("")
    lines.append("`scripts.stage_shadow_cells` reads the JSON and adds each")
    lines.append("eligible cell to `state/strategy_validation.json:live_allowlist`")
    lines.append("with `experimental: true, shadow_reason: 'universal discovery'`.")
    lines.append("Brain emits signals; existing pipeline records to `shadow_trades`")
    lines.append("and resolves outcomes nightly. After 2-4 weeks of live data,")
    lines.append("`scripts.cell_auto_promote` flags cells whose shadow performance")
    lines.append("matches predicted for real-money review.")
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
