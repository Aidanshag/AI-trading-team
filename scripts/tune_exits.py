"""Phase 3 — parameter tuning for exit rules.

Sweep the six exit-rule parameters against this week's 27 replayed
trades. Find which combination captures the most P&L without
introducing fragility (a setting that only wins on 1-2 outlier trades
is a bad pick).

Parameters tuned:
  - RETRACE_CAP_FRACTION       (default 0.30)
  - MIN_PEAK_FOR_FLOOR_USD     (default 20)
  - REVERSAL_BARS_REQUIRED     (default 3)
  - REVERSAL_MIN_PEAK_USD      (default 15)
  - TIME_DECAY_MINUTES_STALE   (default 15)
  - TIME_DECAY_RETRACE_FRACTION (default 0.30)

Strategy: one-group-at-a-time grid search. Tune percent-of-peak first
(it's the workhorse — Phase 1 showed ~10 of 27 trades use it). Then
reversal-exit group. Then time-decay group. Combine winners. Validate
the combined set against a held-out subset.

WARNING: only 27 trades in the sample. Heavy risk of overfit. The
output is a STARTING POINT for live shadow validation, not a final
calibrated set.

Usage:
    .venv/Scripts/python.exe -m scripts.tune_exits
"""
from __future__ import annotations

import itertools
import json
import sys
import glob
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

# Reuse logic from replay_exits (don't duplicate the bar loader / trade pair logic)
from scripts.replay_exits import (  # noqa: E402
    TICK, pair_trades, load_bars_for_trade, unrealized_usd,
)


def replay_trade_with_params(trade: dict,
                                retrace_cap: float,
                                min_peak_floor: float,
                                reversal_bars: int,
                                reversal_min_peak: float,
                                time_decay_min: float,
                                time_decay_retrace: float) -> dict:
    """Replay one trade with parameterized exit rules.

    Same algorithm as replay_exits.replay_trade but with parameters
    overridable so we can sweep them.
    """
    sym = trade['sym']; side = trade['side']
    entry_px = trade['entry_px']
    entry_ts = pd.to_datetime(trade['entry_ts'], utc=True)
    actual_exit_ts = pd.to_datetime(trade['exit_ts'], utc=True)
    tick_size = trade['tick_size']; tick_value = trade['tick_value']
    if tick_size == 0:
        return {**trade, 'cf_pnl': None, 'cf_rule': 'no_tick_economics'}

    bars = load_bars_for_trade(sym, trade['entry_ts'], trade['exit_ts'])
    if bars is None or len(bars) == 0:
        return {**trade, 'cf_pnl': None, 'cf_rule': 'no_bars'}

    bars_after = bars[bars['ts'] >= entry_ts].reset_index(drop=True)
    if len(bars_after) == 0:
        return {**trade, 'cf_pnl': None, 'cf_rule': 'no_bars_after_entry'}

    peak = 0.0
    peak_ts = entry_ts
    closes_seen: list[float] = []
    cf_exit_idx = None
    cf_exit_rule = "actual_holdback"

    for i, row in bars_after.iterrows():
        bar_ts = row['ts']
        bar_close = row['close']
        bar_high = row['high']
        bar_low = row['low']

        # Track peak via high/low intrabar
        if side == "long":
            bar_peak_unr = unrealized_usd("long", entry_px, bar_high, tick_size, tick_value)
        else:
            bar_peak_unr = unrealized_usd("short", entry_px, bar_low, tick_size, tick_value)
        if bar_peak_unr > peak:
            peak = bar_peak_unr; peak_ts = bar_ts

        unr = unrealized_usd(side, entry_px, bar_close, tick_size, tick_value)
        closes_seen.append(bar_close)

        # 1. Time decay
        if peak > 0 and peak_ts is not None:
            if (bar_ts - peak_ts).total_seconds() / 60.0 >= time_decay_min:
                if unr < peak * (1.0 - time_decay_retrace):
                    cf_exit_idx = i; cf_exit_rule = "time_decay_exit"; break

        # 2. Reversal
        if peak >= reversal_min_peak and len(closes_seen) >= reversal_bars:
            last = closes_seen[-reversal_bars:]
            if side == "long":
                if all(last[j] < last[j-1] for j in range(1, len(last))):
                    cf_exit_idx = i; cf_exit_rule = "reversal_exit"; break
            else:
                if all(last[j] > last[j-1] for j in range(1, len(last))):
                    cf_exit_idx = i; cf_exit_rule = "reversal_exit"; break

        # 3. Percent-of-peak floor
        if peak >= min_peak_floor:
            floor = max(min_peak_floor, peak * (1.0 - retrace_cap))
            if unr < floor:
                cf_exit_idx = i; cf_exit_rule = "percent_of_peak"; break

        if bar_ts >= actual_exit_ts:
            cf_exit_idx = i; cf_exit_rule = "actual_exit_reached"; break

    if cf_exit_idx is None:
        cf_exit_idx = len(bars_after) - 1
        cf_exit_rule = "end_of_bars"

    exit_bar = bars_after.iloc[cf_exit_idx]
    cf_exit_price = float(exit_bar['close'])
    cf_pnl = unrealized_usd(side, entry_px, cf_exit_price, tick_size, tick_value)
    return {**trade, 'cf_pnl': cf_pnl, 'cf_rule': cf_exit_rule, 'mfe': peak}


def evaluate_params(trades: list[dict], params: dict) -> dict:
    """Run all trades through the parameterized replay and aggregate."""
    results = []
    for t in trades:
        r = replay_trade_with_params(t, **params)
        results.append(r)
    valid = [r for r in results if r.get('cf_pnl') is not None]
    cf_total = sum(r['cf_pnl'] for r in valid)
    actual_total = sum((r.get('actual_pnl') or 0) for r in valid)
    mfe_total = sum((r.get('mfe') or 0) for r in valid)
    # Per-rule firing distribution
    rule_counts = defaultdict(int)
    for r in valid:
        rule_counts[r['cf_rule']] += 1
    return {
        'cf_total': cf_total,
        'actual_total': actual_total,
        'mfe_total': mfe_total,
        'delta_vs_actual': cf_total - actual_total,
        'capture_pct_cf': (cf_total / mfe_total * 100) if mfe_total > 0 else 0,
        'n_trades': len(valid),
        'rules_fired': dict(rule_counts),
    }


def main() -> int:
    orders_path = PROJECT_ROOT / "logs" / "topstep_orders_week.json"
    if not orders_path.exists():
        print(f"ERROR: {orders_path} not found")
        return 1
    with open(orders_path) as f:
        orders = json.load(f)
    trades = pair_trades(orders)
    print(f"Trades paired: {len(trades)}")
    print()

    # Baseline: current defaults
    defaults = {
        'retrace_cap': 0.30,
        'min_peak_floor': 20.0,
        'reversal_bars': 3,
        'reversal_min_peak': 15.0,
        'time_decay_min': 15.0,
        'time_decay_retrace': 0.30,
    }
    baseline = evaluate_params(trades, defaults)
    print(f"=== BASELINE (current defaults) ===")
    print(f"  CF total: ${baseline['cf_total']:+.2f}")
    print(f"  Delta vs actual: ${baseline['delta_vs_actual']:+.2f}")
    print(f"  Rules fired: {baseline['rules_fired']}")
    print()

    # ── Group A: percent-of-peak sweep ──────────────────────────
    print(f"=== GROUP A: percent-of-peak tuning ===")
    a_results = []
    for rc in [0.15, 0.20, 0.25, 0.30, 0.35, 0.40]:
        for mpf in [10, 15, 20, 25, 30]:
            params = {**defaults, 'retrace_cap': rc, 'min_peak_floor': mpf}
            res = evaluate_params(trades, params)
            a_results.append({'retrace_cap': rc, 'min_peak_floor': mpf, **res})
    a_results.sort(key=lambda x: x['cf_total'], reverse=True)
    print(f"  Top 5 by CF total:")
    for r in a_results[:5]:
        print(f"    retrace={r['retrace_cap']:.2f} min_peak=${r['min_peak_floor']:>2.0f}  "
               f"CF=${r['cf_total']:+7.2f}  Delta=${r['delta_vs_actual']:+7.2f}  "
               f"rules={r['rules_fired']}")
    best_a = a_results[0]
    winning_a = {'retrace_cap': best_a['retrace_cap'],
                  'min_peak_floor': best_a['min_peak_floor']}
    print(f"  Winner: {winning_a}")
    print()

    # ── Group B: reversal-exit sweep ────────────────────────────
    print(f"=== GROUP B: reversal-exit tuning (with Group A winner) ===")
    b_results = []
    base_b = {**defaults, **winning_a}
    for rb in [2, 3, 4, 5]:
        for rmp in [5, 10, 15, 20, 25]:
            params = {**base_b, 'reversal_bars': rb, 'reversal_min_peak': rmp}
            res = evaluate_params(trades, params)
            b_results.append({'reversal_bars': rb, 'reversal_min_peak': rmp, **res})
    b_results.sort(key=lambda x: x['cf_total'], reverse=True)
    print(f"  Top 5 by CF total:")
    for r in b_results[:5]:
        print(f"    bars={r['reversal_bars']} min_peak=${r['reversal_min_peak']:>2.0f}  "
               f"CF=${r['cf_total']:+7.2f}  Delta=${r['delta_vs_actual']:+7.2f}  "
               f"rules={r['rules_fired']}")
    best_b = b_results[0]
    winning_b = {'reversal_bars': best_b['reversal_bars'],
                  'reversal_min_peak': best_b['reversal_min_peak']}
    print(f"  Winner: {winning_b}")
    print()

    # ── Group C: time-decay sweep ───────────────────────────────
    print(f"=== GROUP C: time-decay tuning (with A+B winners) ===")
    c_results = []
    base_c = {**defaults, **winning_a, **winning_b}
    for tdm in [5, 10, 15, 20, 30]:
        for tdr in [0.15, 0.20, 0.25, 0.30, 0.40]:
            params = {**base_c, 'time_decay_min': tdm, 'time_decay_retrace': tdr}
            res = evaluate_params(trades, params)
            c_results.append({'time_decay_min': tdm,
                                'time_decay_retrace': tdr, **res})
    c_results.sort(key=lambda x: x['cf_total'], reverse=True)
    print(f"  Top 5 by CF total:")
    for r in c_results[:5]:
        print(f"    min={r['time_decay_min']:>2.0f} retrace={r['time_decay_retrace']:.2f}  "
               f"CF=${r['cf_total']:+7.2f}  Delta=${r['delta_vs_actual']:+7.2f}  "
               f"rules={r['rules_fired']}")
    best_c = c_results[0]
    winning_c = {'time_decay_min': best_c['time_decay_min'],
                  'time_decay_retrace': best_c['time_decay_retrace']}
    print(f"  Winner: {winning_c}")
    print()

    # ── Combined winning params ─────────────────────────────────
    final_params = {**defaults, **winning_a, **winning_b, **winning_c}
    print(f"=== FINAL CALIBRATED PARAMETERS ===")
    for k, v in final_params.items():
        old = defaults[k]
        marker = "*" if v != old else " "
        if isinstance(v, float):
            print(f"  {marker} {k:30} {v:6.2f}  (was {old:.2f})")
        else:
            print(f"  {marker} {k:30} {v:>6}  (was {old})")
    final = evaluate_params(trades, final_params)
    print()
    print(f"  Combined CF total:  ${final['cf_total']:+.2f}")
    print(f"  Delta vs baseline:      ${final['cf_total'] - baseline['cf_total']:+.2f}")
    print(f"  Delta vs actual:        ${final['delta_vs_actual']:+.2f}")
    print(f"  Capture vs MFE:     {final['capture_pct_cf']:.0f}%")
    print(f"  Rules fired:        {final['rules_fired']}")

    # Save winning params for Phase 5 commit
    out_path = PROJECT_ROOT / "vault" / "research" / "analysis" / "2026-05-15_tuned_exit_params.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            'generated_at': datetime.now(tz=timezone.utc).isoformat(),
            'baseline_params': defaults,
            'baseline_cf_total': baseline['cf_total'],
            'winning_params': final_params,
            'winning_cf_total': final['cf_total'],
            'improvement_vs_baseline': final['cf_total'] - baseline['cf_total'],
            'n_trades': final['n_trades'],
            'sample_caveat': '27 trades only — risk of overfitting. Validate via live shadow.',
        }, f, indent=2, default=str)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
