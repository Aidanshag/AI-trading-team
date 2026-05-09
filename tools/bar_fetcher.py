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
        minutes: bar size in minutes (default 5; supports 1, 5, 15, 30, 60, etc.)
        lookback: how many bars to request (default 200)
        log_fn: optional logger function to receive errors

    Returns:
        DataFrame with columns Open/High/Low/Close/Volume indexed by Date,
        or None if fetch fails or no bars.

    Notes:
        - For minutes=1 with large lookback (>1000), use fetch_bars_paginated
          instead. ProjectX limits each request to 1000 bars.
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
            unit=2, unit_number=minutes, limit=min(lookback, 1000),
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


def fetch_bars_paginated(
    client,
    symbol: str,
    minutes: int = 1,
    days: int = 60,
    log_fn: Callable[[str], None] | None = None,
) -> pd.DataFrame | None:
    """Fetch high-resolution bars over multi-day windows by paginating.

    For 1-minute bars over 60 days = ~25,920 bars/symbol; ProjectX caps
    requests at 1000 bars, so we page through in chunks.

    Args:
        client: ProjectXClient
        symbol: e.g. "ZN"
        minutes: bar size (default 1 — finer than 5m default)
        days: how many trailing days to fetch (default 60)
        log_fn: optional logger

    Returns:
        DataFrame OHLCV indexed by Date, or None on failure.
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
        target_start = end - timedelta(days=days)
        # Page backwards in chunks of ~16 hours of 1-min bars (≈1000 bars)
        # For 5-min bars, ~83 hours. Compute chunk size in minutes:
        chunk_minutes = minutes * 1000  # max bars per request
        cur_end = end
        all_dfs = []
        while cur_end > target_start:
            cur_start = cur_end - timedelta(minutes=chunk_minutes)
            if cur_start < target_start:
                cur_start = target_start
            bars = client.get_bars(
                contract_id=cid,
                start_time=cur_start.isoformat(),
                end_time=cur_end.isoformat(),
                unit=2, unit_number=minutes, limit=1000,
                live=False,
            )
            if not bars:
                break
            df = pd.DataFrame(bars).rename(
                columns={"t": "Date", "o": "Open", "h": "High",
                         "l": "Low", "c": "Close", "v": "Volume"},
            )
            df["Date"] = pd.to_datetime(df["Date"])
            df = df.set_index("Date")
            all_dfs.append(df)
            # Step backward; subtract 1 minute to avoid overlap
            cur_end = cur_start - timedelta(minutes=1)
            if len(bars) < 100:
                # End of available data
                break
        if not all_dfs:
            return None
        full = pd.concat(all_dfs).sort_index()
        full = full[~full.index.duplicated(keep="first")]
        return full.dropna()
    except Exception as e:
        if log_fn:
            log_fn(f"fetch_bars_paginated {symbol}: {type(e).__name__}: {e}")
        return None
