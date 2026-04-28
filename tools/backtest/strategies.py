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


STRATEGY_REGISTRY = {
    # Original 5
    "donchian_breakout": donchian_breakout,
    "bollinger_mean_reversion": bollinger_mean_reversion,
    "volatility_breakout": volatility_breakout,
    "pullback_in_trend": pullback_in_trend,
    "range_mean_reversion": range_mean_reversion,
    # New volatility strategies
    "bollinger_squeeze_break": bollinger_squeeze_break,
    "keltner_breakout": keltner_breakout,
    "vol_regime_trend": vol_regime_trend,
    "vol_spike_fade": vol_spike_fade,
    # New intraday-cadence strategies
    "opening_range_breakout": opening_range_breakout,
    "narrow_range_break": narrow_range_break,
    "inside_bar_break": inside_bar_break,
    # Mean-reversion overlay
    "rsi2_extreme_reversion": rsi2_extreme_reversion,
}


def get_strategy(name: str):
    if name not in STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown strategy {name!r}. Available: {list(STRATEGY_REGISTRY)}"
        )
    return STRATEGY_REGISTRY[name]
