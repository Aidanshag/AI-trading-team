"""Fundamental-data loaders: FRED (macro), EIA (energy), USDA (ags), CFTC (positioning).

All loaders return pandas DataFrames with a DatetimeIndex (tz-naive).
All loaders cache responses locally under `data/cache/fundamentals/`.

Usage:

    from tools.fundamentals import fred, eia, cftc, usda

    tips = fred.load_series("DFII10", "2020-01-01", "2026-01-01")
    crude_stocks = eia.crude_stocks("2020-01-01", "2026-01-01")
    wheat_cot = cftc.commitments("wheat", "2020-01-01", "2026-01-01")

API keys (free, optional):
    FRED_API_KEY       — https://fred.stlouisfed.org/docs/api/api_key.html
    EIA_API_KEY        — https://www.eia.gov/opendata/register.php  (required)
    USDA_NASS_KEY      — https://quickstats.nass.usda.gov/api      (required)
    CFTC               — no key needed; direct CSV downloads
"""
from . import cache, cftc, eia, fred, usda

__all__ = ["cache", "cftc", "eia", "fred", "usda"]
