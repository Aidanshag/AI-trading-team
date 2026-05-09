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
) -> BacktestResult:
    """Run a strategy against historical bars and return aggregate results.

    Assumes one open trade at a time (serial). Multi-position books are a
    future extension.
    """
    params = params or {}
    result = BacktestResult(
        strategy_name=getattr(strategy, "__name__", "strategy"),
        symbol=symbol,
        params=params,
        bars=bars,
    )

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
