"""EIA (Energy Information Administration) loader.

Free API but requires a key: https://www.eia.gov/opendata/register.php
Set EIA_API_KEY in .env.

Covers weekly petroleum inventories, natural gas storage, production.
"""

from __future__ import annotations

import os
from datetime import date

import httpx
import pandas as pd

from . import cache

BASE = "https://api.eia.gov/v2"


def _require_key() -> str:
    key = os.environ.get("EIA_API_KEY")
    if not key:
        raise RuntimeError(
            "EIA_API_KEY not set. Register free at "
            "https://www.eia.gov/opendata/register.php and add to .env."
        )
    return key


def load_series(
    path: str,
    frequency: str = "weekly",
    start: str | date | None = None,
    end: str | date | None = None,
    facets: dict | None = None,
    value_column: str = "value",
) -> pd.DataFrame:
    """Low-level EIA v2 API wrapper.

    Args:
        path: API path e.g. 'petroleum/stoc/wstk' or 'natural-gas/stor/wkly'.
        frequency: 'weekly' | 'monthly' | 'daily' | 'annual'.
        start/end: ISO date.
        facets: filter dict e.g. {'series': ['WCESTUS1']}.
    """
    key = _require_key()
    start_s = str(start) if start else ""
    end_s = str(end) if end else ""

    def fetch() -> pd.DataFrame:
        params = {
            "api_key": key,
            "frequency": frequency,
            "data[0]": value_column,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
            "offset": "0",
            "length": "5000",
        }
        if start_s:
            params["start"] = start_s
        if end_s:
            params["end"] = end_s
        if facets:
            for k, vs in facets.items():
                for i, v in enumerate(vs):
                    params[f"facets[{k}][{i}]"] = v

        url = f"{BASE}/{path.strip('/')}/data/"
        r = httpx.get(url, params=params, timeout=30.0)
        r.raise_for_status()
        data = r.json()
        rows = data.get("response", {}).get("data", [])
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df["period"] = pd.to_datetime(df["period"])
        df = df.set_index("period").sort_index()
        if value_column in df.columns:
            df[value_column] = pd.to_numeric(df[value_column], errors="coerce")
        return df

    return cache.load_or_fetch("eia", path, fetch,
                                start=start_s, end=end_s,
                                facets=str(facets) if facets else "")


# Convenience wrappers for the series the fund uses most
def crude_stocks(start: str, end: str) -> pd.DataFrame:
    """US weekly ending stocks of crude oil (thousand barrels)."""
    return load_series(
        "petroleum/stoc/wstk",
        frequency="weekly",
        start=start,
        end=end,
        facets={"series": ["WCESTUS1"]},  # ending stocks ex-SPR
    )


def gasoline_stocks(start: str, end: str) -> pd.DataFrame:
    """US weekly ending stocks of total gasoline (thousand barrels)."""
    return load_series(
        "petroleum/stoc/wstk",
        frequency="weekly",
        start=start,
        end=end,
        facets={"series": ["WGTSTUS1"]},
    )


def distillate_stocks(start: str, end: str) -> pd.DataFrame:
    """US weekly ending stocks of distillate fuel oil (thousand barrels)."""
    return load_series(
        "petroleum/stoc/wstk",
        frequency="weekly",
        start=start,
        end=end,
        facets={"series": ["WDISTUS1"]},
    )


def natgas_storage(start: str, end: str) -> pd.DataFrame:
    """US weekly working gas in underground storage (billion cubic feet)."""
    return load_series(
        "natural-gas/stor/wkly",
        frequency="weekly",
        start=start,
        end=end,
        facets={"series": ["NW2_EPG0_SWO_R48_BCF"]},
    )


def weekly_surprise(series_fn, start: str, end: str, lookback: int = 52) -> pd.DataFrame:
    """Compute the week-over-week change in a stocks/storage series.

    Returns a DataFrame with columns: value, change, z_score (change vs
    trailing `lookback` weeks of changes).
    """
    df = series_fn(start, end).copy()
    if df.empty:
        return df
    col = [c for c in df.columns if c != "period"][0] if df.columns.size else "value"
    # Get the numeric column
    num_cols = df.select_dtypes(include=["number"]).columns
    if not num_cols.size:
        return df
    value_col = num_cols[0]
    df["change"] = df[value_col].diff()
    df["z_score"] = (
        (df["change"] - df["change"].rolling(lookback).mean())
        / df["change"].rolling(lookback).std()
    )
    return df
