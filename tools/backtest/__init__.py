"""Backtest harness for the fund's strategy library.

Public interface:

    from tools.backtest import load_bars, backtest_strategy
    from tools.backtest.strategies import donchian_breakout

    bars = load_bars("CL=F", "2020-01-01", "2025-01-01", source="yfinance")
    result = backtest_strategy(donchian_breakout, bars, params={"lookback": 20})
    print(result)

Or via CLI:

    python -m tools.backtest run --strategy donchian_breakout \\
        --symbol CL=F --start 2020-01-01 --end 2025-01-01
"""
from .data import load_bars, available_sources
from .engine import backtest_strategy, BacktestResult
from .metrics import summary_stats

__all__ = [
    "load_bars",
    "available_sources",
    "backtest_strategy",
    "BacktestResult",
    "summary_stats",
]
