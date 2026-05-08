"""Topstep bar fetcher — extracted from scripts/live_trader.py 2026-05-08
to keep the trader focused on execution.

Single responsibility: pull recent N-min bars for a symbol from broker.
Returns a pandas DataFrame indexed by timestamp, OHLCV columns.
"""
from __future__ import annotations

from datetime import timedelta
from typing import Callable

import pandas as pd

from tools.trader_utils import _now_utc


def fetch_bars(
    client,
    symbol: str,
    minutes: int = 5,
    lookback: int = 200,
    log_fn: Callable[[str], None] | None = None,
) -> pd.DataFrame | None:
    """Fetch front-month bars for `symbol`.

    Args:
        client: ProjectXClient instance with search_contracts + get_bars
        symbol: e.g. "ZN", "ZB", "NG"
        minutes: bar size in minutes (default 5)
        lookback: how many bars to request (default 200)
        log_fn: optional logger function to receive errors

    Returns:
        DataFrame with columns Open/High/Low/Close/Volume indexed by Date,
        or None if fetch fails or no bars.
    """
    try:
        contracts = client.search_contracts(symbol, live=False)
        if not contracts:
            return None
        front = sorted(
            contracts,
            key=lambda c: c.get("expiryDate") or c.get("lastTradeDate") or "",
        )[0]
        cid = front.get("id") or front.get("contractId")
        end = _now_utc()
        start = end - timedelta(minutes=minutes * lookback * 2)
        bars = client.get_bars(
            contract_id=cid,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            unit=2, unit_number=minutes, limit=lookback,
            live=False,
        )
        if not bars:
            return None
        df = pd.DataFrame(bars).rename(
            columns={"t": "Date", "o": "Open", "h": "High",
                     "l": "Low", "c": "Close", "v": "Volume"},
        )
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        return df.dropna()
    except Exception as e:
        if log_fn:
            log_fn(f"fetch_bars {symbol}: {type(e).__name__}: {e}")
        return None
