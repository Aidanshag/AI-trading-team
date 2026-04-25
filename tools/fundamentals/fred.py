"""FRED (Federal Reserve Economic Data) loader.

Free API. Works without a key but rate-limited. With FRED_API_KEY in env,
higher rate limits. Sign up: https://fred.stlouisfed.org/docs/api/api_key.html

Common series the fund cares about (dict at bottom: FRED_SERIES_COMMON).
"""

from __future__ import annotations

import os
from datetime import date

import httpx
import pandas as pd

from . import cache

BASE = "https://api.stlouisfed.org/fred/series/observations"


def load_series(
    series_id: str,
    start: str | date,
    end: str | date,
    api_key: str | None = None,
    frequency: str | None = None,
) -> pd.DataFrame:
    """Load a single FRED series.

    Args:
        series_id: e.g. 'DGS10' (10-year Treasury), 'CPIAUCSL' (CPI), 'DTWEXBGS' (DXY).
        start/end: ISO date strings or date objects.
        api_key: FRED API key (else uses FRED_API_KEY env). REQUIRED — FRED
            no longer serves anonymous requests.
        frequency: None | 'd' | 'w' | 'm' | 'q' — resample/aggregate via API.

    Returns:
        DataFrame with DatetimeIndex and a single 'value' column (float).
    """
    key = api_key or os.environ.get("FRED_API_KEY")
    if not key:
        raise RuntimeError(
            "FRED_API_KEY required. Free signup (30 seconds): "
            "https://fred.stlouisfed.org/docs/api/api_key.html"
        )
    start_s = str(start)
    end_s = str(end)

    def fetch() -> pd.DataFrame:
        params = {
            "series_id": series_id,
            "observation_start": start_s,
            "observation_end": end_s,
            "file_type": "json",
            "api_key": key,
        }
        if frequency:
            params["frequency"] = frequency

        r = httpx.get(BASE, params=params, timeout=30.0)
        r.raise_for_status()
        data = r.json()
        obs = data.get("observations", [])
        if not obs:
            return pd.DataFrame(columns=["value"])
        df = pd.DataFrame(obs)
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
        # FRED returns "." for missing values — coerce to NaN
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        return df[["value"]]

    return cache.load_or_fetch("fred", series_id, fetch,
                                start=start_s, end=end_s, frequency=frequency or "")


# Curated series the fund references most
FRED_SERIES_COMMON = {
    # Rates / Treasury
    "DGS2": "2-year Treasury yield",
    "DGS5": "5-year Treasury yield",
    "DGS10": "10-year Treasury yield",
    "DGS30": "30-year Treasury yield",
    "T10Y2Y": "10Y-2Y spread",
    "DFF": "Effective Fed Funds Rate",
    # Inflation
    "CPIAUCSL": "CPI All Urban (headline)",
    "CPILFESL": "Core CPI (ex food+energy)",
    "PCEPILFE": "Core PCE",
    "DFII10": "10-year TIPS real yield",
    "T10YIE": "10-year breakeven inflation",
    # Dollar
    "DTWEXBGS": "Trade-weighted US Dollar Broad",
    # Credit
    "BAMLH0A0HYM2": "HY-IG OAS (credit spread)",
    # Jobs / activity
    "PAYEMS": "Nonfarm Payrolls",
    "UNRATE": "Unemployment Rate",
    "ICSA": "Initial Jobless Claims (weekly)",
    # ISM + leading
    "INDPRO": "Industrial Production",
    # Money
    "M2SL": "M2 Money Stock",
    "WALCL": "Fed Balance Sheet",
    "RRPONTSYD": "Reverse Repo",
}


def load_common(name: str, start: str, end: str) -> pd.DataFrame:
    """Shortcut for the series the fund references most."""
    if name not in FRED_SERIES_COMMON:
        raise ValueError(
            f"Unknown common series {name!r}. "
            f"Known: {sorted(FRED_SERIES_COMMON)}"
        )
    return load_series(name, start, end)
