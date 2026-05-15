"""Counterfactual replay — for each of this week's closed trades,
simulate what would have happened with the NEW exit rules shipped
tonight (percent-of-peak retracement + reversal-detection exit +
time-based profit decay + tick-stream).

Compares actual P&L vs counterfactual vs peak MFE. Tells us whether
the execution rebuild actually captures the $527 leakage we measured.

Method:
  1. Pair entry+exit fills from Topstep order history into round-trip trades
  2. For each trade, load 1-min bars from state/bars/<sym>_1m_*.parquet
     between entry_ts and (entry_ts + 90 min) — bound the replay window
  3. Walk bars chronologically tracking peak unrealized
  4. Apply exit rules IN ORDER (first to fire wins):
       a. percent-of-peak floor (max($20, peak * 0.70))
       b. reversal_exit (3 lower closes for long; reverse for short; peak>=$15)
       c. time_decay_exit (>15min stale + >30% retrace)
       d. ACTUAL exit_ts as backstop
  5. Compute counterfactual P&L using bar close at simulated exit time
  6. Output: actual / counterfactual / peak side-by-side

Usage:
    .venv/Scripts/python.exe -m scripts.replay_exits
"""
from __future__ import annotations

import json
import sys
import glob
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd  # noqa: E402

# Tick economics — minimal subset for the symbols we trade
TICK = {
    'MGC': (0.10, 1.0),
    'GC':  (0.10, 10.0),
    'MNQ': (0.25, 0.50),
    'NQ':  (0.25, 5.00),
    'MES': (0.25, 1.25),
    'ES':  (0.25, 12.50),
    'EU6': (0.00005, 6.25),   # Topstep root for 6E
    '6E':  (0.00005, 6.25),
    'NG':  (0.001, 10.0),
    'CL':  (0.01, 10.0),
    'MCL': (0.01, 1.0),
}

# Exit rule parameters (matches tools/profit_protect.py defaults)
RETRACE_CAP_FRACTION = 0.30
MIN_PEAK_FOR_FLOOR_USD = 20.0
REVERSAL_BARS_REQUIRED = 3
REVERSAL_MIN_PEAK_USD = 15.0
TIME_DECAY_MINUTES_STALE = 15
TIME_DECAY_RETRACE_FRACTION = 0.30


def unrealized_usd(side: str, entry_px: float, current_px: float,
                    tick_size: float, tick_value: float) -> float:
    if tick_size <= 0:
        return 0.0
    if side == "long" or side == "BUY":
        ticks = (current_px - entry_px) / tick_size
    else:
        ticks = (entry_px - current_px) / tick_size
    return ticks * tick_value


def compute_active_floor(peak: float) -> float | None:
    if peak < MIN_PEAK_FOR_FLOOR_USD:
        return None
    return max(MIN_PEAK_FOR_FLOOR_USD, peak * (1.0 - RETRACE_CAP_FRACTION))


def detect_reversal(side: str, recent_closes: list[float]) -> bool:
    if len(recent_closes) < REVERSAL_BARS_REQUIRED:
        return False
    last = recent_closes[-REVERSAL_BARS_REQUIRED:]
    if side in ("long", "BUY"):
        return all(last[i] < last[i-1] for i in range(1, len(last)))
    return all(last[i] > last[i-1] for i in range(1, len(last)))


def is_profit_stale(peak: float, peak_ts: datetime,
                      current: float, now: datetime) -> bool:
    if peak <= 0 or peak_ts is None:
        return False
    if current >= peak * (1.0 - TIME_DECAY_RETRACE_FRACTION):
        return False
    elapsed_min = (now - peak_ts).total_seconds() / 60.0
    return elapsed_min >= TIME_DECAY_MINUTES_STALE


def pair_trades(orders: list[dict]) -> list[dict]:
    """FIFO pair entry+exit fills into round-trips."""
    orders.sort(key=lambda o: o['creationTimestamp'])
    fills = [o for o in orders if o.get('status')==2 and o.get('filledPrice') is not None]
    positions: dict[str, list] = defaultdict(list)
    trades = []
    for o in fills:
        cid = o.get('contractId','')
        sym = cid.split('.')[-2] if '.' in cid else cid
        ts = o['creationTimestamp']
        side = 'BUY' if o.get('side')==0 else 'SELL'
        price = float(o['filledPrice'])
        queue = positions[sym]
        if queue and queue[0][0] != side:
            entry_side, entry_px, entry_ts = queue.pop(0)
            tick_size, tick_value = TICK.get(sym, (0.0, 0.0))
            if tick_size > 0:
                trade_side = "long" if entry_side == "BUY" else "short"
                pnl = unrealized_usd(trade_side, entry_px, price, tick_size, tick_value)
            else:
                pnl = None
            trades.append({
                'sym': sym, 'cid': cid,
                'side': "long" if entry_side == "BUY" else "short",
                'entry_ts': entry_ts, 'entry_px': entry_px,
                'exit_ts': ts, 'exit_px': price,
                'actual_pnl': pnl,
                'tick_size': tick_size, 'tick_value': tick_value,
            })
        else:
            queue.append((side, price, ts))
    return trades


def load_bars_for_trade(symbol: str, start_iso: str, end_iso: str) -> pd.DataFrame | None:
    """Load 1-min bars in [start, end+buffer] from the cached parquet."""
    pattern = str(PROJECT_ROOT / "state" / "bars" / f"{symbol}_1m_*.parquet")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        return None
    df = pd.read_parquet(files[0])
    df['ts'] = pd.to_datetime(df['ts'], utc=True)
    start = pd.to_datetime(start_iso, utc=True)
    end = pd.to_datetime(end_iso, utc=True)
    # Pad end by 90 min to allow exit-after-actual scenarios
    end_padded = end + pd.Timedelta(minutes=90)
    window = df[(df['ts'] >= start) & (df['ts'] <= end_padded)].copy()
    if len(window) == 0:
        return None
    return window.sort_values('ts').reset_index(drop=True)


def replay_trade(trade: dict) -> dict:
    """Simulate the new exit rules against historical bars. Returns
    counterfactual P&L + which rule fired."""
    sym = trade['sym']
    side = trade['side']
    entry_px = trade['entry_px']
    entry_ts = pd.to_datetime(trade['entry_ts'], utc=True)
    actual_exit_ts = pd.to_datetime(trade['exit_ts'], utc=True)
    tick_size = trade['tick_size']
    tick_value = trade['tick_value']
    if tick_size == 0:
        return {**trade, 'cf_pnl': None, 'cf_rule': 'no_tick_economics',
                'mfe': None, 'mae': None}

    bars = load_bars_for_trade(sym, trade['entry_ts'], trade['exit_ts'])
    if bars is None or len(bars) == 0:
        return {**trade, 'cf_pnl': None, 'cf_rule': 'no_bars',
                'mfe': None, 'mae': None}

    # Walk bars after entry, compute unrealized each bar, apply exit rules
    bars_after = bars[bars['ts'] >= entry_ts].reset_index(drop=True)
    if len(bars_after) == 0:
        return {**trade, 'cf_pnl': None, 'cf_rule': 'no_bars_after_entry',
                'mfe': None, 'mae': None}

    peak = 0.0
    peak_ts = entry_ts
    trough = 0.0
    closes_seen: list[float] = []
    cf_exit_idx = None
    cf_exit_rule = "actual_holdback"

    for i, row in bars_after.iterrows():
        bar_ts = row['ts']
        bar_close = row['close']
        bar_high = row['high']
        bar_low = row['low']

        # Intrabar peak/trough check using high/low for unrealized boundary
        if side == "long":
            bar_peak_unr = unrealized_usd("long", entry_px, bar_high, tick_size, tick_value)
            bar_trough_unr = unrealized_usd("long", entry_px, bar_low, tick_size, tick_value)
        else:
            bar_peak_unr = unrealized_usd("short", entry_px, bar_low, tick_size, tick_value)
            bar_trough_unr = unrealized_usd("short", entry_px, bar_high, tick_size, tick_value)

        # Track MFE / MAE
        if bar_peak_unr > peak:
            peak = bar_peak_unr
            peak_ts = bar_ts
        if bar_trough_unr < trough:
            trough = bar_trough_unr

        # Close-based unrealized for exit rule checks
        unr = unrealized_usd(side, entry_px, bar_close, tick_size, tick_value)
        closes_seen.append(bar_close)

        # Apply exit rules in priority order (matches profit_protect)
        # 1. Time-decay exit (peak stale + retraced)
        if is_profit_stale(peak, peak_ts, unr, bar_ts):
            cf_exit_idx = i
            cf_exit_rule = "time_decay_exit"
            break

        # 2. Reversal exit (3 consecutive bars against + peak >= $15)
        if peak >= REVERSAL_MIN_PEAK_USD and detect_reversal(side, closes_seen):
            cf_exit_idx = i
            cf_exit_rule = "reversal_exit"
            break

        # 3. Percent-of-peak floor breach
        floor = compute_active_floor(peak)
        if floor is not None and unr < floor:
            cf_exit_idx = i
            cf_exit_rule = "percent_of_peak"
            break

        # 4. Stop the replay at the actual exit time as backstop
        if bar_ts >= actual_exit_ts:
            cf_exit_idx = i
            cf_exit_rule = "actual_exit_reached"
            break

    if cf_exit_idx is None:
        # Replay ran off the bar series — use last bar
        cf_exit_idx = len(bars_after) - 1
        cf_exit_rule = "end_of_bars"

    exit_bar = bars_after.iloc[cf_exit_idx]
    cf_exit_price = float(exit_bar['close'])
    cf_pnl = unrealized_usd(side, entry_px, cf_exit_price, tick_size, tick_value)

    return {
        **trade,
        'mfe': peak,
        'mae': trough,
        'cf_pnl': cf_pnl,
        'cf_exit_ts': exit_bar['ts'].isoformat(),
        'cf_exit_price': cf_exit_price,
        'cf_rule': cf_exit_rule,
    }


def main() -> int:
    orders_path = PROJECT_ROOT / "logs" / "topstep_orders_week.json"
    if not orders_path.exists():
        print(f"ERROR: {orders_path} not found. Pull orders first.")
        return 1
    with open(orders_path) as f:
        orders = json.load(f)
    trades = pair_trades(orders)
    print(f"Trades paired: {len(trades)}")

    results = []
    for t in trades:
        r = replay_trade(t)
        results.append(r)

    # Filter to ones we could replay (had bars + tick economics)
    replayed = [r for r in results if r.get('cf_pnl') is not None]
    print(f"Successfully replayed: {len(replayed)} of {len(results)}")
    print()

    # Output per-trade comparison
    ET = timezone(timedelta(hours=-4))
    print(f"{'entry_ET':<18}{'sym':5}{'side':6}{'actual':>8}{'cf':>8}{'mfe':>8}{'rule':>20}")
    actual_total = 0.0
    cf_total = 0.0
    mfe_total = 0.0
    for r in replayed:
        et = pd.to_datetime(r['entry_ts'], utc=True).astimezone(ET).strftime('%m-%d %H:%M:%S')
        actual = r.get('actual_pnl', 0) or 0
        cf = r['cf_pnl'] or 0
        mfe = r.get('mfe', 0) or 0
        actual_total += actual
        cf_total += cf
        mfe_total += mfe
        print(f"  {et:<18}{r['sym']:5}{r['side']:6}{actual:+7.2f} {cf:+7.2f} {mfe:+7.2f}  {r['cf_rule']:>20}")

    print()
    print(f"=== TOTALS ===")
    print(f"  Actual realized:       ${actual_total:+.2f}")
    print(f"  Counterfactual (new):  ${cf_total:+.2f}")
    print(f"  Peak MFE (theoretical): ${mfe_total:+.2f}")
    delta = cf_total - actual_total
    capture_pct = (cf_total / mfe_total * 100) if mfe_total > 0 else 0
    actual_capture_pct = (actual_total / mfe_total * 100) if mfe_total > 0 else 0
    print(f"  Delta (improvement):   ${delta:+.2f}")
    print(f"  Actual capture vs MFE:    {actual_capture_pct:.0f}%")
    print(f"  Counterfactual vs MFE:    {capture_pct:.0f}%")
    print()
    # Acceptance: counterfactual >= +$300 = rebuild worked
    if cf_total >= 300:
        print(f"OK ACCEPTANCE PASSED: counterfactual ≥ +$300 (got +${cf_total:.0f})")
    elif cf_total >= 150:
        print(f"~ ACCEPTANCE PARTIAL: counterfactual ≥ +$150 (got +${cf_total:.0f}) — calibration helps but not full capture")
    else:
        print(f"XX ACCEPTANCE FAILED: counterfactual < +$150 (got +${cf_total:.0f}) — exit rules not delivering as expected")

    # Save JSON for downstream phases
    out_path = PROJECT_ROOT / "vault" / "research" / "analysis" / "2026-05-15_exit_replay.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        # Convert pd.Timestamp to ISO
        for r in replayed:
            for k in ('mfe_ts','cf_exit_ts'):
                if k in r and not isinstance(r.get(k), str):
                    r[k] = str(r.get(k))
        json.dump({
            'actual_total': actual_total,
            'counterfactual_total': cf_total,
            'mfe_total': mfe_total,
            'delta': delta,
            'capture_pct_actual': actual_capture_pct,
            'capture_pct_counterfactual': capture_pct,
            'n_trades': len(replayed),
            'trades': replayed,
        }, f, indent=2, default=str)
    print(f"\nJSON: {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
