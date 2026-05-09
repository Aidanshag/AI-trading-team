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


# Common market name mappings.
# IMPORTANT: CFTC formats the market_and_exchange_names field with SPACES
# around the dash (e.g. "GOLD - COMMODITY EXCHANGE INC."). Do not omit them
# — exact match is required by Socrata's `=` operator. All names below have
# been verified via the live API.
MARKET_PATTERNS = {
    # Energies
    # NOTE: CFTC renamed the NYMEX CL feed in 2024-2025. The old
    # "CRUDE OIL, LIGHT SWEET" listing is dormant; the active
    # speculator-rich CL is now "WTI-PHYSICAL". Verified ~2.94M MM-long
    # cumulative through 2026; "WTI FINANCIAL" and "WTI 1ST LINE" both
    # have near-zero speculator activity by design.
    "crude_wti":    "WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
    "brent":        "BRENT LAST DAY - NEW YORK MERCANTILE EXCHANGE",
    "natgas":       "NAT GAS NYME - NEW YORK MERCANTILE EXCHANGE",
    "gasoline":     "GASOLINE RBOB - NEW YORK MERCANTILE EXCHANGE",
    "heating_oil":  "NY HARBOR ULSD - NEW YORK MERCANTILE EXCHANGE",
    "ethanol":      "ETHANOL - NEW YORK MERCANTILE EXCHANGE",
    # Metals
    "gold":         "GOLD - COMMODITY EXCHANGE INC.",
    "silver":       "SILVER - COMMODITY EXCHANGE INC.",
    "copper":       "COPPER- #1 - COMMODITY EXCHANGE INC.",
    "platinum":     "PLATINUM - NEW YORK MERCANTILE EXCHANGE",
    "palladium":    "PALLADIUM - NEW YORK MERCANTILE EXCHANGE",
    "aluminum":     "ALUMINUM - COMMODITY EXCHANGE INC.",
    # Grains & oilseeds (wheat split into HRW / HRSpring / SRW; ZW = SRW)
    "corn":         "CORN - CHICAGO BOARD OF TRADE",
    "soybeans":     "SOYBEANS - CHICAGO BOARD OF TRADE",
    "wheat":        "WHEAT-SRW - CHICAGO BOARD OF TRADE",
    "soy_oil":      "SOYBEAN OIL - CHICAGO BOARD OF TRADE",
    "soy_meal":     "SOYBEAN MEAL - CHICAGO BOARD OF TRADE",
    "oats":         "OATS - CHICAGO BOARD OF TRADE",
    "rough_rice":   "ROUGH RICE - CHICAGO BOARD OF TRADE",
    # Softs (most live on ICE)
    "coffee":       "COFFEE C - ICE FUTURES U.S.",
    "cotton":       "COTTON NO. 2 - ICE FUTURES U.S.",
    "sugar":        "SUGAR NO. 11 - ICE FUTURES U.S.",
    "cocoa":        "COCOA - ICE FUTURES U.S.",
    "orange_juice": "FRZN CONCENTRATED ORANGE JUICE - ICE FUTURES U.S.",
    "lumber":       "LUMBER - CHICAGO MERCANTILE EXCHANGE",
    # Livestock
    "live_cattle":  "LIVE CATTLE - CHICAGO MERCANTILE EXCHANGE",
    "feeder_cattle":"FEEDER CATTLE - CHICAGO MERCANTILE EXCHANGE",
    "lean_hogs":    "LEAN HOGS - CHICAGO MERCANTILE EXCHANGE",
    # Rates (TFF / financial)
    "2y_note":      "UST 2Y NOTE - CHICAGO BOARD OF TRADE",
    "5y_note":      "UST 5Y NOTE - CHICAGO BOARD OF TRADE",
    "10y_note":     "UST 10Y NOTE - CHICAGO BOARD OF TRADE",
    "30y_bond":     "UST BOND - CHICAGO BOARD OF TRADE",
    "ultra_bond":   "ULTRA UST BOND - CHICAGO BOARD OF TRADE",
    # FX (TFF / financial)
    "eur":          "EURO FX - CHICAGO MERCANTILE EXCHANGE",
    "gbp":          "BRITISH POUND - CHICAGO MERCANTILE EXCHANGE",
    "jpy":          "JAPANESE YEN - CHICAGO MERCANTILE EXCHANGE",
    "aud":          "AUSTRALIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "cad":          "CANADIAN DOLLAR - CHICAGO MERCANTILE EXCHANGE",
    "chf":          "SWISS FRANC - CHICAGO MERCANTILE EXCHANGE",
    # Index (TFF / financial)
    "sp500":        "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
    "nasdaq":       "NASDAQ-100 Consolidated - CHICAGO MERCANTILE EXCHANGE",
    "russell":      "RUSSELL E-MINI - CHICAGO MERCANTILE EXCHANGE",
    "djia":         "DJIA Consolidated - CHICAGO BOARD OF TRADE",
}


# Maps trading symbol → (market_key, report_type).
# Micros (MES, MNQ, MCL, MGC, M2K, MYM, M6E, M6B, SIL, QG) inherit their
# parent contract's positioning data — CFTC doesn't publish separate COT
# for micros. Symbols absent from this map have no COT proxy.
SYMBOL_TO_COT = {
    # Index (financial report)
    "ES":  ("sp500",   "financial"),
    "MES": ("sp500",   "financial"),
    "NQ":  ("nasdaq",  "financial"),
    "MNQ": ("nasdaq",  "financial"),
    "RTY": ("russell", "financial"),
    "M2K": ("russell", "financial"),
    "YM":  ("djia",    "financial"),
    "MYM": ("djia",    "financial"),
    # Energies (disaggregated)
    "CL":  ("crude_wti",  "disaggregated"),
    "MCL": ("crude_wti",  "disaggregated"),
    "BZ":  ("brent",      "disaggregated"),
    "NG":  ("natgas",     "disaggregated"),
    "QG":  ("natgas",     "disaggregated"),
    "RB":  ("gasoline",   "disaggregated"),
    "HO":  ("heating_oil","disaggregated"),
    "EH":  ("ethanol",    "disaggregated"),
    # Metals (disaggregated)
    "GC":  ("gold",      "disaggregated"),
    "MGC": ("gold",      "disaggregated"),
    "SI":  ("silver",    "disaggregated"),
    "SIL": ("silver",    "disaggregated"),
    "HG":  ("copper",    "disaggregated"),
    "PL":  ("platinum",  "disaggregated"),
    "PA":  ("palladium", "disaggregated"),
    "ALI": ("aluminum",  "disaggregated"),
    # Grains (disaggregated)
    "ZC":  ("corn",       "disaggregated"),
    "ZS":  ("soybeans",   "disaggregated"),
    "ZW":  ("wheat",      "disaggregated"),
    "ZL":  ("soy_oil",    "disaggregated"),
    "ZM":  ("soy_meal",   "disaggregated"),
    "ZO":  ("oats",       "disaggregated"),
    "ZR":  ("rough_rice", "disaggregated"),
    # Softs (disaggregated)
    "KC":  ("coffee",       "disaggregated"),
    "CT":  ("cotton",       "disaggregated"),
    "SB":  ("sugar",        "disaggregated"),
    "CC":  ("cocoa",        "disaggregated"),
    "OJ":  ("orange_juice", "disaggregated"),
    "LBR": ("lumber",       "disaggregated"),
    # Livestock (disaggregated)
    "LE":  ("live_cattle",   "disaggregated"),
    "GF":  ("feeder_cattle", "disaggregated"),
    "HE":  ("lean_hogs",     "disaggregated"),
    # Rates (financial)
    "ZT":  ("2y_note",    "financial"),
    "ZF":  ("5y_note",    "financial"),
    "ZN":  ("10y_note",   "financial"),
    "ZB":  ("30y_bond",   "financial"),
    "UB":  ("ultra_bond", "financial"),
    # FX (financial)
    "6E":  ("eur", "financial"),
    "M6E": ("eur", "financial"),
    "6B":  ("gbp", "financial"),
    "M6B": ("gbp", "financial"),
    "6J":  ("jpy", "financial"),
    "6A":  ("aud", "financial"),
    "6C":  ("cad", "financial"),
    "6S":  ("chf", "financial"),
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


def commitments_for_symbol(
    symbol: str,
    start: str | date,
    end: str | date,
) -> pd.DataFrame:
    """Convenience: pull COT keyed by trading symbol (CL, ZC, ES, …).
    Resolves the right market name + report type from SYMBOL_TO_COT.
    Returns empty DataFrame if symbol has no COT proxy.
    """
    if symbol not in SYMBOL_TO_COT:
        return pd.DataFrame()
    market_key, report = SYMBOL_TO_COT[symbol]
    return commitments(market_key, start, end, report=report)


# Column name candidates per report type. Disaggregated tracks Managed
# Money; financial (TFF) tracks Leveraged Funds. Both are the speculative
# pool whose positioning extremes drive contrarian setups.
SPECULATOR_COLS = {
    "disaggregated": ("m_money_positions_long_all", "m_money_positions_short_all"),
    "financial":     ("lev_money_positions_long",   "lev_money_positions_short"),
    "legacy":        ("noncomm_positions_long_all", "noncomm_positions_short_all"),
}


def speculator_net(df: pd.DataFrame, report: str) -> pd.Series:
    """Net speculator position (long - short) for the given report type.
    Returns empty Series if columns absent.
    """
    long_key, short_key = SPECULATOR_COLS.get(report, (None, None))
    if not long_key:
        return pd.Series(dtype=float)
    long_col  = next((c for c in df.columns if long_key in c), None)
    short_col = next((c for c in df.columns if short_key in c), None)
    if not long_col or not short_col:
        return pd.Series(dtype=float)
    return df[long_col].fillna(0) - df[short_col].fillna(0)


def positioning_extreme_score(
    df: pd.DataFrame,
    lookback_weeks: int = 104,
    report: str = "disaggregated",
) -> pd.Series:
    """Compute speculator net position as percentile of trailing range.

    Returns a Series (0.0 to 1.0) where 0 = N-week low, 1 = N-week high.
    >0.90 → crowded long → fade-risk on rallies.
    <0.10 → crowded short → fade-risk on declines.
    """
    net = speculator_net(df, report)
    if net.empty:
        return pd.Series(dtype=float)
    return net.rolling(lookback_weeks, min_periods=20).apply(
        lambda x: (x.iloc[-1] - x.min()) / (x.max() - x.min()) if x.max() != x.min() else 0.5,
        raw=False,
    )
