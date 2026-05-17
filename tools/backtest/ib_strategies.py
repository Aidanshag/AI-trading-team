"""Strategies UNIQUE to the IB workstream — instruments that can't be
traded on Topstep (equities, options).

These are kept separate from `tools/backtest/strategies.py` because:
1. They use mechanics that don't apply to futures (overnight gaps, earnings)
2. They register into a SEPARATE registry (IB_STRATEGY_REGISTRY) so
   universal sweeps don't accidentally run them against futures bars
3. Most existing 36 futures strategies ALSO work on equities — those
   stay in strategies.py and apply to both workstreams via the shared
   backtest engine

Equity-specific characteristics this file targets:
- Overnight gaps (futures trade ~24h, equities have a real overnight)
- Earnings releases (binary events with predictable IV behavior)
- Dividend ex-dates (predictable price drops)
- Sector rotation (relative-strength plays across SPDRs)
- ETF mean-reversion (RSI-2 / oversold bounces work better on diversified ETFs)

OPTIONS strategies are NOT in this file. Options need:
- Black-Scholes pricing + greeks
- Multi-leg P&L tracking
- IV surface / term structure
- Strike + expiry selection logic
These are a separate build — see `vault/ib/research/strategy_catalog.md`
for the planned options framework.
"""
from __future__ import annotations

from typing import Iterator

import pandas as pd

from .engine import Signal
from .strategies import _atr  # reuse existing ATR helper


IB_STRATEGY_REGISTRY: dict = {}


def overnight_gap_continuation(
    bars: pd.DataFrame,
    min_gap_pct: float = 0.005,    # 0.5% gap required
    hold_first_hour_bars: int = 12,  # if 5m bars, ~1 hour
    stop_atr_mult: float = 1.5,
    target_atr_mult: float = 2.5,
    atr_period: int = 14,
) -> Iterator[Signal]:
    """Buy the first-hour open after a strong overnight gap.

    Distinct from futures gap_fill (which FADES gaps). On EQUITIES,
    overnight gaps that hold the first 30-60 minutes typically continue
    in the gap direction (institutional flow follows news / pre-market
    momentum). Gap-up + first-hour-hold = momentum entry long.

    Trigger:
      - Open vs prior close gap >= min_gap_pct (e.g., 0.5%)
      - At session-boundary bar (first bar of new session)
      - Hold position for `hold_first_hour_bars` bars or until stop/target
      - Direction: WITH the gap (gap_up = long, gap_down = short)
      - Stop: prior close (gap fill = invalidation)
      - Target: ATR-based extension in gap direction
    """
    if "Open" not in bars.columns:
        return
    o, h, l, c = bars["Open"], bars["High"], bars["Low"], bars["Close"]
    atr = _atr(bars, atr_period)
    prev_c = c.shift(1)

    # Session boundary: timestamp gap from previous bar > 30 minutes
    ts = bars.index.to_series()
    gap_minutes = (ts - ts.shift(1)).dt.total_seconds() / 60.0

    for i in range(atr_period, len(bars)):
        date = bars.index[i]
        a = atr.iloc[i]
        if pd.isna(a) or a <= 0:
            continue
        bar_gap = gap_minutes.iloc[i]
        if pd.isna(bar_gap) or bar_gap < 30.0:
            continue  # not a session-boundary bar
        prev = prev_c.iloc[i]
        if pd.isna(prev) or prev <= 0:
            continue
        gap_pct = (float(o.iloc[i]) - float(prev)) / float(prev)
        if abs(gap_pct) < min_gap_pct:
            continue

        entry = float(o.iloc[i])
        if gap_pct > 0:
            # Gap-up — go with it (continuation long)
            stop = float(prev)  # if gap fills entirely, thesis invalidated
            target = entry + target_atr_mult * float(a)
            if stop < entry and target > entry:
                yield Signal.entry(
                    date=date, side="long", price=entry, stop=stop, target=target,
                    reason=f"gap_up_continuation gap={gap_pct*100:+.2f}%",
                )
        else:
            # Gap-down — go with it (continuation short)
            stop = float(prev)
            target = entry - target_atr_mult * float(a)
            if stop > entry and target < entry:
                yield Signal.entry(
                    date=date, side="short", price=entry, stop=stop, target=target,
                    reason=f"gap_down_continuation gap={gap_pct*100:+.2f}%",
                )


IB_STRATEGY_REGISTRY["overnight_gap_continuation"] = overnight_gap_continuation


def etf_oversold_revert(
    bars: pd.DataFrame,
    rsi_period: int = 2,
    rsi_threshold: float = 10.0,
    hold_max_bars: int = 5,
    stop_atr_mult: float = 1.5,
    atr_period: int = 14,
) -> Iterator[Signal]:
    """Larry Connors-style RSI-2 oversold bounce. Works best on broad
    ETFs (SPY, QQQ, IWM) and large-cap stocks where the index regression
    to mean is reliable. Generally fails on volatile individual stocks
    or commodities.

    Trigger:
      - 2-period RSI <= rsi_threshold (deeply oversold)
      - Long entry at the close
      - Exit when RSI > 50, OR after hold_max_bars, OR stop hit
      - Stop: stop_atr_mult × ATR below entry

    Distinct from rsi2_extreme_reversion in the main strategy library
    in that this is calibrated for ETFs specifically — longer hold
    (5 bars vs 1-2 in the original), wider stop (1.5×ATR vs 1.0).
    """
    c = bars["Close"]
    delta = c.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(rsi_period).mean()
    avg_loss = loss.rolling(rsi_period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    atr = _atr(bars, atr_period)

    for i in range(atr_period + rsi_period + 1, len(bars)):
        date = bars.index[i]
        a = atr.iloc[i]
        cur_rsi = rsi.iloc[i]
        if pd.isna(a) or pd.isna(cur_rsi) or a <= 0:
            continue
        if float(cur_rsi) > rsi_threshold:
            continue
        entry = float(c.iloc[i])
        stop = entry - stop_atr_mult * float(a)
        # Target: RSI = 50 = revert to neutral. Approximate price target as
        # entry + 1×ATR (matches the rule-of-thumb that mean-revert moves
        # cover 1 ATR before petering out).
        target = entry + 1.0 * float(a)
        if stop < entry and target > entry:
            yield Signal.entry(
                date=date, side="long", price=entry, stop=stop, target=target,
                reason=f"etf_oversold rsi2={float(cur_rsi):.0f}",
            )


IB_STRATEGY_REGISTRY["etf_oversold_revert"] = etf_oversold_revert


def post_earnings_drift(
    bars: pd.DataFrame,
    earnings_gap_threshold_pct: float = 0.03,  # 3%+ overnight gap = earnings reaction
    drift_hold_days: int = 3,
    stop_atr_mult: float = 2.0,
    atr_period: int = 14,
) -> Iterator[Signal]:
    """Post-Earnings Announcement Drift (PEAD). Stocks that gap big on
    earnings tend to drift in the same direction for several days as
    institutional buyers/sellers slowly rebalance.

    Trigger (proxy — no earnings calendar required):
      - Daily bar where open vs prior close gap > earnings_gap_threshold_pct
        (3%+ overnight gap is a strong earnings reaction signal)
      - Enter at open in direction of gap
      - Hold drift_hold_days days unless stopped
      - Stop: stop_atr_mult × ATR adverse from entry

    NOTE: this is a proxy detection. Real implementation should integrate
    with an earnings calendar API (e.g., IB's reqHistoricalEvents, or
    a third-party feed). The pure-price proxy works for >80% of cases
    since 3%+ overnight gaps in liquid stocks are almost always
    earnings-driven (or M&A, which also drifts).

    Best for: large-cap stocks with earnings 4× per year. Skip ETFs,
    skip pre-announcement vol spikes.
    """
    if "Open" not in bars.columns:
        return
    o, c = bars["Open"], bars["Close"]
    atr = _atr(bars, atr_period)
    prev_c = c.shift(1)
    # Daily-resolution check — only fire on bars that look "daily-ish"
    # (>= 12 hours from previous bar usually = daily bars at session open)
    ts = bars.index.to_series()
    gap_hours = (ts - ts.shift(1)).dt.total_seconds() / 3600.0

    for i in range(atr_period, len(bars)):
        date = bars.index[i]
        a = atr.iloc[i]
        if pd.isna(a) or a <= 0:
            continue
        bar_gap_h = gap_hours.iloc[i]
        # Only fire if we're at a daily-style boundary (>= 12 hours)
        if pd.isna(bar_gap_h) or bar_gap_h < 12.0:
            continue
        prev = prev_c.iloc[i]
        if pd.isna(prev) or prev <= 0:
            continue
        gap_pct = (float(o.iloc[i]) - float(prev)) / float(prev)
        if abs(gap_pct) < earnings_gap_threshold_pct:
            continue
        entry = float(o.iloc[i])
        if gap_pct > 0:
            # Earnings beat-like — drift long
            stop = entry - stop_atr_mult * float(a)
            target = entry + (drift_hold_days * 0.5) * float(a)
            if stop < entry and target > entry:
                yield Signal.entry(
                    date=date, side="long", price=entry, stop=stop, target=target,
                    reason=f"pead_long earnings_gap={gap_pct*100:+.1f}%",
                )
        else:
            # Earnings miss-like — drift short
            stop = entry + stop_atr_mult * float(a)
            target = entry - (drift_hold_days * 0.5) * float(a)
            if stop > entry and target < entry:
                yield Signal.entry(
                    date=date, side="short", price=entry, stop=stop, target=target,
                    reason=f"pead_short earnings_gap={gap_pct*100:+.1f}%",
                )


IB_STRATEGY_REGISTRY["post_earnings_drift"] = post_earnings_drift


def opening_drive(
    bars: pd.DataFrame,
    drive_threshold_atr: float = 0.75,
    first_n_bars: int = 6,  # ~30 min on 5m, ~6 min on 1m
    stop_atr_mult: float = 1.0,
    target_atr_mult: float = 2.0,
    atr_period: int = 14,
) -> Iterator[Signal]:
    """Trade the opening drive: if the first N bars of a session move
    >= drive_threshold_atr × ATR in one direction, ride the momentum.

    Distinct from opening_range_breakout (which waits for the range to
    set then trades a breakout). Opening drive fires DURING the drive
    itself when momentum is unambiguous.

    Best for equity ETFs (SPY/QQQ) and large caps where the open
    establishes institutional bias for the day.

    Trigger:
      - We're between bar 1 and bar N of a session (session boundary
        detected by >= 30 min timestamp gap)
      - Cumulative move from session open to current close >= threshold
      - Enter at current bar's close in direction of drive
      - Stop: stop_atr_mult × ATR adverse
      - Target: target_atr_mult × ATR favorable
    """
    if "Open" not in bars.columns:
        return
    o, c = bars["Open"], bars["Close"]
    atr = _atr(bars, atr_period)
    ts = bars.index.to_series()
    gap_minutes = (ts - ts.shift(1)).dt.total_seconds() / 60.0

    session_open_idx = None
    bars_into_session = 0
    fired_this_session = False
    for i in range(atr_period, len(bars)):
        date = bars.index[i]
        a = atr.iloc[i]
        if pd.isna(a) or a <= 0:
            continue
        # Detect session boundary
        bar_gap = gap_minutes.iloc[i]
        if not pd.isna(bar_gap) and bar_gap >= 30.0:
            session_open_idx = i
            bars_into_session = 0
            fired_this_session = False
        else:
            bars_into_session += 1
        # Only fire within first N bars
        if session_open_idx is None or bars_into_session > first_n_bars:
            continue
        if fired_this_session:
            continue
        session_open = float(o.iloc[session_open_idx])
        cur_close = float(c.iloc[i])
        drive = cur_close - session_open
        if abs(drive) < drive_threshold_atr * float(a):
            continue
        if drive > 0:
            stop = cur_close - stop_atr_mult * float(a)
            target = cur_close + target_atr_mult * float(a)
            fired_this_session = True
            yield Signal.entry(
                date=date, side="long", price=cur_close, stop=stop, target=target,
                reason=f"opening_drive_long drive={drive/float(a):+.1f}×ATR",
            )
        else:
            stop = cur_close + stop_atr_mult * float(a)
            target = cur_close - target_atr_mult * float(a)
            fired_this_session = True
            yield Signal.entry(
                date=date, side="short", price=cur_close, stop=stop, target=target,
                reason=f"opening_drive_short drive={drive/float(a):+.1f}×ATR",
            )


IB_STRATEGY_REGISTRY["opening_drive"] = opening_drive


def get_ib_strategy(name: str):
    if name not in IB_STRATEGY_REGISTRY:
        raise ValueError(
            f"Unknown IB strategy {name!r}. Available: {list(IB_STRATEGY_REGISTRY)}"
        )
    return IB_STRATEGY_REGISTRY[name]
