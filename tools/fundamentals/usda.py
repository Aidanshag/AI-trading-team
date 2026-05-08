"""USDA data loaders — NASS QuickStats + WASDE archives.

NASS: free API key from https://quickstats.nass.usda.gov/api
WASDE: monthly PDF + embedded tables; we grab the CSV extracts from USDA.

NASS gives: crop progress, crop production, grain stocks, cattle on feed.
WASDE gives: monthly supply/demand/ending-stocks estimates.

NOTE: WASDE CSVs are only downloadable for recent releases. Historical
archives exist but require some scraping. For the fund's purposes, start
with NASS (stable API) and defer WASDE CSV parsing.
"""

from __future__ import annotations

import os
from datetime import date

import httpx
import pandas as pd

from . import cache

NASS_BASE = "https://quickstats.nass.usda.gov/api/api_GET/"


def _require_nass_key() -> str:
    key = os.environ.get("USDA_NASS_KEY")
    if not key:
        raise RuntimeError(
            "USDA_NASS_KEY not set. Register free at "
            "https://quickstats.nass.usda.gov/api and add to .env."
        )
    return key


def nass_query(
    commodity: str,
    statistic: str,
    year_start: int,
    year_end: int,
    agg_level: str = "NATIONAL",
    extra: dict | None = None,
) -> pd.DataFrame:
    """Low-level NASS query wrapper.

    Args:
        commodity: e.g. 'CORN', 'SOYBEANS', 'WHEAT', 'CATTLE'.
        statistic: short-desc search — NASS matches substrings.
        year_start / year_end: inclusive year range.
        agg_level: 'NATIONAL' | 'STATE' | 'COUNTY'.
        extra: additional query params.
    """
    key = _require_nass_key()

    def fetch() -> pd.DataFrame:
        params = {
            "key": key,
            "commodity_desc": commodity,
            "short_desc": statistic,
            "agg_level_desc": agg_level,
            "format": "JSON",
            "year__GE": str(year_start),
            "year__LE": str(year_end),
        }
        if extra:
            params.update(extra)
        r = httpx.get(NASS_BASE, params=params, timeout=60.0)
        r.raise_for_status()
        rows = r.json().get("data", [])
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        # Build a date index from week_ending or year+week
        if "week_ending" in df.columns:
            df["date"] = pd.to_datetime(df["week_ending"], errors="coerce")
        elif "year" in df.columns and "reference_period_desc" in df.columns:
            df["date"] = pd.to_datetime(df["year"].astype(str) + "-01-01", errors="coerce")
        if "Value" in df.columns:
            df["Value"] = pd.to_numeric(
                df["Value"].astype(str).str.replace(",", "", regex=False),
                errors="coerce",
            )
        if "date" in df.columns:
            df = df.set_index("date").sort_index()
        return df

    return cache.load_or_fetch(
        "usda_nass",
        f"{commodity}_{statistic}_{year_start}_{year_end}",
        fetch,
        commodity=commodity,
        statistic=statistic,
        agg_level=agg_level,
    )


# Convenience wrappers for the fund's recurring needs
def crop_progress(commodity: str, year_start: int, year_end: int) -> pd.DataFrame:
    """Weekly crop progress (planting, silking, dough, mature, harvested pct)."""
    return nass_query(
        commodity=commodity.upper(),
        statistic=f"{commodity.upper()} - PROGRESS",
        year_start=year_start,
        year_end=year_end,
    )


def cattle_on_feed(year_start: int, year_end: int) -> pd.DataFrame:
    """Monthly Cattle on Feed — on-feed, placements, marketings."""
    return nass_query(
        commodity="CATTLE",
        statistic="CATTLE, ON FEED",
        year_start=year_start,
        year_end=year_end,
    )


def cold_storage(product: str, year_start: int, year_end: int) -> pd.DataFrame:
    """Monthly Cold Storage inventories for a given protein (e.g., 'BEEF', 'PORK')."""
    return nass_query(
        commodity=product.upper(),
        statistic=f"{product.upper()} - COLD STORAGE",
        year_start=year_start,
        year_end=year_end,
    )


# WASDE wrapper — stub. WASDE archive CSVs live at USDA.gov under a
# predictable URL pattern but require PDF parsing for older vintages.
def wasde_latest_url() -> str:
    """Latest WASDE release URL. Agents can fetch + parse manually for now."""
    return "https://www.usda.gov/sites/default/files/documents/latest.pdf"  # placeholder


# TODO: build a WASDE CSV parser once the MCP tool is wired and we've
# verified the actual release-file naming convention for recent releases.
