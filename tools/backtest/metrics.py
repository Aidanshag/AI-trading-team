"""Summary stats computation for BacktestResult."""

from __future__ import annotations

import numpy as np
import pandas as pd

from .engine import BacktestResult


def summary_stats(result: BacktestResult) -> dict:
    """Return a dict of human-readable stats. Handles empty results safely."""
    if not result.trades:
        return {
            "strategy": result.strategy_name,
            "symbol": result.symbol,
            "params": result.params,
            "n_trades": 0,
            "note": "no trades — strategy didn't fire or bars too short",
        }

    ec = result.equity_curve
    sharpe = _naive_sharpe(ec) if ec is not None else 0.0

    wins = result.wins
    losses = result.losses
    profit_factor = (
        sum(t.r_multiple for t in wins) / abs(sum(t.r_multiple for t in losses))
        if losses else float("inf")
    )

    # Trade duration stats
    durations = [
        (t.exit_date - t.entry_date).days for t in result.trades
        if t.exit_date is not None
    ]

    return {
        "strategy": result.strategy_name,
        "symbol": result.symbol,
        "params": result.params,
        "n_trades": result.n_trades,
        "n_wins": len(wins),
        "n_losses": len(losses),
        "hit_rate": result.hit_rate,
        "avg_r": result.avg_r,
        "avg_win_r": result.avg_win_r,
        "avg_loss_r": result.avg_loss_r,
        "total_r": result.total_r,
        "max_drawdown_r": result.max_drawdown_r,
        "profit_factor": profit_factor,
        "sharpe_naive": sharpe,
        "avg_duration_days": float(np.mean(durations)) if durations else 0.0,
        "max_duration_days": int(np.max(durations)) if durations else 0,
    }


def _naive_sharpe(equity: pd.Series, periods_per_year: int = 252) -> float:
    """Sharpe on the R-multiple daily-equity delta. Naive; no risk-free adjustment."""
    daily = equity.diff().dropna()
    if daily.std() == 0 or len(daily) < 2:
        return 0.0
    return float((daily.mean() / daily.std()) * np.sqrt(periods_per_year))


def format_summary(result: BacktestResult) -> str:
    """Human-readable text summary."""
    s = summary_stats(result)
    if s["n_trades"] == 0:
        return f"{s['strategy']} on {s['symbol']}: no trades.\nparams: {s['params']}"

    lines = [
        f"Backtest: {s['strategy']} on {s['symbol']}",
        f"Params: {s['params']}",
        "",
        f"Trades:      {s['n_trades']}  ({s['n_wins']} wins / {s['n_losses']} losses)",
        f"Hit rate:    {s['hit_rate']:.1%}",
        f"Avg R:       {s['avg_r']:+.2f}",
        f"Avg win R:   {s['avg_win_r']:+.2f}",
        f"Avg loss R:  {s['avg_loss_r']:+.2f}",
        f"Total R:     {s['total_r']:+.1f}",
        f"Max DD R:    {s['max_drawdown_r']:+.1f}",
        f"Profit factor: {s['profit_factor']:.2f}",
        f"Sharpe (naive): {s['sharpe_naive']:.2f}",
        f"Avg trade duration: {s['avg_duration_days']:.1f} days",
    ]
    return "\n".join(lines)
