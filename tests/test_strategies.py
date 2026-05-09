"""Smoke tests for the strategy registry.

Each strategy must:
  1. Import and be discoverable via STRATEGY_REGISTRY
  2. Run on synthetic OHLC bars without raising
  3. Produce signals with valid stop placement (not on the wrong side of entry)

This is not a profitability test — that's the backtest harness's job.
This is a "does the code work and not lie about its risk" test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from tools.backtest.strategies import STRATEGY_REGISTRY
from tools.backtest.engine import backtest_strategy


def _synthetic_bars(n: int = 500, seed: int = 7) -> pd.DataFrame:
    """Random walk with a touch of trend + intermittent vol regime shifts."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    drift = 0.0003
    base_vol = 0.012
    # Inject vol regime shifts so vol-aware strategies have something to find
    regime = np.where((np.arange(n) // 50) % 2 == 0, 1.0, 2.5)
    rets = drift + base_vol * regime * rng.standard_normal(n)
    close = 100 * np.exp(np.cumsum(rets))
    # Open ≈ prior close; intrabar high/low ≈ ±0.7% noise
    high = close * (1 + np.abs(rng.standard_normal(n)) * 0.007)
    low = close * (1 - np.abs(rng.standard_normal(n)) * 0.007)
    open_ = np.concatenate([[close[0]], close[:-1]])
    return pd.DataFrame(
        {"Open": open_, "High": high, "Low": low, "Close": close},
        index=dates,
    )


@pytest.fixture(scope="module")
def bars() -> pd.DataFrame:
    return _synthetic_bars()


@pytest.mark.parametrize("name", list(STRATEGY_REGISTRY))
def test_strategy_runs(name: str, bars: pd.DataFrame):
    """Strategy executes end-to-end without raising."""
    strat = STRATEGY_REGISTRY[name]
    result = backtest_strategy(strat, bars, symbol="TEST")
    assert result is not None
    assert result.strategy_name


@pytest.mark.parametrize("name", list(STRATEGY_REGISTRY))
def test_strategy_stops_are_correct_side(name: str, bars: pd.DataFrame):
    """For every entry signal, stop must be on the loss side of entry.
    This catches sign-flip bugs that would silently produce 'free money'
    backtests.
    """
    strat = STRATEGY_REGISTRY[name]
    sigs = list(strat(bars))
    entries = [s for s in sigs if s.kind == "entry"]
    for s in entries:
        if s.stop is None:
            continue
        if s.side == "long":
            assert s.stop < s.price, (
                f"{name}: long entry @ {s.price:.2f} has stop {s.stop:.2f} "
                f"ABOVE entry — sign bug"
            )
        else:
            assert s.stop > s.price, (
                f"{name}: short entry @ {s.price:.2f} has stop {s.stop:.2f} "
                f"BELOW entry — sign bug"
            )


@pytest.mark.parametrize("name", list(STRATEGY_REGISTRY))
def test_strategy_targets_are_correct_side(name: str, bars: pd.DataFrame):
    """If a target is set, it must be on the profit side of entry."""
    strat = STRATEGY_REGISTRY[name]
    sigs = list(strat(bars))
    entries = [s for s in sigs if s.kind == "entry"]
    for s in entries:
        if s.target is None:
            continue
        if s.side == "long":
            assert s.target > s.price, (
                f"{name}: long target {s.target:.2f} not above entry {s.price:.2f}"
            )
        else:
            assert s.target < s.price, (
                f"{name}: short target {s.target:.2f} not below entry {s.price:.2f}"
            )


def test_registry_size():
    """Lock in the count so accidental deletions are loud."""
    assert len(STRATEGY_REGISTRY) >= 13, (
        f"Strategy registry shrunk to {len(STRATEGY_REGISTRY)} — original 5 + "
        f"8 new should give >= 13"
    )


def test_new_strategies_present():
    """The 8 new strategies must all be registered."""
    new = {
        "bollinger_squeeze_break",
        "keltner_breakout",
        "vol_regime_trend",
        "vol_spike_fade",
        "opening_range_breakout",
        "narrow_range_break",
        "inside_bar_break",
        "rsi2_extreme_reversion",
    }
    missing = new - set(STRATEGY_REGISTRY)
    assert not missing, f"Missing from registry: {missing}"
