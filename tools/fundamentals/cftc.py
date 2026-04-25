"""CFTC Commitments of Traders (COT) loader.

Free — no key needed. CFTC publishes weekly CSVs. We use the public
Socrata API hosted at publicreporting.cftc.gov for structured access.

Reports:
- 'legacy' : long-standing format; categories = Commercial / Non-Commercial / Non-Reportable
- 'disaggregated' : newer; categories = Producer/Merchant, Swap Dealers, Managed Money, Other Reportables
- 'financial' : for financial futures (rates, FX, indexes)

Typical use: compare Managed Money positioning vs historical range to
identify positioning extremes.
"""

from __future__ import annotations

from datetime import date

import httpx
import pandas as pd

from . import cache

# Socrata resource IDs (stable public endpoints)
RESOURCES = {
    "legacy":         "jun7-fc8e",    # Legacy Futures Only
    "disaggregated":  "72hh-3qpy",    # Disaggregated Futures Only
    "financial":      "gpe5-46if",    # Traders in Financial Futures
}

BASE = "https://publicreporting.cftc.gov/resource"


# Common market name mappings (CFTC's market_and_exchange_names field is
# messy; these are tested matches for our tradeable universe).
MARKET_PATTERNS = {
    # Energies
    "crude_wti":    "CRUDE OIL, LIGHT SWEET-NYMEX",
    "natgas":       "NAT GAS NYME-NEW YORK MERCANTILE EXCHANGE",
    "gasoline":     "GASOLINE RBOB-NEW YORK MERCANTILE EXCHANGE",
    "heating_oil":  "NY HARBOR ULSD-NEW YORK MERCANTILE EXCHANGE",
    # Metals
    "gold":         "GOLD-COMMODITY EXCHANGE INC.",
    "silver":       "SILVER-COMMODITY EXCHANGE INC.",
    "copper":       "COPPER-COMMODITY EXCHANGE INC.",
    # Grains
    "corn":         "CORN-CHICAGO BOARD OF TRADE",
    "soybeans":     "SOYBEANS-CHICAGO BOARD OF TRADE",
    "wheat":        "WHEAT-CHICAGO BOARD OF TRADE",
    # Rates
    "10y_note":     "UST 10Y NOTE-CHICAGO BOARD OF TRADE",
    "30y_bond":     "UST BOND-CHICAGO BOARD OF TRADE",
    # FX
    "eur":          "EURO FX-CHICAGO MERCANTILE EXCHANGE",
    "gbp":          "BRITISH POUND-CHICAGO MERCANTILE EXCHANGE",
    "jpy":          "JAPANESE YEN-CHICAGO MERCANTILE EXCHANGE",
    # Indexes
    "sp500":        "E-MINI S&P 500-CHICAGO MERCANTILE EXCHANGE",
    "nasdaq":       "NASDAQ-100 Consolidated-CHICAGO MERCANTILE EXCHANGE",
}


def commitments(
    market: str,
    start: str | date,
    end: str | date,
    report: str = "disaggregated",
) -> pd.DataFrame:
    """Load weekly COT data for a named market.

    Returns a DataFrame indexed by report date with positioning columns.
    """
    if market not in MARKET_PATTERNS:
        raise ValueError(
            f"Unknown market {market!r}. Known: {sorted(MARKET_PATTERNS)}"
        )
    if report not in RESOURCES:
        raise ValueError(
            f"Unknown report {report!r}. Use {list(RESOURCES)}."
        )

    market_name = MARKET_PATTERNS[market]
    resource_id = RESOURCES[report]
    start_s = str(start)
    end_s = str(end)

    def fetch() -> pd.DataFrame:
        url = f"{BASE}/{resource_id}.json"
        # Socrata SoQL query
        where = (
            f"market_and_exchange_names='{market_name}' "
            f"AND report_date_as_yyyy_mm_dd>='{start_s}T00:00:00' "
            f"AND report_date_as_yyyy_mm_dd<='{end_s}T00:00:00'"
        )
        params = {
            "$where": where,
            "$order": "report_date_as_yyyy_mm_dd ASC",
            "$limit": "5000",
        }
        r = httpx.get(url, params=params, timeout=30.0)
        r.raise_for_status()
        rows = r.json()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        # Normalize date column
        dc = "report_date_as_yyyy_mm_dd"
        if dc in df.columns:
            df[dc] = pd.to_datetime(df[dc])
            df = df.set_index(dc).sort_index()
            df.index.name = "date"
        # Coerce known numeric columns
        for c in df.columns:
            if any(tok in c for tok in ("positions", "_all", "_old", "_other")):
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    return cache.load_or_fetch("cftc", f"{report}_{market}", fetch,
                                start=start_s, end=end_s)


def positioning_extreme_score(df: pd.DataFrame, lookback_weeks: int = 104) -> pd.Series:
    """Compute Managed Money net position as percentile of trailing 2-yr range.

    Returns a Series (0.0 to 1.0) where 0 = 2yr low, 1 = 2yr high.
    Useful to identify crowded long/short setups.
    """
    long_col  = next((c for c in df.columns if "m_money_positions_long_all" in c), None)
    short_col = next((c for c in df.columns if "m_money_positions_short_all" in c), None)
    if not long_col or not short_col:
        return pd.Series(dtype=float)
    net = df[long_col] - df[short_col]
    return net.rolling(lookback_weeks, min_periods=20).apply(
        lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) if x.max() != x.min() else 0.5,
        raw=False,
    )
