"""passive_entry_shadow — A/B simulator: post-only limit entries vs the
current marketable-limit entries.

User direction 2026-05-17: build the change in a simulated environment
first; compare to live.

The current trader (tools.bracket_placement.place_bracket) places entry
as a marketable LIMIT at signal_price +/- 5 ticks (the slippage buffer).
This basically always fills but PAYS the spread + buffer (~1-5 ticks).

The proposed change: place entry as a POST-ONLY LIMIT at signal_price
exactly (or signal_price -/+ 1 tick favorable). Two outcomes:
  1. Market crosses to us within FILL_TIMEOUT_MIN → filled at our price
     (saves the buffer cost)
  2. Market doesn't cross → we cancel and the signal is missed (a cost
     in opportunity, but no slippage)

Hypothesis: net P&L improves because the slippage saved on filled trades
exceeds the missed-trade opportunity cost.

This module provides a PURE simulator:
  simulate_passive_entry(signal, bars_after_signal) -> dict
    returns {
      "live_fill_price": float | None,
      "live_slippage_ticks": float,
      "passive_fill_price": float | None,
      "passive_filled": bool,
      "delta_ticks": float,   # negative = passive cheaper
      "fill_within_min": int | None,
    }

Called from live_trader when a signal fires: in addition to the live
bracket placement, log the simulated passive outcome to
vault/research/passive_entry_shadow.jsonl for later analysis.
"""
from __future__ import annotations

import pandas as pd


FILL_TIMEOUT_MIN = 5  # cancel passive limit after this many minutes
ASSUMED_LIVE_BUFFER_TICKS = 5  # what place_bracket adds


def simulate_passive_entry(signal: dict, bars_after: pd.DataFrame,
                            tick_size: float) -> dict:
    """Simulate a post-only limit entry at signal_price, walking through
    `bars_after` (the 1-min bars after signal fires).

    A buy passive limit at $P fills when bars_after.Low crosses <= $P.
    A sell passive limit at $P fills when bars_after.High crosses >= $P.

    Returns a comparison dict (see module docstring).
    """
    sig_price = float(signal.get("price") or 0)
    side = str(signal.get("side") or "").lower()
    if sig_price <= 0 or side not in ("long", "short", "buy", "sell"):
        return {"error": "invalid_signal"}
    is_long = side in ("long", "buy")

    # Live (current) outcome: marketable limit fills at signal +/- 5 ticks
    live_fill = (sig_price + ASSUMED_LIVE_BUFFER_TICKS * tick_size
                 if is_long else
                 sig_price - ASSUMED_LIVE_BUFFER_TICKS * tick_size)
    live_slippage_ticks = ASSUMED_LIVE_BUFFER_TICKS

    # Passive outcome: post-only limit at signal_price exactly
    passive_filled = False
    passive_fill_price = None
    fill_within_min = None

    if bars_after is not None and len(bars_after) > 0:
        cap = min(len(bars_after), FILL_TIMEOUT_MIN)
        for i in range(cap):
            bar = bars_after.iloc[i]
            low = float(bar.get("Low") or bar.get("low") or 0)
            high = float(bar.get("High") or bar.get("high") or 0)
            if low <= 0 or high <= 0:
                continue
            if is_long and low <= sig_price:
                passive_filled = True
                passive_fill_price = sig_price
                fill_within_min = i + 1
                break
            if not is_long and high >= sig_price:
                passive_filled = True
                passive_fill_price = sig_price
                fill_within_min = i + 1
                break

    delta_ticks = 0.0
    if passive_filled and passive_fill_price is not None:
        # Negative delta = passive was cheaper for us
        if is_long:
            delta_ticks = (passive_fill_price - live_fill) / tick_size
        else:
            delta_ticks = (live_fill - passive_fill_price) / tick_size

    return {
        "live_fill_price": live_fill,
        "live_slippage_ticks": live_slippage_ticks,
        "passive_fill_price": passive_fill_price,
        "passive_filled": passive_filled,
        "delta_ticks": round(delta_ticks, 2),
        "fill_within_min": fill_within_min,
    }


def aggregate_shadow_log(log_path: str = "vault/research/passive_entry_shadow.jsonl") -> dict:
    """Read the shadow log and return summary stats: fill rate, mean
    delta ticks, projected net effect."""
    import json
    from pathlib import Path
    p = Path(log_path)
    if not p.exists():
        return {"n": 0}
    entries = []
    with p.open(encoding="utf-8") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                continue
    if not entries:
        return {"n": 0}
    n = len(entries)
    filled = [e for e in entries if e.get("passive_filled")]
    fill_rate = len(filled) / n
    deltas = [e["delta_ticks"] for e in filled if "delta_ticks" in e]
    avg_delta = sum(deltas) / len(deltas) if deltas else 0
    return {
        "n": n,
        "fill_rate": round(fill_rate, 3),
        "avg_delta_ticks_when_filled": round(avg_delta, 2),
        "missed_rate": round(1 - fill_rate, 3),
        # Net effect = (fill_rate * delta_saved) - missed_opportunity
        # missed_opportunity assumed = 0 R-multiple (signal didn't fire)
        # which is conservative
        "estimated_savings_per_trade_ticks": round(fill_rate * avg_delta, 2),
    }
