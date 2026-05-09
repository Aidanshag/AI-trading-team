"""Event-driven backtest strategies.

These combine price bars with fundamental event data (FRED / EIA / USDA
/ CFTC). They implement the real strategies our playbooks document —
unlike the pure-price `strategies.py` which was a harness smoke-test.
"""

from __future__ import annotations

from typing import Iterator

import numpy as np
import pandas as pd

from tools.backtest.engine import Signal
from tools.backtest.strategies import _atr


def eia_crude_surprise_continuation(
    bars: pd.DataFrame,
    eia_changes: pd.DataFrame,
    surprise_threshold_z: float = 1.5,
    atr_period: int = 20,
    stop_atr_mult: float = 1.5,
    target_r: float = 2.0,
    hold_sessions: int = 3,
) -> Iterator[Signal]:
    """Continuation on large EIA crude-stocks surprise.

    After an EIA report with weekly change > threshold sigma from trailing mean,
    enter in the direction of the surprise at the next day's close. Hold up
    to `hold_sessions` sessions or stop/target.

    Sign convention: DRAW (negative stocks change) is bullish crude → long.
                     BUILD (positive stocks change) is bearish crude → short.

    Args:
        bars: daily OHLCV of CL=F (or equivalent).
        eia_changes: DataFrame from eia.weekly_surprise(eia.crude_stocks, ...).
            Must have 'z_score' column and DatetimeIndex aligned to weekly EIA release.
        surprise_threshold_z: abs z-score threshold to trigger entry.
        atr_period / stop_atr_mult / target_r: standard stop/target params.
        hold_sessions: max days to hold before time-stop exit.
    """
    atr = _atr(bars, atr_period)

    # For each EIA release date with surprise > threshold, the NEXT daily
    # bar's close is the entry trigger. Because EIA releases Wednesday
    # 10:30 ET, we use the FOLLOWING daily bar to avoid lookahead.
    release_dates = eia_changes.index
    surprises: dict[pd.Timestamp, float] = {}
    if "z_score" in eia_changes.columns:
        for dt, z in eia_changes["z_score"].items():
            if pd.notna(z) and abs(z) >= surprise_threshold_z:
                # EIA is weekly; map to the next bar date in `bars`
                next_bar = bars.index[bars.index > dt]
                if len(next_bar) > 0:
                    surprises[next_bar[0]] = z

    in_trade = False
    entry_bar = None
    direction: str = "long"

    for i in range(len(bars)):
        date = bars.index[i]
        row = bars.iloc[i]
        close = float(row["Close"])

        # Handle time-stop exit
        if in_trade and entry_bar is not None:
            if (i - entry_bar) >= hold_sessions:
                in_trade = False
                entry_bar = None
                yield Signal.exit(date=date, price=close, reason="time_stop")
                continue

        if not in_trade and date in surprises:
            if i < atr_period or pd.isna(atr.iloc[i]):
                continue
            a = float(atr.iloc[i])
            z = surprises[date]
            # Negative z (stock draw) = bullish crude → long
            # Positive z (stock build) = bearish crude → short
            # Per firm rule: no outright short futures. Shorts would need
            # defined-risk structure — here we record a short-signal but
            # skip it in the mechanical backtest to stay consistent.
            if z < 0:
                direction = "long"
                entry = close
                stop = entry - stop_atr_mult * a
                target = entry + target_r * stop_atr_mult * a
                in_trade = True
                entry_bar = i
                yield Signal.entry(
                    date=date, side="long", price=entry, stop=stop, target=target,
                    reason=f"EIA_draw_z={z:+.2f}",
                )
            # else: short signal — skip outright per firm rule


# Registry addendum
EVENT_STRATEGY_REGISTRY = {
    "eia_crude_surprise_continuation": eia_crude_surprise_continuation,
}
