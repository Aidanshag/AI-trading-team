"""Tests for tools/passive_entry_shadow."""
from __future__ import annotations

import pandas as pd

from tools.passive_entry_shadow import (
    simulate_passive_entry,
    ASSUMED_LIVE_BUFFER_TICKS,
)


def _bars(closes_lows_highs: list[tuple[float, float, float]]) -> pd.DataFrame:
    """Build a tiny DataFrame from (Close, Low, High) tuples."""
    return pd.DataFrame([
        {"Close": c, "Low": l, "High": h}
        for c, l, h in closes_lows_highs
    ])


def test_long_passive_fills_when_low_crosses_signal_price():
    """Long entry at $100, bar 2's Low drops to $99.5 — fills at $100."""
    sig = {"price": 100.0, "side": "long"}
    bars = _bars([(100.5, 100.2, 100.7), (99.8, 99.5, 100.3)])  # bar2 Low=99.5
    out = simulate_passive_entry(sig, bars, tick_size=0.1)
    assert out["passive_filled"] is True
    assert out["passive_fill_price"] == 100.0
    assert out["fill_within_min"] == 2
    # Live would fill at 100 + 5*0.1 = 100.5; delta = 100 - 100.5 = -0.5 → -5 ticks
    assert out["delta_ticks"] == -ASSUMED_LIVE_BUFFER_TICKS


def test_long_passive_misses_when_market_never_crosses():
    """Long entry at $100, all bars stay above → never fills."""
    sig = {"price": 100.0, "side": "long"}
    bars = _bars([(100.5, 100.3, 100.7)] * 6)  # 6 bars, never below 100
    out = simulate_passive_entry(sig, bars, tick_size=0.1)
    assert out["passive_filled"] is False
    assert out["fill_within_min"] is None


def test_short_passive_fills_when_high_crosses_up():
    """Short entry at $100, bar 1's High reaches $100.5 — fills at $100."""
    sig = {"price": 100.0, "side": "short"}
    bars = _bars([(99.7, 99.5, 100.5)])  # High touched 100.5 → fills at 100
    out = simulate_passive_entry(sig, bars, tick_size=0.1)
    assert out["passive_filled"] is True
    assert out["passive_fill_price"] == 100.0
    # Live = 100 - 5*0.1 = 99.5; delta = 99.5 - 100 = -0.5 → -5 ticks (cheaper)
    assert out["delta_ticks"] == -ASSUMED_LIVE_BUFFER_TICKS


def test_invalid_signal_returns_error():
    out = simulate_passive_entry({"price": 0, "side": "long"},
                                    _bars([(100, 100, 100)]), tick_size=0.1)
    assert "error" in out


def test_fill_timeout_after_5_min():
    """If market doesn't cross until bar 7, FILL_TIMEOUT_MIN=5 → no fill."""
    sig = {"price": 100.0, "side": "long"}
    # First 6 bars don't cross, bar 7 does
    bars = _bars([(100.5, 100.3, 100.7)] * 6 + [(100.0, 99.5, 100.5)])
    out = simulate_passive_entry(sig, bars, tick_size=0.1)
    assert out["passive_filled"] is False
