"""Backtest engine.

A strategy is a callable that takes a bars DataFrame + params and yields
trade signals. The engine processes signals, honors stops/targets/trailing,
and produces a BacktestResult with the full trade list + equity curve.

Strategy protocol:

    def my_strategy(bars: pd.DataFrame, **params) -> Iterator[Signal]:
        for i in range(len(bars)):
            # decide on entry / exit given bars.iloc[:i+1] (no lookahead)
            if should_enter:
                yield Signal.entry(date=bars.index[i], side="long",
                                   price=bars['Close'].iloc[i],
                                   stop=stop, target=target)

The engine handles position accounting, P&L, R-multiples.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Iterator, Literal

import numpy as np
import pandas as pd

Side = Literal["long", "short"]


# 2026-05-15: min_stop_ticks floor enforced at the engine level to kill
# the sub-tick stop collapse bug. Strategies using ATR-based stops
# can compute stop distance ≈ 0 in low-vol regimes; division-by-tiny-epsilon
# in r-multiple computation inflated t-stats by orders of magnitude.
# Pattern B failure shape (see vault/_meta/analysis/2026-05-07_lesson_meta_patterns.md).
#
# Symbol-aware tick sizes mirror hooks/risk_gate._normalize_root +
# tools/profit_protect._TICK_ECONOMICS. Any entry signal whose stop is
# closer than MIN_STOP_TICKS_DEFAULT * tick_size from entry is DROPPED
# at signal-processing time — it never becomes a Trade and never
# pollutes the t-stat.
_TICK_SIZES_BY_SYMBOL: dict[str, float] = {
    # Metals
    "MGC": 0.10, "GC": 0.10, "GCE": 0.10,
    "SI": 0.005, "SIL": 0.005, "SIE": 0.005,
    "HG": 0.0005, "MHG": 0.0005, "CPE": 0.0005,
    "PL": 0.10, "PLE": 0.10,
    # Equity index
    "ES": 0.25, "MES": 0.25, "EP": 0.25,
    "NQ": 0.25, "MNQ": 0.25, "ENQ": 0.25,
    "RTY": 0.10, "M2K": 0.10, "TNA": 0.10,
    "YM": 1.00, "MYM": 0.50,
    "NKD": 5.00,
    "MBT": 5.0,
    # Energies
    "CL": 0.01, "MCL": 0.01, "CLE": 0.01, "MCLE": 0.01,
    "NG": 0.001, "MNG": 0.005, "NGE": 0.001,
    "QG": 0.005, "NQG": 0.005, "QM": 0.025, "NQM": 0.025,
    "HO": 0.0001, "HOE": 0.0001, "RB": 0.0001, "RBE": 0.0001,
    # Rates
    "ZN": 0.015625, "TYA": 0.015625,
    "ZB": 0.03125, "ZF": 0.0078125, "FVA": 0.0078125,
    "ZT": 0.0078125, "TUA": 0.0078125,
    "US": 0.03125, "USA": 0.03125, "UL": 0.03125, "ULA": 0.03125,
    # FX
    "6E": 0.00005, "EU6": 0.00005, "M6E": 0.00005,
    "6B": 0.0001, "BP6": 0.0001, "M6B": 0.0001,
    "6A": 0.0001, "DA6": 0.0001, "M6A": 0.0001,
    "6C": 0.00005, "CA6": 0.00005,
    "6J": 0.0000005, "JY6": 0.0000005,
    "6S": 0.00005, "SF6": 0.00005,
    "6N": 0.0001, "NE6": 0.0001,
    "MX6": 0.00001, "E7": 0.0001, "EEU": 0.0001,
    # Grains / livestock
    "ZC": 0.0025, "ZCE": 0.0025,
    "ZS": 0.0025, "ZSE": 0.0025,
    "ZW": 0.0025, "ZWA": 0.0025,
    "ZL": 0.0001, "ZLE": 0.0001,
    "ZM": 0.10, "ZME": 0.10,
    "LE": 0.025, "GLE": 0.025,
    "HE": 0.025,
    "GMET": 0.10,
}

MIN_STOP_TICKS_DEFAULT = 6   # matches scripts/live_trader.MIN_SIGNAL_R_TICKS


@dataclass
class Signal:
    """Signal emitted by a strategy."""
    kind: Literal["entry", "exit"]
    date: pd.Timestamp
    side: Side = "long"
    price: float = 0.0
    stop: float | None = None
    target: float | None = None
    reason: str = ""

    @classmethod
    def entry(cls, date, side, price, stop, target=None, reason=""):
        return cls("entry", date, side, price, stop, target, reason)

    @classmethod
    def exit(cls, date, price, reason=""):
        return cls("exit", date, price=price, reason=reason)


@dataclass
class Trade:
    entry_date: pd.Timestamp
    entry_price: float
    side: Side
    stop: float
    target: float | None
    exit_date: pd.Timestamp | None = None
    exit_price: float | None = None
    exit_reason: str = ""
    r_multiple: float = 0.0

    @property
    def is_open(self) -> bool:
        return self.exit_date is None

    def close(self, date, price, reason: str):
        self.exit_date = date
        self.exit_price = price
        self.exit_reason = reason
        risk = abs(self.entry_price - self.stop)
        if risk == 0:
            self.r_multiple = 0.0
        else:
            pnl = (price - self.entry_price) if self.side == "long" else (self.entry_price - price)
            self.r_multiple = pnl / risk


@dataclass
class BacktestResult:
    strategy_name: str
    symbol: str
    params: dict
    trades: list[Trade] = field(default_factory=list)
    equity_curve: pd.Series | None = None
    bars: pd.DataFrame | None = None  # retained for reporting

    @property
    def n_trades(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> list[Trade]:
        return [t for t in self.trades if t.r_multiple > 0]

    @property
    def losses(self) -> list[Trade]:
        return [t for t in self.trades if t.r_multiple <= 0]

    @property
    def hit_rate(self) -> float:
        return len(self.wins) / len(self.trades) if self.trades else 0.0

    @property
    def avg_r(self) -> float:
        return float(np.mean([t.r_multiple for t in self.trades])) if self.trades else 0.0

    @property
    def avg_win_r(self) -> float:
        return float(np.mean([t.r_multiple for t in self.wins])) if self.wins else 0.0

    @property
    def avg_loss_r(self) -> float:
        return float(np.mean([t.r_multiple for t in self.losses])) if self.losses else 0.0

    @property
    def total_r(self) -> float:
        return float(sum(t.r_multiple for t in self.trades))

    @property
    def max_drawdown_r(self) -> float:
        if not self.trades:
            return 0.0
        cum = np.cumsum([t.r_multiple for t in self.trades])
        peak = np.maximum.accumulate(cum)
        dd = cum - peak
        return float(dd.min())

    def __repr__(self) -> str:
        if not self.trades:
            return f"BacktestResult({self.strategy_name}, 0 trades)"
        return (
            f"BacktestResult({self.strategy_name} on {self.symbol}, "
            f"{self.n_trades} trades, hit={self.hit_rate:.1%}, "
            f"avg_R={self.avg_r:+.2f}, total_R={self.total_r:+.1f}, "
            f"max_dd={self.max_drawdown_r:+.1f}R)"
        )


def backtest_strategy(
    strategy: Callable[..., Iterator[Signal]],
    bars: pd.DataFrame,
    symbol: str = "",
    params: dict | None = None,
    min_stop_ticks: int | None = None,
) -> BacktestResult:
    """Run a strategy against historical bars and return aggregate results.

    Assumes one open trade at a time (serial). Multi-position books are a
    future extension.

    2026-05-15: applies min_stop_ticks floor — entry signals whose stop
    is < `min_stop_ticks * tick_size_for_symbol` from entry are SKIPPED.
    Kills the sub-tick-stop t-stat inflation Pattern B failure. Default
    is MIN_STOP_TICKS_DEFAULT (6); pass 0 to disable the floor (regression
    tests + research that wants raw output).
    """
    params = params or {}
    if min_stop_ticks is None:
        min_stop_ticks = MIN_STOP_TICKS_DEFAULT
    tick_size = _TICK_SIZES_BY_SYMBOL.get(symbol, 0.0)
    min_stop_distance = (min_stop_ticks * tick_size) if tick_size > 0 else 0.0

    result = BacktestResult(
        strategy_name=getattr(strategy, "__name__", "strategy"),
        symbol=symbol,
        params=params,
        bars=bars,
    )
    # Counters for the dropped-signal floor (informational; could surface
    # via BacktestResult later if needed)
    result._floor_dropped_count = 0  # type: ignore[attr-defined]

    open_trade: Trade | None = None
    closed_trades: list[Trade] = []

    # We walk bars day by day. On each day:
    # (1) If a trade is open, check stop/target against this day's High/Low.
    # (2) Then pull strategy signals for this day (strategy sees bars up to
    #     and including this bar's close; no lookahead).
    # Strategies emit signals; we execute them at the CURRENT bar's close.

    # Pre-compute all signals (strategies are pure; this simplifies the loop)
    signals_by_date: dict[pd.Timestamp, list[Signal]] = {}
    for sig in strategy(bars, **params):
        signals_by_date.setdefault(sig.date, []).append(sig)

    for i in range(len(bars)):
        date = bars.index[i]
        row = bars.iloc[i]

        # (1) Intrabar stop/target check on existing open trade
        if open_trade is not None:
            h, l = row["High"], row["Low"]
            if open_trade.side == "long":
                if open_trade.stop is not None and l <= open_trade.stop:
                    open_trade.close(date, open_trade.stop, "stop")
                    closed_trades.append(open_trade)
                    open_trade = None
                elif open_trade.target is not None and h >= open_trade.target:
                    open_trade.close(date, open_trade.target, "target")
                    closed_trades.append(open_trade)
                    open_trade = None
            else:  # short
                if open_trade.stop is not None and h >= open_trade.stop:
                    open_trade.close(date, open_trade.stop, "stop")
                    closed_trades.append(open_trade)
                    open_trade = None
                elif open_trade.target is not None and l <= open_trade.target:
                    open_trade.close(date, open_trade.target, "target")
                    closed_trades.append(open_trade)
                    open_trade = None

        # (2) Process signals for this bar
        for sig in signals_by_date.get(date, []):
            if sig.kind == "entry" and open_trade is None:
                # Floor check: drop signals with sub-tick stops. Kills
                # the t-stat inflation Pattern B from sub-tick ATR collapse.
                if min_stop_distance > 0 and sig.stop is not None:
                    stop_distance = abs(sig.price - sig.stop)
                    if stop_distance < min_stop_distance:
                        result._floor_dropped_count += 1  # type: ignore[attr-defined]
                        continue
                open_trade = Trade(
                    entry_date=date,
                    entry_price=sig.price,
                    side=sig.side,
                    stop=sig.stop or 0.0,
                    target=sig.target,
                )
            elif sig.kind == "exit" and open_trade is not None:
                open_trade.close(date, sig.price, sig.reason or "signal")
                closed_trades.append(open_trade)
                open_trade = None

    # Force-close any remaining open trade at the last bar
    if open_trade is not None:
        last_date = bars.index[-1]
        last_close = float(bars["Close"].iloc[-1])
        open_trade.close(last_date, last_close, "end_of_data")
        closed_trades.append(open_trade)

    result.trades = closed_trades
    result.equity_curve = _compute_equity_curve(closed_trades, bars.index)
    return result


def _compute_equity_curve(trades: list[Trade], index: pd.DatetimeIndex) -> pd.Series:
    """Cumulative R series indexed by trade exit date, forward-filled on the bar index."""
    if not trades:
        return pd.Series(0.0, index=index)
    events = pd.Series(
        [t.r_multiple for t in trades],
        index=[t.exit_date for t in trades],
    )
    cum = events.cumsum()
    # Align to bar index, forward-fill between exits, start at 0
    equity = cum.reindex(index).ffill().fillna(0.0)
    return equity
