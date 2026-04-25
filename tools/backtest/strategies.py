"""Seed strategies that the backtest engine can run.

These are pure-price strategies (no fundamental data required) — proof that
the harness works end-to-end. Fundamental-data-driven strategies (EIA
surprise, WASDE, etc.) will be added as we wire fundamental-data loaders.

Strategy protocol:

    def strategy(bars: pd.DataFrame, **params) -> Iterator[Signal]:
        for i in range(len(bars)):
            # use bars.iloc[:i+1] ONLY — no lookahead
            ...
            yield Signal.entry(...)

Conventions:
- Entries at the current bar's Close (this is idealized; real fills are worse)
- Stops and targets as price levels; engine honors them intrabar on High/Low
- One open position at a time (serial)
"""

from __future__ import annotations

from typing import Iterator

import numpy as np
import pandas as pd

from .engine import Signal


def donchian_breakout(
    bars: pd.DataFrame,
    lookback: int = 20,
    atr_period: int = 20,
    stop_atr_mult: float = 2.0,
    trail_lookback: int = 10,
) -> Iterator[Signal]:
    """Classic turtle-style Donchian breakout.

    Long entry: close breaks above the prior `lookback`-bar high.
    Stop: entry − stop_atr_mult × ATR(atr_period) at entry.
    Trail: raises stop to the `trail_lookback`-bar low once in profit.
    No explicit target; ride until stop hits.
    """
    atr = _atr(bars, atr_period)
    prior_high = bars["High"].rolling(lookback).max().shift(1)

    in_trade = False
    current_stop = 0.0
    trail = 0.0

    for i in range(len(bars)):
        date = bars.index[i]
        close = float(bars["Close"].iloc[i])

        if not in_trade:
            if i < max(lookback, atr_period):
                continue
            ph = prior_high.iloc[i]
            a = atr.iloc[i]
            if pd.isna(ph) or pd.isna(a):
                continue
            if close > ph:
                entry = close
                stop = entry - stop_atr_mult * a
                current_stop = stop
                trail = stop
                in_trade = True
                yield Signal.entry(
                    date=date, side="long", price=entry,
                    stop=stop, target=None,
                    reason=f"close {close:.2f} > {lookback}-high {ph:.2f}",
                )
        else:
            # Update trailing stop on a new `trail_lookback`-low
            if i >= trail_lookback:
                new_trail = float(bars["Low"].iloc[i - trail_lookback:i].min())
                if new_trail > trail:
                    trail = new_trail
                    # Note: engine honors the ORIGINAL stop. For a trailing
                    # implementation, we'd need to emit stop-update signals.
                    # Simple version: emit an explicit exit when close breaks
                    # the trail.
            if close < trail:
                in_trade = False
                yield Signal.exit(date=date, price=close, reason="trail_break")


def bollinger_mean_reversion(
    bars: pd.DataFrame,
    sma_period: int = 20,
    bb_std: float = 2.0,
    atr_period: int = 20,
    stop_atr_mult: float = 1.5,
) -> Iterator[Signal]:
    """Long pullback in uptrend: price below lower Bollinger band while 50-EMA rising.

    Entry: Close < SMA(sma_period) − bb_std × std, AND EMA(50) rising.
    Target: return to SMA(sma_period) (mid band).
    Stop: entry − stop_atr_mult × ATR(atr_period).
    """
    sma = bars["Close"].rolling(sma_period).mean()
    std = bars["Close"].rolling(sma_period).std()
    lower_band = sma - bb_std * std
    ema50 = bars["Close"].ewm(span=50, adjust=False).mean()
    atr = _atr(bars, atr_period)

    in_trade = False

    for i in range(len(bars)):
        date = bars.index[i]
        close = float(bars["Close"].iloc[i])

        if i < max(sma_period, 50, atr_period):
            continue

        lb = lower_band.iloc[i]
        mid = sma.iloc[i]
        a = atr.iloc[i]
        ema_rising = ema50.iloc[i] > ema50.iloc[i - 5]   # 5-bar slope up

        if pd.isna(lb) or pd.isna(mid) or pd.isna(a):
            continue

        if not in_trade and close < lb and ema_rising:
            stop = close - stop_atr_mult * a
            target = mid
            in_trade = True
            yield Signal.entry(
                date=date, side="long", price=close,
                stop=stop, target=target,
                reason=f"close {close:.2f} < lower_bb {lb:.2f}, EMA50 rising",
            )
        elif in_trade and close >= mid:
            # Target-hit fallback if engine didn't catch it intrabar
            in_trade = False
            yield Signal.exit(date=date, price=close, reason="midband_reached")


def _atr(bars: pd.DataFrame, period: int) -> pd.Series:
    """Classic ATR: mean of true range over period."""
    h, l, c = bars["High"], bars["Low"], bars["Close"]
    prev_c = c.shift(1)
    tr = pd.concat([
        (h - l),
        (h - prev_c).abs(),
        (l - prev_c).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(period).mean()


STRATEGY_REGISTRY = {
    "donchian_breakout": donchian_breakout,
    "bollinger_mean_reversion": bollinger_mean_reversion,
}


def get_strategy(name: str):
    if name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy {name!r}. Available: {list(STRATEGY_REGISTRY)}"
        )
    return STRATEGY_REGISTRY[name]
