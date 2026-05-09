"""Data loaders for the backtest harness.

Pluggable sources. Each source normalizes to a pandas DataFrame with:
    index: DatetimeIndex (tz-naive, daily bars)
    columns: Open, High, Low, Close, Volume
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd

Source = Literal["yfinance", "firstrate_csv"]


def available_sources() -> list[str]:
    return ["yfinance", "firstrate_csv"]


def load_bars(
    symbol: str,
    start: str,
    end: str,
    source: Source = "yfinance",
    **kwargs,
) -> pd.DataFrame:
    """Load daily OHLC bars for a symbol from the given source.

    Args:
        symbol: source-specific symbol. For yfinance, continuous futures like
            'CL=F', 'GC=F', 'ES=F', 'ZC=F'. For firstrate_csv, the filename
            stem (e.g., 'CL' expects 'data/firstrate/CL.csv').
        start: ISO date 'YYYY-MM-DD'.
        end:   ISO date 'YYYY-MM-DD' (exclusive).
        source: 'yfinance' (free) or 'firstrate_csv' (paid one-time purchase).
        **kwargs: source-specific options (e.g., csv_path for firstrate).

    Returns:
        DataFrame with DatetimeIndex and OHLCV columns.
    """
    if source == "yfinance":
        return _load_yfinance(symbol, start, end)
    if source == "firstrate_csv":
        return _load_firstrate(symbol, start, end, **kwargs)
    raise ValueError(f"Unknown source: {source!r}. Available: {available_sources()}")


def _load_yfinance(symbol: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf

    df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=False)
    if df.empty:
        raise ValueError(f"No data returned for {symbol} {start} → {end}")

    # yfinance 0.2+ returns MultiIndex columns when multiple tickers; flatten for single ticker
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Normalize column names
    df = df.rename(columns={
        "Open": "Open", "High": "High", "Low": "Low",
        "Close": "Close", "Adj Close": "AdjClose", "Volume": "Volume",
    })
    keep = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def _load_firstrate(
    symbol: str,
    start: str,
    end: str,
    csv_path: str | Path | None = None,
) -> pd.DataFrame:
    """Load a FirstRate Data daily-bar CSV.

    FirstRate typically ships CSV with columns: datetime,open,high,low,close,volume.
    Conventional path: data/firstrate/{SYMBOL}.csv.
    """
    if csv_path is None:
        csv_path = Path("data/firstrate") / f"{symbol}.csv"
    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(
            f"FirstRate CSV not found at {csv_path}. "
            "Place files under data/firstrate/ or pass csv_path=..."
        )

    df = pd.read_csv(csv_path)
    # FirstRate column convention varies; try common patterns
    date_col = next((c for c in df.columns if c.lower() in ("datetime", "date", "timestamp")), None)
    if date_col is None:
        raise ValueError(f"No datetime column in {csv_path}. Columns: {list(df.columns)}")

    df[date_col] = pd.to_datetime(df[date_col])
    df = df.set_index(date_col).sort_index()
    df.index.name = "Date"

    # Normalize column names (case-insensitive)
    rename_map = {}
    for col in df.columns:
        lc = col.lower()
        if lc == "open":   rename_map[col] = "Open"
        elif lc == "high":  rename_map[col] = "High"
        elif lc == "low":   rename_map[col] = "Low"
        elif lc == "close": rename_map[col] = "Close"
        elif lc == "volume": rename_map[col] = "Volume"
    df = df.rename(columns=rename_map)

    df = df.loc[start:end]
    return df[["Open", "High", "Low", "Close", "Volume"]].copy()
