"""Model expected returns + Combine pass probability for top strategies
across slippage levels.

For each candidate strategy:
1. Apply live_trader's gating (8/day cap, 45-min cooldown, $150 per-trade cap, DLL)
2. Compute daily P&L at slippage levels [0, 0.10, 0.25, 0.50, 1.0] per side
3. Bootstrap 30-day Combine runs (5,000 sims each)
4. Report prob_profit, prob_hit_$3k, prob_bust_$2k, P&L distribution

Strategies modeled:
- gap_fill (current allowlist baseline)
- gap_fill_wide (slippage-resistant alternative)
- rsi2_extreme_reversion (tail-driven option)
- "best_mix" — top per-cell candidates from grid analysis
"""
from __future__ import annotations

import math
import random
import sys
import warnings
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.backtest import strategies as strats  # noqa: E402

SYMBOL_SPECS = {
    "ZN": {"tick_size": 0.015625, "tick_value": 15.625, "yf": "ZN=F"},
    "ZB": {"tick_size": 0.03125,  "tick_value": 31.25,  "yf": "ZB=F"},
    "ZT": {"tick_size": 0.0078125, "tick_value": 15.625, "yf": "ZT=F"},
    "ZF": {"tick_size": 0.0078125, "tick_value": 7.8125, "yf": "ZF=F"},
    "NG": {"tick_size": 0.001,    "tick_value": 10.00,  "yf": "NG=F"},
    "GC": {"tick_size": 0.10,     "tick_value": 10.00,  "yf": "GC=F"},
    "6E": {"tick_size": 0.00005,  "tick_value": 6.25,   "yf": "6E=F"},
    "ES": {"tick_size": 0.25,     "tick_value": 12.50,  "yf": "ES=F"},
    "NQ": {"tick_size": 0.25,     "tick_value": 5.00,   "yf": "NQ=F"},
    "CL": {"tick_size": 0.01,     "tick_value": 10.00,  "yf": "CL=F"},
}

PER_TRADE_LOSS_CAP_USD = 150.0
DLL_USD = 1000.0
TDD_USD = 2000.0
MAX_TRADES_PER_DAY = 8
COOLDOWN_MIN = 45
COMBINE_TARGET_USD = 3000.0
RT_FEE = 4.80


def fetch_bars(yf_ticker: str) -> pd.DataFrame:
    df = yf.download(yf_ticker, period="60d", interval="5m",
                     progress=False, auto_adjust=False)
    if hasattr(df.columns, "get_level_values"):
        df.columns = df.columns.get_level_values(0)
    df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df.index = df.index.tz_convert("America/New_York")
    return df


def simulate_outcome(event, bars):
    forward = bars[bars.index > event["ts"]]
    if len(forward) == 0:
        return event["entry"], "no_data"
    for ts, row in forward.iterrows():
        hi, lo = float(row["High"]), float(row["Low"])
        if event["side"] == "long":
            if lo <= event["stop"]: return event["stop"], "stop"
            if event.get("target") and hi >= event["target"]:
                return event["target"], "target"
        else:
            if hi >= event["stop"]: return event["stop"], "stop"
            if event.get("target") and lo <= event["target"]:
                return event["target"], "target"
        if (ts - event["ts"]) > timedelta(hours=8):
            return float(row["Close"]), "timeout"
    return float(forward.iloc[-1]["Close"]), "eod"


def size(stop_dollars):
    if stop_dollars <= 0: return 0
    return max(0, min(math.floor(PER_TRADE_LOSS_CAP_USD / stop_dollars), 5))


def simulate_strategy_daily_pnl(strategy_fn, symbols_with_bars, slip_per_side):
    """Run strategy with live_trader gating; return list of daily P&Ls."""
    daily_pnl = defaultdict(float)
    daily_count = defaultdict(int)
    last_trade_per_sym = {}
    halted = set()

    # Generate all events across symbols, sort by ts
    all_events = []
    for sym, bars in symbols_with_bars.items():
        spec = SYMBOL_SPECS[sym]
        try:
            sigs = list(strategy_fn(bars))
        except Exception:
            continue
        for s in sigs:
            if s.kind != "entry": continue
            if not s.stop: continue
            ts = s.date if s.date.tzinfo else s.date.tz_localize("UTC")
            ts_et = ts.tz_convert("America/New_York")
            all_events.append({
                "ts": ts_et, "symbol": sym, "side": s.side,
                "entry": s.price, "stop": s.stop, "target": s.target,
                "spec": spec, "bars": bars,
            })
    all_events.sort(key=lambda e: e["ts"])

    # Apply gates and simulate
    for ev in all_events:
        day = ev["ts"].date()
        if day in halted: continue
        if daily_count[day] >= MAX_TRADES_PER_DAY: continue
        last_t = last_trade_per_sym.get(ev["symbol"])
        if last_t and (ev["ts"] - last_t) < timedelta(minutes=COOLDOWN_MIN):
            continue
        spec = ev["spec"]
        stop_dist = abs(ev["entry"] - ev["stop"])
        stop_dollars = (stop_dist / spec["tick_size"]) * spec["tick_value"]
        n_contracts = size(stop_dollars)
        if n_contracts == 0: continue
        exit_price, _ = simulate_outcome(ev, ev["bars"])
        if ev["side"] == "long":
            pnl_price = exit_price - ev["entry"]
        else:
            pnl_price = ev["entry"] - exit_price
        pnl_dollars = (pnl_price / spec["tick_size"]) * spec["tick_value"]
        slip = slip_per_side * spec["tick_value"] * 2 * n_contracts
        pnl_total = pnl_dollars * n_contracts - RT_FEE * n_contracts - slip
        daily_pnl[day] += pnl_total
        daily_count[day] += 1
        last_trade_per_sym[ev["symbol"]] = ev["ts"]
        if daily_pnl[day] <= -DLL_USD:
            halted.add(day)

    return list(daily_pnl.values()) or [0]


def bootstrap_combine(daily_pnls, n_sims=5000, sim_days=30):
    """Bootstrap 30-day Combine runs. Returns dict of probabilities."""
    random.seed(42)
    pass_count = 0
    bust_count = 0
    profit_count = 0
    final_pnls = []
    for _ in range(n_sims):
        cum = 0; peak = 0; mdd = 0; passed = False; busted = False
        for d in range(sim_days):
            cum += random.choice(daily_pnls)
            if cum > peak: peak = cum
            mdd = max(mdd, peak - cum)
            if mdd >= TDD_USD:
                bust_count += 1; busted = True; break
            if cum >= COMBINE_TARGET_USD and not passed:
                pass_count += 1; passed = True
        final_pnls.append(cum)
        if cum > 0: profit_count += 1
    final_pnls.sort()
    return {
        "prob_pass": pass_count / n_sims,
        "prob_bust": bust_count / n_sims,
        "prob_profit": profit_count / n_sims,
        "p5": final_pnls[int(n_sims * 0.05)],
        "p50": final_pnls[int(n_sims * 0.50)],
        "p95": final_pnls[int(n_sims * 0.95)],
    }


def main():
    print("=" * 84)
    print("STRATEGY RETURNS MODELING with slippage sensitivity")
    print("=" * 84)

    # Fetch bars
    bars_by_sym = {}
    for sym, spec in SYMBOL_SPECS.items():
        try:
            bars_by_sym[sym] = fetch_bars(spec["yf"])
            if len(bars_by_sym[sym]) < 100:
                del bars_by_sym[sym]
        except Exception:
            pass
    print(f"Bars fetched for: {sorted(bars_by_sym.keys())}")

    # Subsets per strategy candidate
    treasuries = {k: v for k, v in bars_by_sym.items() if k in ("ZN","ZB","ZT","ZF")}
    extended = {k: v for k, v in bars_by_sym.items()
                if k in ("ZN","ZB","ZT","ZF","NG","6E")}
    rsi2_set = {k: v for k, v in bars_by_sym.items()
                if k in ("CL","ES","NG","NQ")}

    candidates = [
        ("gap_fill (current allowlist)", strats.gap_fill, treasuries),
        ("gap_fill_wide on treasuries", strats.gap_fill_wide, treasuries),
        ("gap_fill_wide on extended (+NG, +6E)", strats.gap_fill_wide, extended),
        ("gap_fill on extended (+NG, +6E)", strats.gap_fill, extended),
        ("rsi2_extreme_reversion (CL/ES/NG/NQ)", strats.rsi2_extreme_reversion, rsi2_set),
    ]

    SLIPPAGES = [0.0, 0.10, 0.25, 0.50, 1.0]

    print()
    print(f"{'STRATEGY':<40} {'slip':>5}  {'days':>5}  {'60d P&L':>10}  "
          f"{'mean/d':>8}  {'P_pass':>7}  {'P_bust':>7}  {'P_prof':>7}  {'p50_30d':>9}")
    print("-" * 130)

    for label, fn, syms in candidates:
        for slip in SLIPPAGES:
            daily = simulate_strategy_daily_pnl(fn, syms, slip)
            total_60d = sum(daily)
            mean_d = total_60d / max(1, len(daily))
            stats = bootstrap_combine(daily)
            print(f"{label:<40} {slip:>5}  {len(daily):>5}  ${total_60d:>+9,.0f}  "
                  f"${mean_d:>+7,.0f}  {stats['prob_pass']*100:>5.0f}%  "
                  f"{stats['prob_bust']*100:>5.0f}%  {stats['prob_profit']*100:>5.0f}%  "
                  f"${stats['p50']:>+8,.0f}")
        print()


if __name__ == "__main__":
    main()
