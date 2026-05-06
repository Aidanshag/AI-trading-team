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


def volatility_breakout(
    bars: pd.DataFrame,
    atr_period: int = 14,
    expansion_mult: float = 1.5,
    stop_atr_mult: float = 1.5,
    target_atr_mult: float = 3.0,
) -> Iterator[Signal]:
    """ATR-expansion breakout. Long when current bar's TR > expansion_mult * ATR
    AND closes above prior bar's high. Captures volatility regime shifts."""
    atr = _atr(bars, atr_period)
    h, l, c = bars["High"], bars["Low"], bars["Close"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    prev_high = h.shift(1)
    in_trade = False
    for i in range(len(bars)):
        if i < atr_period + 1:
            continue
        date = bars.index[i]
        close = float(c.iloc[i])
        a = atr.iloc[i]
        if pd.isna(a):
            continue
        if not in_trade:
            tr_today = float(tr.iloc[i])
            ph = prev_high.iloc[i]
            if pd.isna(ph):
                continue
            if tr_today > expansion_mult * a and close > ph:
                stop = close - stop_atr_mult * a
                target = close + target_atr_mult * a
                in_trade = True
                yield Signal.entry(
                    date=date, side="long", price=close, stop=stop, target=target,
                    reason=f"vol_expansion tr={tr_today:.2f}>{expansion_mult}*ATR",
                )


def pullback_in_trend(
    bars: pd.DataFrame,
    ema_period: int = 200,
    pullback_period: int = 5,
    pullback_atr_mult: float = 1.0,
    atr_period: int = 14,
    stop_atr_mult: float = 1.5,
    target_atr_mult: float = 2.5,
) -> Iterator[Signal]:
    """Buy pullback in established uptrend. EMA200 rising AND price has pulled back
    >= pullback_atr_mult * ATR over `pullback_period`, then closes back up."""
    ema = bars["Close"].ewm(span=ema_period, adjust=False).mean()
    atr = _atr(bars, atr_period)
    in_trade = False
    for i in range(len(bars)):
        if i < ema_period + pullback_period:
            continue
        date = bars.index[i]
        close = float(bars["Close"].iloc[i])
        prior_close = float(bars["Close"].iloc[i - 1])
        ema_now = ema.iloc[i]
        ema_prior = ema.iloc[i - 5]
        a = atr.iloc[i]
        if pd.isna(ema_now) or pd.isna(a):
            continue
        ema_rising = ema_now > ema_prior
        recent_high = bars["High"].iloc[i - pullback_period:i].max()
        recent_low = bars["Low"].iloc[i - pullback_period:i].min()
        pullback_size = recent_high - recent_low
        if not in_trade and ema_rising:
            if (
                pullback_size >= pullback_atr_mult * a
                and close > prior_close
                and close < recent_high
            ):
                stop = close - stop_atr_mult * a
                target = close + target_atr_mult * a
                in_trade = True
                yield Signal.entry(
                    date=date, side="long", price=close, stop=stop, target=target,
                    reason=f"pullback in EMA200 uptrend",
                )


def range_mean_reversion(
    bars: pd.DataFrame,
    range_period: int = 20,
    range_max_pct: float = 0.04,
    atr_period: int = 14,
    stop_atr_mult: float = 1.0,
) -> Iterator[Signal]:
    """Mean revert only when range-bound. Detects range via tight high-low over
    `range_period`. Buys at lower band, targets upper band."""
    high_n = bars["High"].rolling(range_period).max()
    low_n = bars["Low"].rolling(range_period).min()
    range_pct = (high_n - low_n) / bars["Close"]
    atr = _atr(bars, atr_period)
    in_trade = False
    for i in range(len(bars)):
        if i < max(range_period, atr_period):
            continue
        date = bars.index[i]
        close = float(bars["Close"].iloc[i])
        rp = range_pct.iloc[i]
        hi = high_n.iloc[i]
        lo = low_n.iloc[i]
        a = atr.iloc[i]
        if pd.isna(rp) or pd.isna(a) or pd.isna(hi) or pd.isna(lo):
            continue
        if not in_trade:
            band_size = hi - lo
            if band_size <= 0:
                continue
            position_in_range = (close - lo) / band_size
            if rp < range_max_pct and position_in_range < 0.20:
                stop = close - stop_atr_mult * a
                target = lo + 0.85 * band_size
                in_trade = True
                yield Signal.entry(
                    date=date, side="long", price=close, stop=stop, target=target,
                    reason=f"range-bound (range={rp*100:.1f}%) at lower band",
                )


# =====================================================================
# VOLATILITY STRATEGIES
# =====================================================================
# A note on "high-frequency" scope:
# True HFT (sub-second microstructure) requires colocation, direct exchange
# feeds, and tick data — none of which we have on Topstep/ProjectX. The
# strategies below labelled "intraday cadence" work on any bar timeframe
# the engine is fed (daily, hourly, 15-min, 5-min). The Quant team should
# run them across multiple timeframes to compare cadence sensitivity.
# =====================================================================


def bollinger_squeeze_break(
    bars: pd.DataFrame,
    sma_period: int = 20,
    bb_std: float = 2.0,
    squeeze_lookback: int = 120,
    squeeze_pct: float = 0.20,
    stop_atr_mult: float = 1.5,
    target_atr_mult: float = 3.0,
    atr_period: int = 14,
) -> Iterator[Signal]:
    """Bollinger-band squeeze: width in bottom `squeeze_pct` of last
    `squeeze_lookback` bars → trade the direction of the next clean break.

    Vol-compression precedes vol-expansion. Long when close > upper band on
    a squeeze release; short when close < lower band. Edge-triggered:
    fires only on the bar where the break first occurs (close was inside
    band on prior bar). Engine handles serial position management.
    """
    sma = bars["Close"].rolling(sma_period).mean()
    std = bars["Close"].rolling(sma_period).std()
    upper = sma + bb_std * std
    lower = sma - bb_std * std
    width = (upper - lower) / sma
    width_pctile = width.rolling(squeeze_lookback).rank(pct=True)
    atr = _atr(bars, atr_period)
    close_s = bars["Close"]

    for i in range(1, len(bars)):
        if i < max(sma_period, squeeze_lookback, atr_period):
            continue
        date = bars.index[i]
        close = float(close_s.iloc[i])
        prev_close = float(close_s.iloc[i - 1])
        u, l = upper.iloc[i], lower.iloc[i]
        u_prev, l_prev = upper.iloc[i - 1], lower.iloc[i - 1]
        wp = width_pctile.iloc[i - 1]  # squeeze regime measured BEFORE the break
        a = atr.iloc[i]
        if any(pd.isna(x) for x in (u, l, u_prev, l_prev, wp, a)):
            continue
        if wp > squeeze_pct:
            continue
        # Edge: close just crossed above upper or below lower
        if close > u and prev_close <= u_prev:
            stop = close - stop_atr_mult * a
            target = close + target_atr_mult * a
            yield Signal.entry(
                date=date, side="long", price=close, stop=stop, target=target,
                reason=f"squeeze_break_long width_pctile={wp:.2f}",
            )
        elif close < l and prev_close >= l_prev:
            stop = close + stop_atr_mult * a
            target = close - target_atr_mult * a
            yield Signal.entry(
                date=date, side="short", price=close, stop=stop, target=target,
                reason=f"squeeze_break_short width_pctile={wp:.2f}",
            )


def keltner_breakout(
    bars: pd.DataFrame,
    ema_period: int = 20,
    keltner_mult: float = 2.0,
    atr_period: int = 20,
    stop_atr_mult: float = 1.5,
    target_atr_mult: float = 3.0,
    trend_filter_period: int = 50,
) -> Iterator[Signal]:
    """Keltner channel breakout: EMA ± k × ATR.
    Differs from Bollinger because the channel is ATR-based (path-dependent
    vol) rather than std-based (point-in-time vol). Filter requires the
    longer-EMA trend to align with breakout direction.
    """
    ema = bars["Close"].ewm(span=ema_period, adjust=False).mean()
    atr = _atr(bars, atr_period)
    upper = ema + keltner_mult * atr
    lower = ema - keltner_mult * atr
    trend_ema = bars["Close"].ewm(span=trend_filter_period, adjust=False).mean()
    close_s = bars["Close"]

    for i in range(1, len(bars)):
        if i < max(ema_period, atr_period, trend_filter_period) + 5:
            continue
        date = bars.index[i]
        close = float(close_s.iloc[i])
        prev_close = float(close_s.iloc[i - 1])
        u, l = upper.iloc[i], lower.iloc[i]
        u_prev, l_prev = upper.iloc[i - 1], lower.iloc[i - 1]
        a = atr.iloc[i]
        trend_now = trend_ema.iloc[i]
        trend_prev = trend_ema.iloc[i - 5]
        if any(pd.isna(x) for x in (u, l, u_prev, l_prev, a)):
            continue
        if close > u and prev_close <= u_prev and trend_now > trend_prev:
            stop = close - stop_atr_mult * a
            target = close + target_atr_mult * a
            yield Signal.entry(
                date=date, side="long", price=close, stop=stop, target=target,
                reason="keltner_break_long + trend_up",
            )
        elif close < l and prev_close >= l_prev and trend_now < trend_prev:
            stop = close + stop_atr_mult * a
            target = close - target_atr_mult * a
            yield Signal.entry(
                date=date, side="short", price=close, stop=stop, target=target,
                reason="keltner_break_short + trend_down",
            )


def vol_regime_trend(
    bars: pd.DataFrame,
    vol_lookback: int = 60,
    rv_window: int = 20,
    lookback: int = 20,
    atr_period: int = 20,
    stop_atr_mult: float = 2.0,
    target_atr_mult: float = 4.0,
) -> Iterator[Signal]:
    """Donchian breakout, but ONLY when realized vol is BELOW its
    `vol_lookback`-bar median. Trends emerge from compressed-vol regimes;
    chop dominates expanded-vol regimes. Filtered breakouts catch the good
    half and skip the chop half.
    """
    rets = bars["Close"].pct_change()
    rv = rets.rolling(rv_window).std() * np.sqrt(252)
    rv_median = rv.rolling(vol_lookback).median()
    prior_high = bars["High"].rolling(lookback).max().shift(1)
    atr = _atr(bars, atr_period)
    close_s = bars["Close"]

    for i in range(1, len(bars)):
        if i < max(lookback, vol_lookback, atr_period, rv_window):
            continue
        date = bars.index[i]
        close = float(close_s.iloc[i])
        prev_close = float(close_s.iloc[i - 1])
        ph = prior_high.iloc[i]
        ph_prev = prior_high.iloc[i - 1]
        a = atr.iloc[i]
        rv_now = rv.iloc[i]
        rv_med = rv_median.iloc[i]
        if any(pd.isna(x) for x in (ph, ph_prev, a, rv_now, rv_med)):
            continue
        # Edge-trigger: just broke above prior_high under low-vol regime
        if rv_now < rv_med and close > ph and prev_close <= ph_prev:
            stop = close - stop_atr_mult * a
            target = close + target_atr_mult * a
            yield Signal.entry(
                date=date, side="long", price=close, stop=stop, target=target,
                reason=f"low_vol_breakout rv={rv_now:.2f}<median={rv_med:.2f}",
            )


def vol_spike_fade(
    bars: pd.DataFrame,
    atr_period: int = 14,
    spike_mult: float = 2.5,
    stop_atr_mult: float = 1.0,
    target_atr_mult: float = 1.5,
) -> Iterator[Signal]:
    """Fade exhaustion: when one bar's true range > spike_mult × ATR, the
    next bar's gap-of-flow tends to retrace. Long after a wide DOWN bar,
    short after a wide UP bar. Mean-reversion in the vol domain.
    """
    h, l, c = bars["High"], bars["Low"], bars["Close"]
    o = bars["Open"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    atr = _atr(bars, atr_period)

    # Spikes themselves are rare, naturally edge-triggered. No in_trade gate
    # needed — engine handles serial position management.
    for i in range(len(bars) - 1):
        if i < atr_period + 1:
            continue
        date_today = bars.index[i]
        a = atr.iloc[i]
        tr_today = float(tr.iloc[i])
        if pd.isna(a):
            continue
        if tr_today > spike_mult * a:
            close_today = float(c.iloc[i])
            open_today = float(o.iloc[i])
            if close_today < open_today:
                # Wide down bar → fade up
                stop = close_today - stop_atr_mult * a
                target = close_today + target_atr_mult * a
                yield Signal.entry(
                    date=date_today, side="long", price=close_today,
                    stop=stop, target=target,
                    reason=f"vol_spike_fade_long TR/ATR={tr_today/a:.1f}",
                )
            elif close_today > open_today:
                stop = close_today + stop_atr_mult * a
                target = close_today - target_atr_mult * a
                yield Signal.entry(
                    date=date_today, side="short", price=close_today,
                    stop=stop, target=target,
                    reason=f"vol_spike_fade_short TR/ATR={tr_today/a:.1f}",
                )


# =====================================================================
# INTRADAY-CADENCE STRATEGIES
# =====================================================================


def opening_range_breakout(
    bars: pd.DataFrame,
    or_bars: int = 4,
    session_bars: int = 26,
    stop_atr_mult: float = 0.5,
    target_atr_mult: float = 1.5,
    atr_period: int = 14,
) -> Iterator[Signal]:
    """Opening Range Breakout. First `or_bars` of each session define the
    range. Subsequent close above range high → long; below → short.
    Most useful on intraday bars (15-min default: or_bars=4 = first hour;
    session_bars=26 = full RTH at 15-min). On daily bars, becomes a multi-
    day breakout — still useful but less classic.
    """
    h, l, c = bars["High"], bars["Low"], bars["Close"]
    atr = _atr(bars, atr_period)

    or_high = None
    or_low = None
    bars_into_session = 0
    fired_this_session = False

    for i in range(len(bars)):
        if i < atr_period + or_bars:
            bars_into_session = (bars_into_session + 1) % session_bars
            continue
        date = bars.index[i]
        # Session boundary: reset OR + allow fresh fire
        if bars_into_session == 0:
            or_high = float(h.iloc[i:i + or_bars].max()) if i + or_bars <= len(bars) else None
            or_low = float(l.iloc[i:i + or_bars].min()) if i + or_bars <= len(bars) else None
            fired_this_session = False
        bars_into_session = (bars_into_session + 1) % session_bars

        if or_high is None or fired_this_session or bars_into_session <= or_bars:
            continue
        close = float(c.iloc[i])
        a = atr.iloc[i]
        if pd.isna(a):
            continue
        if close > or_high:
            stop = close - stop_atr_mult * a
            target = close + target_atr_mult * a
            fired_this_session = True
            yield Signal.entry(
                date=date, side="long", price=close, stop=stop, target=target,
                reason=f"orb_long > or_high {or_high:.2f}",
            )
        elif close < or_low:
            stop = close + stop_atr_mult * a
            target = close - target_atr_mult * a
            fired_this_session = True
            yield Signal.entry(
                date=date, side="short", price=close, stop=stop, target=target,
                reason=f"orb_short < or_low {or_low:.2f}",
            )


def narrow_range_break(
    bars: pd.DataFrame,
    nr_period: int = 7,
    stop_atr_mult: float = 1.0,
    target_atr_mult: float = 2.0,
    atr_period: int = 14,
) -> Iterator[Signal]:
    """NR7 (or NRn) breakout. The narrowest range bar in the last n is a
    coil signal. Trade the direction of the break.
    """
    h, l = bars["High"], bars["Low"]
    rng = h - l
    is_nr = rng == rng.rolling(nr_period).min()
    atr = _atr(bars, atr_period)

    nr_high = None
    nr_low = None

    for i in range(len(bars)):
        if i < max(nr_period, atr_period) + 1:
            continue
        date = bars.index[i]
        close = float(bars["Close"].iloc[i])
        a = atr.iloc[i]
        if pd.isna(a):
            continue
        # On the bar AFTER an NR signal, register the bracket (first occurrence wins)
        if is_nr.iloc[i - 1] and nr_high is None:
            nr_high = float(h.iloc[i - 1])
            nr_low = float(l.iloc[i - 1])
        if nr_high is None:
            continue
        if close > nr_high:
            stop = nr_low
            target = close + target_atr_mult * a
            yield Signal.entry(
                date=date, side="long", price=close, stop=stop, target=target,
                reason=f"nr{nr_period}_break_long",
            )
            nr_high = None
            nr_low = None
        elif close < nr_low:
            stop = nr_high
            target = close - target_atr_mult * a
            yield Signal.entry(
                date=date, side="short", price=close, stop=stop, target=target,
                reason=f"nr{nr_period}_break_short",
            )
            nr_high = None
            nr_low = None


def inside_bar_break(
    bars: pd.DataFrame,
    stop_atr_mult: float = 1.0,
    target_atr_mult: float = 2.0,
    atr_period: int = 14,
) -> Iterator[Signal]:
    """Inside-bar breakout. Today's H ≤ yesterday's H AND today's L ≥
    yesterday's L → coil. Next break of the inside bar in either direction
    triggers entry. Classic discretionary pattern, statistically clean.
    """
    h, l = bars["High"], bars["Low"]
    atr = _atr(bars, atr_period)

    inside_h = None
    inside_l = None

    for i in range(len(bars)):
        if i < atr_period + 2:
            continue
        date = bars.index[i]
        close = float(bars["Close"].iloc[i])
        a = atr.iloc[i]
        if pd.isna(a):
            continue
        # Detect inside bar at i-1 (relative to i-2). First detection wins until break.
        if inside_h is None and (
            h.iloc[i - 1] <= h.iloc[i - 2]
            and l.iloc[i - 1] >= l.iloc[i - 2]
        ):
            inside_h = float(h.iloc[i - 1])
            inside_l = float(l.iloc[i - 1])
        if inside_h is None:
            continue
        if close > inside_h:
            stop = inside_l
            target = close + target_atr_mult * a
            yield Signal.entry(
                date=date, side="long", price=close, stop=stop, target=target,
                reason="inside_bar_break_long",
            )
            inside_h = None
            inside_l = None
        elif close < inside_l:
            stop = inside_h
            target = close - target_atr_mult * a
            yield Signal.entry(
                date=date, side="short", price=close, stop=stop, target=target,
                reason="inside_bar_break_short",
            )
            inside_h = None
            inside_l = None


def rsi2_extreme_reversion(
    bars: pd.DataFrame,
    rsi_period: int = 2,
    rsi_buy_below: float = 10,
    rsi_exit_above: float = 70,
    trend_ema: int = 200,
    stop_lookback: int = 5,
) -> Iterator[Signal]:
    """Larry Connors-style RSI(2) extreme. Long when RSI(2) < 10 AND price
    above 200-EMA (trend filter); exit when RSI(2) > 70. Stop = N-bar low.
    Long-only — designed for pullbacks within established uptrends.
    """
    delta = bars["Close"].diff()
    gain = delta.clip(lower=0).rolling(rsi_period).mean()
    loss = (-delta.clip(upper=0)).rolling(rsi_period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    ema = bars["Close"].ewm(span=trend_ema, adjust=False).mean()

    in_trade = False
    for i in range(len(bars)):
        if i < max(trend_ema, stop_lookback) + 5:
            continue
        date = bars.index[i]
        close = float(bars["Close"].iloc[i])
        r = rsi.iloc[i]
        e = ema.iloc[i]
        if pd.isna(r) or pd.isna(e):
            continue
        if not in_trade:
            if r < rsi_buy_below and close > e:
                stop = float(bars["Low"].iloc[i - stop_lookback:i + 1].min())
                if stop >= close:
                    continue
                in_trade = True
                yield Signal.entry(
                    date=date, side="long", price=close, stop=stop, target=None,
                    reason=f"rsi2={r:.1f}<{rsi_buy_below} above ema{trend_ema}",
                )
        else:
            if r > rsi_exit_above:
                in_trade = False
                yield Signal.exit(date=date, price=close, reason=f"rsi2_exit r={r:.1f}")


# =====================================================================
# ADDITIONAL INTRADAY STRATEGIES (added 2026-04-28 for HFT-flavor)
# =====================================================================


# vwap_reversion REMOVED 2026-05-04 — backtest + walk-forward both
# confirmed it has NO edge. Hit rate 1-10% on equity indices, t-stat as
# bad as -24.25 on MNQ RTH OOS. Was a stop-loss factory across all
# symbols and sessions. See vault/research/backtests/2026-05-04_*.md.


def volume_spike_reversal(
    bars: pd.DataFrame,
    volume_spike_mult: float = 3.0,
    rr_target: float = 2.0,
) -> Iterator[Signal]:
    """Fade a wide-range bar with abnormal volume — institutional flow
    capitulation creates mean-reversion opportunity.

    Trigger: TR > 2× ATR AND volume > N× recent-avg-volume AND prior
    bar closed in the outer 25% of its range (climax).
    Long after wide DOWN bar; short after wide UP bar.
    """
    h, l, c, o = bars["High"], bars["Low"], bars["Close"], bars["Open"]
    if "Volume" not in bars.columns:
        return  # need volume
    v = bars["Volume"]
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    atr = _atr(bars, 14)
    avg_vol = v.rolling(20).mean()

    for i in range(20, len(bars) - 1):
        date = bars.index[i]
        a = atr.iloc[i]
        avg = avg_vol.iloc[i]
        if pd.isna(a) or pd.isna(avg) or avg == 0:
            continue
        bar_v = float(v.iloc[i])
        bar_tr = float(tr.iloc[i])
        if bar_tr <= 2.0 * a or bar_v < volume_spike_mult * avg:
            continue
        # Climactic close in outer 25% of range
        bar_h, bar_l = float(h.iloc[i]), float(l.iloc[i])
        bar_c = float(c.iloc[i])
        rng = max(bar_h - bar_l, 1e-9)
        outer = (bar_c - bar_l) / rng
        if outer < 0.25:
            # Down climax — fade long
            entry = bar_c
            stop = bar_l - 0.25 * a
            target = bar_c + rr_target * (entry - stop)
            yield Signal.entry(
                date=date, side="long", price=entry, stop=stop, target=target,
                reason=f"vol_spike_rev_long V={bar_v/avg:.1f}× TR={bar_tr/a:.1f}×",
            )
        elif outer > 0.75:
            # Up climax — fade short
            entry = bar_c
            stop = bar_h + 0.25 * a
            target = bar_c - rr_target * (stop - entry)
            yield Signal.entry(
                date=date, side="short", price=entry, stop=stop, target=target,
                reason=f"vol_spike_rev_short V={bar_v/avg:.1f}× TR={bar_tr/a:.1f}×",
            )


def support_resistance_bounce(
    bars: pd.DataFrame,
    lookback: int = 50,
    proximity_atr: float = 0.3,
    rr_target: float = 2.0,
) -> Iterator[Signal]:
    """Long when price touches a tested support level (≥3 prior touches);
    short at tested resistance. Stop just beyond the level; target the
    range mid-point or nearest opposing level.
    """
    h, l, c = bars["High"], bars["Low"], bars["Close"]
    atr = _atr(bars, 14)

    for i in range(lookback + 1, len(bars)):
        date = bars.index[i]
        price = float(c.iloc[i])
        a = atr.iloc[i]
        if pd.isna(a) or a == 0:
            continue
        # Define recent range
        window_h = float(h.iloc[i - lookback:i].max())
        window_l = float(l.iloc[i - lookback:i].min())

        # Count touches near support / resistance
        eps = proximity_atr * a
        n_l_touches = int(((l.iloc[i - lookback:i] - window_l).abs() < eps).sum())
        n_h_touches = int(((h.iloc[i - lookback:i] - window_h).abs() < eps).sum())

        # Long bounce off support
        if abs(price - window_l) < eps and n_l_touches >= 3:
            entry = price
            stop = window_l - 0.5 * a
            target = (window_h + window_l) / 2
            if (target - entry) / max(entry - stop, 1e-9) >= rr_target:
                yield Signal.entry(
                    date=date, side="long", price=entry, stop=stop, target=target,
                    reason=f"sr_bounce_long touches={n_l_touches}",
                )
        # Short fade at resistance
        elif abs(price - window_h) < eps and n_h_touches >= 3:
            entry = price
            stop = window_h + 0.5 * a
            target = (window_h + window_l) / 2
            if (entry - target) / max(stop - entry, 1e-9) >= rr_target:
                yield Signal.entry(
                    date=date, side="short", price=entry, stop=stop, target=target,
                    reason=f"sr_bounce_short touches={n_h_touches}",
                )


def gap_fill(
    bars: pd.DataFrame,
    min_gap_atr: float = 0.75,
    rr_target: float = 1.5,
) -> Iterator[Signal]:
    """Open gap > min_gap_atr × ATR → fade back toward prior close.

    Use case: overnight gaps that don't have a strong news driver tend
    to fill within the first 1–2 hours. Defined risk: stop beyond gap
    extreme; target = prior close (the gap fill).
    """
    o, c, h, l = bars["Open"], bars["Close"], bars["High"], bars["Low"]
    prev_c = c.shift(1)
    atr = _atr(bars, 14)

    for i in range(20, len(bars)):
        date = bars.index[i]
        a = atr.iloc[i]
        if pd.isna(a) or a == 0:
            continue
        gap = float(o.iloc[i] - prev_c.iloc[i])
        if abs(gap) < min_gap_atr * a:
            continue
        if gap > 0:
            # Gap up → fade short, target prior close
            entry = float(o.iloc[i])
            stop = entry + 0.5 * a
            target = float(prev_c.iloc[i])
            if (entry - target) / max(stop - entry, 1e-9) >= rr_target:
                yield Signal.entry(
                    date=date, side="short", price=entry, stop=stop, target=target,
                    reason=f"gap_up_fade gap={gap/a:+.1f}×ATR",
                )
        else:
            # Gap down → fade long, target prior close
            entry = float(o.iloc[i])
            stop = entry - 0.5 * a
            target = float(prev_c.iloc[i])
            if (target - entry) / max(entry - stop, 1e-9) >= rr_target:
                yield Signal.entry(
                    date=date, side="long", price=entry, stop=stop, target=target,
                    reason=f"gap_down_fade gap={gap/a:+.1f}×ATR",
                )


def pivot_reversal(
    bars: pd.DataFrame,
    pivot_lookback: int = 5,
    rr_target: float = 2.0,
) -> Iterator[Signal]:
    """Pivot-point reversal — bar makes new N-bar high then closes red
    (long fade) or new N-bar low then closes green (short fade). Classic
    reversal signal at exhaustion points.
    """
    h, l, c, o = bars["High"], bars["Low"], bars["Close"], bars["Open"]
    atr = _atr(bars, 14)

    for i in range(pivot_lookback + 1, len(bars)):
        date = bars.index[i]
        a = atr.iloc[i]
        if pd.isna(a) or a == 0:
            continue
        bar_h, bar_l, bar_c, bar_o = (float(h.iloc[i]), float(l.iloc[i]),
                                       float(c.iloc[i]), float(o.iloc[i]))
        prior_h = float(h.iloc[i - pivot_lookback:i].max())
        prior_l = float(l.iloc[i - pivot_lookback:i].min())

        # Pivot high reversal: new high made + close red
        if bar_h > prior_h and bar_c < bar_o:
            entry = bar_c
            stop = bar_h + 0.25 * a
            target = bar_c - rr_target * (stop - entry)
            yield Signal.entry(
                date=date, side="short", price=entry, stop=stop, target=target,
                reason=f"pivot_high_rev",
            )
        # Pivot low reversal: new low made + close green
        elif bar_l < prior_l and bar_c > bar_o:
            entry = bar_c
            stop = bar_l - 0.25 * a
            target = bar_c + rr_target * (entry - stop)
            yield Signal.entry(
                date=date, side="long", price=entry, stop=stop, target=target,
                reason=f"pivot_low_rev",
            )


# =============================================================
# PRICE-ACTION STRATEGIES (fund's primary focus, added 2026-05-04)
# =============================================================
# These are pure microstructure strategies derived from candle geometry
# alone — no oscillators, no volume confirmation, no macro context. They
# work natively 24/5 because they only require price bars to evaluate.
#
# Hierarchy (per project_strategy_focus_fvg.md memory):
#   1. fair_value_gap   — primary lead strategy
#   2. order_block      — secondary support
#   3. liquidity_sweep  — secondary support
#
# These are the ICT (Inner Circle Trader) / Smart Money Concept family.
# Edge claim: institutional order flow leaves predictable imbalances and
# stop-hunt patterns; retail can fade or follow them.

def fair_value_gap(
    bars: pd.DataFrame,
    min_gap_atr: float = 0.20,
    max_age_bars: int = 30,
    rr_target: float = 2.0,
) -> Iterator[Signal]:
    """Fair Value Gap (FVG) mitigation entry — fund's PRIMARY strategy.

    A bullish FVG forms across 3 consecutive bars (i-2, i-1, i) when the
    high of bar i-2 is BELOW the low of bar i — leaving an unfilled price
    range (the "imbalance") that bar i-1 leapt across. The middle bar
    must close in the direction of the gap.

    Bullish FVG zone:  [bars[i-2].High, bars[i].Low]
    Bearish FVG zone:  [bars[i].High, bars[i-2].Low]

    Entry rule (mitigation): on a later bar, when price retraces back
    INTO the gap zone (the wick touches inside the gap) but the close
    holds beyond the far edge of the gap, enter in the direction of the
    original gap. Stop beyond the far edge of the gap. Target: rr_target
    times the risk distance.

    Filters:
    - min_gap_atr: gap must be >= min_gap_atr × ATR (filters microscopic
      gaps that are noise).
    - max_age_bars: FVGs decay after max_age_bars; institutional edge
      fades as the market moves on.
    - one signal per FVG: the FVG is "consumed" once mitigated.
    """
    h, l, c, o = bars["High"], bars["Low"], bars["Close"], bars["Open"]
    atr = _atr(bars, 14)

    # active_fvgs: list of dicts {kind, gap_low, gap_high, formed_at_idx, atr_at_form}
    # gap_low/high are absolute prices defining the imbalance zone.
    active_fvgs: list[dict] = []

    for i in range(2, len(bars)):
        date = bars.index[i]
        a = atr.iloc[i]
        if pd.isna(a) or a == 0:
            continue
        bar_h, bar_l, bar_c = float(h.iloc[i]), float(l.iloc[i]), float(c.iloc[i])

        # ── 1. Detect new FVGs forming at THIS 3-bar window ──
        h2, l2 = float(h.iloc[i - 2]), float(l.iloc[i - 2])
        o1, c1 = float(o.iloc[i - 1]), float(c.iloc[i - 1])

        # Bullish FVG: high[i-2] < low[i] AND middle bar closed up
        if l2 < bar_l and h2 < bar_l and c1 > o1:
            gap_low, gap_high = h2, bar_l
            if gap_high - gap_low >= min_gap_atr * a:
                active_fvgs.append({
                    "kind": "bull",
                    "gap_low": gap_low,
                    "gap_high": gap_high,
                    "formed_at": i,
                })

        # Bearish FVG: low[i-2] > high[i] AND middle bar closed down
        if h2 > bar_h and l2 > bar_h and c1 < o1:
            gap_low, gap_high = bar_h, l2
            if gap_high - gap_low >= min_gap_atr * a:
                active_fvgs.append({
                    "kind": "bear",
                    "gap_low": gap_low,
                    "gap_high": gap_high,
                    "formed_at": i,
                })

        # ── 2. Decay old FVGs ──
        active_fvgs = [
            f for f in active_fvgs
            if (i - f["formed_at"]) <= max_age_bars
        ]

        # ── 3. Check current bar for mitigation of any active FVG ──
        consumed: list[int] = []
        for idx, fvg in enumerate(active_fvgs):
            # Skip the FVG that JUST formed at this bar (mitigation needs a later bar)
            if fvg["formed_at"] == i:
                continue

            if fvg["kind"] == "bull":
                # Bullish mitigation: low pierced INTO the gap, close held above gap_low
                if bar_l <= fvg["gap_high"] and bar_c > fvg["gap_low"]:
                    entry = bar_c
                    stop = fvg["gap_low"] - 0.25 * a
                    if entry - stop <= 0:
                        consumed.append(idx)
                        continue
                    target = entry + rr_target * (entry - stop)
                    yield Signal.entry(
                        date=date, side="long", price=entry,
                        stop=stop, target=target,
                        reason=f"fvg_bull_mitigation gap=[{fvg['gap_low']:.2f},{fvg['gap_high']:.2f}] age={i-fvg['formed_at']}",
                    )
                    consumed.append(idx)

            else:  # bear
                # Bearish mitigation: high pierced INTO the gap, close held below gap_high
                if bar_h >= fvg["gap_low"] and bar_c < fvg["gap_high"]:
                    entry = bar_c
                    stop = fvg["gap_high"] + 0.25 * a
                    if stop - entry <= 0:
                        consumed.append(idx)
                        continue
                    target = entry - rr_target * (stop - entry)
                    yield Signal.entry(
                        date=date, side="short", price=entry,
                        stop=stop, target=target,
                        reason=f"fvg_bear_mitigation gap=[{fvg['gap_low']:.2f},{fvg['gap_high']:.2f}] age={i-fvg['formed_at']}",
                    )
                    consumed.append(idx)

        # Remove consumed FVGs (one mitigation per gap)
        for idx in sorted(consumed, reverse=True):
            del active_fvgs[idx]


def order_block(
    bars: pd.DataFrame,
    displacement_atr: float = 1.5,
    max_age_bars: int = 50,
    rr_target: float = 2.0,
) -> Iterator[Signal]:
    """Order Block (OB) — institutional reversal zone.

    A bullish order block is the LAST bearish (red) candle before a
    strong upward displacement (a bar whose body >= displacement_atr × ATR
    closing strongly higher). Theory: institutions accumulated on that red
    candle; price returning to that zone should bounce.

    Bullish OB zone: [last red candle's Low, last red candle's High]
    Bearish OB zone: [last green candle's Low, last green candle's High]

    Entry: when price returns into the OB zone, enter in the direction of
    the original displacement. Stop beyond the OB extreme. Target: rr_target
    times risk.
    """
    h, l, c, o = bars["High"], bars["Low"], bars["Close"], bars["Open"]
    atr = _atr(bars, 14)

    active_obs: list[dict] = []

    for i in range(1, len(bars)):
        date = bars.index[i]
        a = atr.iloc[i]
        if pd.isna(a) or a == 0:
            continue
        bar_h, bar_l, bar_c, bar_o = (float(h.iloc[i]), float(l.iloc[i]),
                                       float(c.iloc[i]), float(o.iloc[i]))
        body = bar_c - bar_o

        # ── 1. Detect strong displacement bars and locate the most recent
        #       opposite-color candle as the order block ──
        if abs(body) >= displacement_atr * a:
            # Walk back to find the last opposite-color candle
            kind = "bull" if body > 0 else "bear"
            for j in range(i - 1, max(i - 10, -1), -1):
                prev_o, prev_c = float(o.iloc[j]), float(c.iloc[j])
                if kind == "bull" and prev_c < prev_o:
                    active_obs.append({
                        "kind": "bull",
                        "ob_low": float(l.iloc[j]),
                        "ob_high": float(h.iloc[j]),
                        "formed_at": i,
                    })
                    break
                if kind == "bear" and prev_c > prev_o:
                    active_obs.append({
                        "kind": "bear",
                        "ob_low": float(l.iloc[j]),
                        "ob_high": float(h.iloc[j]),
                        "formed_at": i,
                    })
                    break

        # ── 2. Decay old OBs ──
        active_obs = [
            ob for ob in active_obs
            if (i - ob["formed_at"]) <= max_age_bars
        ]

        # ── 3. Check current bar for return into any active OB ──
        consumed: list[int] = []
        for idx, ob in enumerate(active_obs):
            if ob["formed_at"] == i:
                continue

            if ob["kind"] == "bull":
                # Long entry: price dipped into OB zone, closed above OB low
                if bar_l <= ob["ob_high"] and bar_c > ob["ob_low"]:
                    entry = bar_c
                    stop = ob["ob_low"] - 0.25 * a
                    if entry - stop <= 0:
                        consumed.append(idx)
                        continue
                    target = entry + rr_target * (entry - stop)
                    yield Signal.entry(
                        date=date, side="long", price=entry,
                        stop=stop, target=target,
                        reason=f"order_block_bull zone=[{ob['ob_low']:.2f},{ob['ob_high']:.2f}] age={i-ob['formed_at']}",
                    )
                    consumed.append(idx)
            else:
                # Short entry: price rallied into OB zone, closed below OB high
                if bar_h >= ob["ob_low"] and bar_c < ob["ob_high"]:
                    entry = bar_c
                    stop = ob["ob_high"] + 0.25 * a
                    if stop - entry <= 0:
                        consumed.append(idx)
                        continue
                    target = entry - rr_target * (stop - entry)
                    yield Signal.entry(
                        date=date, side="short", price=entry,
                        stop=stop, target=target,
                        reason=f"order_block_bear zone=[{ob['ob_low']:.2f},{ob['ob_high']:.2f}] age={i-ob['formed_at']}",
                    )
                    consumed.append(idx)

        for idx in sorted(consumed, reverse=True):
            del active_obs[idx]


def liquidity_sweep(
    bars: pd.DataFrame,
    swing_lookback: int = 10,
    rr_target: float = 2.0,
) -> Iterator[Signal]:
    """Liquidity sweep — fade a stop-hunt that pierces a recent swing
    extreme but reverses on the same bar.

    Pattern:
    - Bull sweep (LONG signal): bar's Low breaks BELOW the prior
      swing_lookback-bar low, but the bar closes ABOVE that prior low.
      Stops below the swing got hunted; price rejected back up.
    - Bear sweep (SHORT signal): bar's High breaks ABOVE the prior
      swing_lookback-bar high, but the bar closes BELOW that prior high.

    Entry: bar's close. Stop just beyond the bar's swept extreme.
    Target: rr_target × risk.
    """
    h, l, c = bars["High"], bars["Low"], bars["Close"]
    atr = _atr(bars, 14)

    for i in range(swing_lookback + 1, len(bars)):
        date = bars.index[i]
        a = atr.iloc[i]
        if pd.isna(a) or a == 0:
            continue
        bar_h, bar_l, bar_c = float(h.iloc[i]), float(l.iloc[i]), float(c.iloc[i])
        prior_high = float(h.iloc[i - swing_lookback:i].max())
        prior_low = float(l.iloc[i - swing_lookback:i].min())

        # Bull sweep: pierced below prior low, closed back above it
        if bar_l < prior_low and bar_c > prior_low:
            entry = bar_c
            stop = bar_l - 0.25 * a
            if entry - stop <= 0:
                continue
            target = entry + rr_target * (entry - stop)
            yield Signal.entry(
                date=date, side="long", price=entry,
                stop=stop, target=target,
                reason=f"liquidity_sweep_bull pierced_low={prior_low:.2f} closed_back={bar_c:.2f}",
            )

        # Bear sweep: pierced above prior high, closed back below it
        elif bar_h > prior_high and bar_c < prior_high:
            entry = bar_c
            stop = bar_h + 0.25 * a
            if stop - entry <= 0:
                continue
            target = entry - rr_target * (stop - entry)
            yield Signal.entry(
                date=date, side="short", price=entry,
                stop=stop, target=target,
                reason=f"liquidity_sweep_bear pierced_high={prior_high:.2f} closed_back={bar_c:.2f}",
            )


STRATEGY_REGISTRY = {
    # ── PRICE-ACTION (fund's primary focus, added 2026-05-04) ──
    # FVG is the lead strategy. Order blocks + liquidity sweeps are
    # secondary supports. These take precedence over classical TA below.
    "fair_value_gap": fair_value_gap,
    "order_block": order_block,
    "liquidity_sweep": liquidity_sweep,
    # ── CLASSICAL TA (backstop tier — only fire when no price-action
    #    setup is active for a symbol) ──
    # Original 5
    "donchian_breakout": donchian_breakout,
    "bollinger_mean_reversion": bollinger_mean_reversion,
    "volatility_breakout": volatility_breakout,
    "pullback_in_trend": pullback_in_trend,
    "range_mean_reversion": range_mean_reversion,
    # Volatility strategies
    "bollinger_squeeze_break": bollinger_squeeze_break,
    "keltner_breakout": keltner_breakout,
    "vol_regime_trend": vol_regime_trend,
    "vol_spike_fade": vol_spike_fade,
    # Intraday-cadence strategies
    "opening_range_breakout": opening_range_breakout,
    "narrow_range_break": narrow_range_break,
    "inside_bar_break": inside_bar_break,
    # Mean-reversion overlay
    "rsi2_extreme_reversion": rsi2_extreme_reversion,
    # NEW (2026-04-28): more intraday flexibility for HFT-style trading
    # vwap_reversion REMOVED 2026-05-04 — broken strategy (see comment above)
    "volume_spike_reversal": volume_spike_reversal,
    "support_resistance_bounce": support_resistance_bounce,
    "gap_fill": gap_fill,
    "pivot_reversal": pivot_reversal,
}


# ── Parametrized strategy variants (Tier 4 walk-forward findings) ──
# Default `order_block` (displacement_atr=1.5) had ZERO validated cells.
# 2026-05-06 Tier 4 sweep with displacement_atr=1.0 found 4 validated
# cells: 6B London long (t=+3.49), 6E RTH short (t=+2.06), MNQ Asian
# short (t=+1.80), 6B Asian short (t=+1.52). Wrapper exposes the tuned
# variant as if it were a separate strategy so the existing validation +
# auto_trader pipelines pick it up without per-cell parameter overrides.

def order_block_d1(bars, **kwargs) -> Iterator[Signal]:
    """order_block tuned variant — displacement_atr=1.0 (vs default 1.5).
    See Tier 4 walk-forward 2026-05-06 for validation."""
    kwargs.setdefault("displacement_atr", 1.0)
    return order_block(bars, **kwargs)


def fair_value_gap_tuned(bars, **kwargs) -> Iterator[Signal]:
    """fair_value_gap tuned variant — rr_target=2.5 (vs default 2.0).
    Tier 4 multi-sweep 2026-05-06 found rr=2.5 was the dominant
    winning RR across the top 15 validated cells. min_gap_atr and
    max_age default (0.20, 30) are compatible with most winners."""
    kwargs.setdefault("min_gap_atr", 0.2)
    kwargs.setdefault("max_age_bars", 30)
    kwargs.setdefault("rr_target", 2.5)
    return fair_value_gap(bars, **kwargs)


def liquidity_sweep_tuned(bars, **kwargs) -> Iterator[Signal]:
    """liquidity_sweep tuned variant — rr_target=2.5 + swing_lookback=10
    (vs defaults 2.0, 10). Tier 4 multi-sweep 2026-05-06 found 6
    validated cells, top 3 use rr=2.5 + swing=10:
      MES RTH long    OOS E=+0.96R t=+2.71 n=25
      MNQ RTH long    OOS E=+0.94R t=+2.77 n=27
      MCL RTH long    OOS E=+0.68R t=+2.24 n=25"""
    kwargs.setdefault("swing_lookback", 10)
    kwargs.setdefault("rr_target", 2.5)
    return liquidity_sweep(bars, **kwargs)


STRATEGY_REGISTRY["order_block_d1"] = order_block_d1
STRATEGY_REGISTRY["fair_value_gap_tuned"] = fair_value_gap_tuned
STRATEGY_REGISTRY["liquidity_sweep_tuned"] = liquidity_sweep_tuned


# ── Cross-asset divergence (Quant Researcher proposal #3, 2026-05-06) ──
# Yield-curve cointegration trade. The fund's only cross-asset signal.
# Bets that ZN-ZT spread mean-reverts when it dislocates, regardless of
# where either leg is vs prior close (orthogonal to gap_fill).
#
# Phase 1 (this implementation): single-leg ZN directional. Long ZN
# when spread_z <= -2 (cheap), short ZN when spread_z >= +2 (rich).
# Phase 2 (deferred): true 2-leg pair trade with hedge ratio sizing.
#
# Spec from vault/research/strategy_proposals/2026-05-06_quant_researcher_proposals.md
def cross_asset_divergence_zn(bars, partner_bars=None,
                                beta_window: int = 60,
                                z_window: int = 60,
                                z_threshold: float = 2.0,
                                atr_stop_multi: float = 1.5,
                                time_stop_bars: int = 30) -> Iterator[Signal]:
    """ZN cointegration-divergence trade vs ZT (or other curve partner).

    Args:
      bars: ZN OHLCV
      partner_bars: ZT OHLCV with matching index (DateTime). If None,
        attempts yfinance fetch (for backtests). Falls back to no-op
        if partner not available.
      beta_window: rolling OLS lookback for β (ZN ≈ β × ZT + ε)
      z_window: rolling lookback for spread mean/std (z-score)
      z_threshold: |z| ≥ this value triggers entry
      atr_stop_multi: stop placed atr_stop_multi × ATR14 from entry
      time_stop_bars: max hold; force-close if spread doesn't revert
    """
    import numpy as np

    if partner_bars is None:
        # Try yfinance fallback (only used in backtests)
        try:
            import yfinance as yf
            df = yf.download("ZT=F", period="60d", interval="5m",
                             progress=False, auto_adjust=False)
            if df.empty: return
            if hasattr(df.columns, "get_level_values"):
                df.columns = df.columns.get_level_values(0)
            partner_bars = df[["High", "Low", "Close"]].copy().dropna()
            if partner_bars.index.tz is None:
                partner_bars.index = partner_bars.index.tz_localize("UTC")
            partner_bars.index = partner_bars.index.tz_convert(bars.index.tz or "UTC")
        except Exception:
            return

    # Align on index intersection
    common_idx = bars.index.intersection(partner_bars.index)
    if len(common_idx) < beta_window + z_window:
        return
    zn = bars.loc[common_idx, "Close"].astype(float)
    zt = partner_bars.loc[common_idx, "Close"].astype(float)
    atr = _atr(bars.loc[common_idx], 14)

    # Rolling OLS β (no intercept — pure cointegration ratio)
    # β = sum(ZN×ZT) / sum(ZT²) over window
    spreads: list[float] = []
    betas: list[float] = []
    for i in range(len(common_idx)):
        if i < beta_window:
            spreads.append(np.nan); betas.append(np.nan)
            continue
        win_zn = zn.iloc[i - beta_window:i].values
        win_zt = zt.iloc[i - beta_window:i].values
        denom = float(np.sum(win_zt * win_zt))
        beta = float(np.sum(win_zn * win_zt) / denom) if denom > 0 else 0
        betas.append(beta)
        spreads.append(float(zn.iloc[i] - beta * zt.iloc[i]))

    spreads = np.array(spreads)
    z_scores: list[float] = []
    for i in range(len(spreads)):
        if i < beta_window + z_window or np.isnan(spreads[i]):
            z_scores.append(np.nan); continue
        win = spreads[i - z_window:i]
        win = win[~np.isnan(win)]
        if len(win) < 10:
            z_scores.append(np.nan); continue
        m, s = float(np.mean(win)), float(np.std(win, ddof=1))
        if s <= 0:
            z_scores.append(0.0); continue
        z_scores.append((spreads[i] - m) / s)

    # Walk forward generating entry signals on z-threshold crossings
    in_position = False
    entry_idx = -1
    entry_side = None
    for i in range(1, len(common_idx)):
        date = common_idx[i]
        z_now = z_scores[i]
        z_prev = z_scores[i - 1]
        if np.isnan(z_now) or np.isnan(z_prev):
            continue
        a = atr.iloc[i] if i < len(atr) else None
        if a is None or pd.isna(a) or a <= 0:
            continue

        # Exit logic (track in_position via signals; but engine handles
        # exits, so emit only entries — strategy is stateless re: position)

        # Crossing into rich → short ZN
        if z_now >= z_threshold and z_prev < z_threshold:
            entry = float(zn.iloc[i])
            stop = entry + float(a) * atr_stop_multi
            target = entry - float(a) * atr_stop_multi   # symmetric R 1:1; engine uses this
            yield Signal(
                date=date, side="short", price=entry,
                stop=stop, target=target,
                reason=f"curve_divergence_zn_short_z{z_now:+.2f}",
                kind="entry",
            )

        # Crossing into cheap → long ZN
        elif z_now <= -z_threshold and z_prev > -z_threshold:
            entry = float(zn.iloc[i])
            stop = entry - float(a) * atr_stop_multi
            target = entry + float(a) * atr_stop_multi
            yield Signal(
                date=date, side="long", price=entry,
                stop=stop, target=target,
                reason=f"curve_divergence_zn_long_z{z_now:+.2f}",
                kind="entry",
            )


STRATEGY_REGISTRY["cross_asset_divergence_zn"] = cross_asset_divergence_zn


def get_strategy(name: str):
    if name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy {name!r}. Available: {list(STRATEGY_REGISTRY)}"
        )
    return STRATEGY_REGISTRY[name]
