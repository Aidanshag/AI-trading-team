"""End-to-end backtest of the simplified live_trader system.

Replays the live_trader's actual decision flow against historical data:
- Reads live_allowlist (the same cells the live trader will trade)
- For each cell, generates gap_fill signals on 5m bars
- Applies the live_trader's gates IN ORDER:
    1. DLL halt ($1,000 daily loss → no more trades that day)
    2. Max trades/day cap (8)
    3. Per-symbol cooldown (45 min)
    4. Per-trade loss cap ($150 → contracts = floor(150 / stop_dollars))
    5. Bracket OCO simulation (entry → first hit of stop or target)
- Tracks day-by-day P&L, drawdown, hit rate, contract sizing

Output: a probability-of-profitable + Combine-pass estimate based on this 60d sim.
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from statistics import mean, median, stdev

import pandas as pd
import yfinance as yf

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.backtest import strategies as strats  # noqa: E402

# Symbol economics (mirrored from config/symbols.yaml)
SYMBOL_SPECS = {
    "ZN": {"tick_size": 0.015625, "tick_value": 15.625, "yf": "ZN=F"},
    "ZB": {"tick_size": 0.03125,  "tick_value": 31.25,  "yf": "ZB=F"},
    "ZT": {"tick_size": 0.0078125, "tick_value": 15.625, "yf": "ZT=F"},
    "ZF": {"tick_size": 0.0078125, "tick_value": 7.8125, "yf": "ZF=F"},
}

# live_trader.py constants (mirrored)
PER_TRADE_LOSS_CAP_USD = 150.0
DLL_USD = 1000.0
MAX_TRADES_PER_DAY = 8
COOLDOWN_MIN = 45
COMBINE_TARGET_USD = 3000.0


def session_for(ts_et) -> str:
    """ET-local hour → session bucket (mirrors live_trader.session_now_utc)."""
    h = ts_et.hour
    if 18 <= h or h < 4:
        return "Asian"
    if 4 <= h < 8:
        return "London"
    if 9 <= h < 16:
        return "RTH"
    return "PostClose"


def load_allowlist() -> list[dict]:
    p = PROJECT_ROOT / "state" / "strategy_validation.json"
    with open(p) as f:
        return json.load(f).get("live_allowlist", [])


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


def generate_signals_for_cell(cell: dict, bars: pd.DataFrame) -> list[dict]:
    """Run gap_fill on the bars; emit one trade-event dict per signal that matches the cell."""
    sym = cell["symbol"]
    side_filter = cell["side"]
    sess_filter = cell["session"]
    spec = SYMBOL_SPECS[sym]

    sigs = list(strats.gap_fill(bars))
    events = []
    for sig in sigs:
        if sig.kind != "entry":
            continue
        entry_ts = sig.date
        if entry_ts.tzinfo is None:
            entry_ts = entry_ts.tz_localize("UTC")
        entry_et = entry_ts.tz_convert("America/New_York")
        if session_for(entry_et) != sess_filter:
            continue
        if sig.side != side_filter:
            continue
        events.append({
            "ts": entry_et,
            "symbol": sym,
            "session": sess_filter,
            "side": sig.side,
            "entry": sig.price,
            "stop": sig.stop,
            "target": sig.target,
        })
    return events


def simulate_bracket_outcome(event: dict, bars: pd.DataFrame) -> tuple[float, str, pd.Timestamp]:
    """Walk forward from entry bar; return (exit_price, exit_reason, exit_ts)."""
    sym = event["symbol"]
    spec = SYMBOL_SPECS[sym]
    entry = event["entry"]
    stop = event["stop"]
    target = event["target"]
    side = event["side"]
    entry_ts = event["ts"]

    # Find bars after entry
    forward = bars[bars.index > entry_ts]
    if len(forward) == 0:
        return entry, "no_data", entry_ts

    # Walk bars; conservative — assume stop hits first if same bar straddles both
    for ts, row in forward.iterrows():
        hi, lo = float(row["High"]), float(row["Low"])
        if side == "long":
            if lo <= stop:
                return stop, "stop_hit", ts
            if hi >= target:
                return target, "target_hit", ts
        else:  # short
            if hi >= stop:
                return stop, "stop_hit", ts
            if lo <= target:
                return target, "target_hit", ts
        # Cap holding time at 8h (96 bars on 5m)
        if (ts - entry_ts) > timedelta(hours=8):
            close = float(row["Close"])
            return close, "timeout", ts

    # End of data — close at last bar
    last = forward.iloc[-1]
    return float(last["Close"]), "end_of_data", forward.index[-1]


def size_position(stop_dollars_per_contract: float) -> int:
    """Mirror live_trader sizing: contracts = floor(loss_cap / stop_dollars)."""
    if stop_dollars_per_contract <= 0:
        return 0
    n = math.floor(PER_TRADE_LOSS_CAP_USD / stop_dollars_per_contract)
    return max(0, min(n, 5))  # hard cap of 5 contracts (Topstep $50K limit)


def main():
    print("=" * 78)
    print("END-TO-END BACKTEST: simplified live_trader system")
    print("=" * 78)

    allowlist = load_allowlist()
    print(f"\nlive_allowlist: {len(allowlist)} cells")
    symbols = sorted({c["symbol"] for c in allowlist})
    print(f"Symbols: {symbols}")

    # Fetch bars per symbol once
    bars_by_sym = {}
    for sym in symbols:
        spec = SYMBOL_SPECS[sym]
        print(f"  Fetching {sym} ({spec['yf']})... ", end="", flush=True)
        bars_by_sym[sym] = fetch_bars(spec["yf"])
        print(f"{len(bars_by_sym[sym])} bars")

    # Generate all events across cells, sort by timestamp
    all_events = []
    for cell in allowlist:
        sym = cell["symbol"]
        bars = bars_by_sym[sym]
        evs = generate_signals_for_cell(cell, bars)
        all_events.extend(evs)
    all_events.sort(key=lambda e: e["ts"])
    print(f"\nTotal signals from allowlist: {len(all_events)}")

    # Walk events chronologically with live_trader gating
    daily_pnl = defaultdict(float)
    daily_trade_count = defaultdict(int)
    last_trade_per_sym = {}
    halted_days = set()

    trades = []  # logged outcomes
    for ev in all_events:
        day_key = ev["ts"].date()

        # Gate 1: DLL halted for the day
        if day_key in halted_days:
            continue

        # Gate 2: max trades/day
        if daily_trade_count[day_key] >= MAX_TRADES_PER_DAY:
            continue

        # Gate 3: per-symbol cooldown
        last_t = last_trade_per_sym.get(ev["symbol"])
        if last_t and (ev["ts"] - last_t) < timedelta(minutes=COOLDOWN_MIN):
            continue

        # Gate 4: position sizing via per-trade $ loss cap
        spec = SYMBOL_SPECS[ev["symbol"]]
        stop_dist_price = abs(ev["entry"] - ev["stop"])
        stop_dollars = (stop_dist_price / spec["tick_size"]) * spec["tick_value"]
        n_contracts = size_position(stop_dollars)
        if n_contracts == 0:
            continue

        # Simulate bracket outcome
        exit_price, exit_reason, exit_ts = simulate_bracket_outcome(
            ev, bars_by_sym[ev["symbol"]]
        )
        if ev["side"] == "long":
            pnl_per_contract_price = exit_price - ev["entry"]
        else:
            pnl_per_contract_price = ev["entry"] - exit_price
        pnl_per_contract_dollars = (pnl_per_contract_price / spec["tick_size"]) * spec["tick_value"]
        # Topstep round-turn fee: ~$2.40 per contract per side ≈ $4.80 r/t
        fees = 4.80 * n_contracts
        pnl_total = pnl_per_contract_dollars * n_contracts - fees

        daily_pnl[day_key] += pnl_total
        daily_trade_count[day_key] += 1
        last_trade_per_sym[ev["symbol"]] = ev["ts"]

        # Gate 5: DLL kill check (after this trade)
        if daily_pnl[day_key] <= -DLL_USD:
            halted_days.add(day_key)

        trades.append({
            **ev,
            "exit_price": exit_price,
            "exit_reason": exit_reason,
            "exit_ts": exit_ts,
            "n_contracts": n_contracts,
            "pnl_total": pnl_total,
            "daily_pnl_after": daily_pnl[day_key],
        })

    # Stats
    print("\n" + "=" * 78)
    print("RESULTS")
    print("=" * 78)
    print(f"Total trades simulated: {len(trades)}")
    if not trades:
        print("No trades — nothing to evaluate.")
        return

    wins = [t for t in trades if t["pnl_total"] > 0]
    losses = [t for t in trades if t["pnl_total"] < 0]
    flats = [t for t in trades if t["pnl_total"] == 0]
    hit_rate = len(wins) / len(trades)

    avg_win = mean(t["pnl_total"] for t in wins) if wins else 0
    avg_loss = mean(t["pnl_total"] for t in losses) if losses else 0
    expectancy_per_trade = mean(t["pnl_total"] for t in trades)

    total_pnl = sum(t["pnl_total"] for t in trades)
    days_traded = len(daily_pnl)
    daily_pnls = sorted(daily_pnl.values())
    profitable_days = sum(1 for v in daily_pnls if v > 0)
    losing_days = sum(1 for v in daily_pnls if v < 0)
    breakeven_days = sum(1 for v in daily_pnls if v == 0)

    # Equity curve + drawdown
    equity = []
    cum = 0
    for d in sorted(daily_pnl):
        cum += daily_pnl[d]
        equity.append((d, cum))
    peak = 0
    max_dd = 0
    for _, v in equity:
        if v > peak:
            peak = v
        dd = peak - v
        if dd > max_dd:
            max_dd = dd

    print(f"\n— Per-trade —")
    print(f"  Hit rate:           {hit_rate*100:.1f}% ({len(wins)}W / {len(losses)}L / {len(flats)}flat)")
    print(f"  Avg win:           ${avg_win:+.2f}")
    print(f"  Avg loss:          ${avg_loss:+.2f}")
    print(f"  Expectancy/trade:  ${expectancy_per_trade:+.2f}")
    print(f"  Median trade:      ${median(t['pnl_total'] for t in trades):+.2f}")

    print(f"\n— Daily —")
    print(f"  Days traded:        {days_traded}")
    print(f"  Profitable days:    {profitable_days} ({profitable_days/days_traded*100:.0f}%)")
    print(f"  Losing days:        {losing_days}")
    print(f"  Breakeven days:     {breakeven_days}")
    print(f"  Best day:          ${max(daily_pnls):+.2f}")
    print(f"  Worst day:         ${min(daily_pnls):+.2f}")
    print(f"  Median daily P&L:  ${median(daily_pnls):+.2f}")
    print(f"  Mean daily P&L:    ${mean(daily_pnls):+.2f}")
    print(f"  DLL halts:          {len(halted_days)}")

    print(f"\n— Aggregate —")
    print(f"  Total P&L (60d):   ${total_pnl:+.2f}")
    print(f"  Max drawdown:      ${max_dd:.2f}")
    print(f"  Cost-discipline check: ~$26/day × {days_traded} = ${26*days_traded} fixed; net = ${total_pnl - 26*days_traded:+.2f}")

    # Combine math: $3,000 cumulative profit with no day > 50% of total
    print(f"\n— Combine (Topstep $50K) —")
    print(f"  Target: +${COMBINE_TARGET_USD} cumulative, ≥5 days, no day > 50%")
    days_to_target = None
    cum = 0
    for d, val in equity:
        cum_check = val
        if cum_check >= COMBINE_TARGET_USD and days_to_target is None:
            days_to_target = sum(1 for x in equity if x[0] <= d)
    if days_to_target:
        print(f"  Hit +${COMBINE_TARGET_USD} in this 60d window: YES (day {days_to_target})")
    else:
        print(f"  Hit +${COMBINE_TARGET_USD} in this 60d window: NO  (peaked at ${peak:+.2f})")

    # Concentration check
    if total_pnl > 0:
        top_day = max(daily_pnls)
        concentration = top_day / total_pnl * 100
        print(f"  Top-day concentration: {concentration:.0f}% of total P&L (must be < 50% for Combine)")

    # Bootstrap: probability of profitable next 30d
    import random
    random.seed(42)
    n_iter = 5000
    sample_n = 30
    profitable_sims = 0
    target_sims = 0
    dll_breach_sims = 0
    sims = []
    daily_list = list(daily_pnl.values())
    for _ in range(n_iter):
        sample = [random.choice(daily_list) for _ in range(sample_n)]
        s = sum(sample)
        sims.append(s)
        if s > 0:
            profitable_sims += 1
        if s >= COMBINE_TARGET_USD:
            target_sims += 1
        # Drawdown in sim
        cum = 0; peak = 0; max_dd_sim = 0
        for v in sample:
            cum += v
            if cum > peak: peak = cum
            if peak - cum > max_dd_sim: max_dd_sim = peak - cum
        if max_dd_sim >= 1500:  # TDD-ish
            dll_breach_sims += 1

    sims.sort()
    print(f"\n— Bootstrap (5,000 sims of next 30 trading days) —")
    print(f"  Probability profitable:        {profitable_sims/n_iter*100:.1f}%")
    print(f"  Probability hits +$3,000:      {target_sims/n_iter*100:.1f}%")
    print(f"  Probability of $1,500+ DD:     {dll_breach_sims/n_iter*100:.1f}%")
    print(f"  P&L distribution: 5%=${sims[int(n_iter*0.05)]:+.0f}  25%=${sims[int(n_iter*0.25)]:+.0f}  50%=${sims[int(n_iter*0.5)]:+.0f}  75%=${sims[int(n_iter*0.75)]:+.0f}  95%=${sims[int(n_iter*0.95)]:+.0f}")

    # By cell
    print(f"\n— Per-cell breakdown —")
    by_cell = defaultdict(list)
    for t in trades:
        key = f"{t['symbol']}|{t['session']}|{t['side']}"
        by_cell[key].append(t)
    print(f"  {'cell':<24} {'n':>4} {'hit%':>6} {'avg':>9} {'total':>10}")
    for k in sorted(by_cell):
        cs = by_cell[k]
        h = sum(1 for t in cs if t["pnl_total"] > 0) / len(cs)
        avg = mean(t["pnl_total"] for t in cs)
        tot = sum(t["pnl_total"] for t in cs)
        print(f"  {k:<24} {len(cs):>4} {h*100:>5.0f}% {avg:>+8.2f} {tot:>+10.2f}")


if __name__ == "__main__":
    main()
