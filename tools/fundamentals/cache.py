"""Shared disk cache for fundamental-data responses.

Design: one parquet file per (source, series_id, date-range) key. Avoids
re-hitting rate-limited public APIs during backtests. TTL-based
invalidation keeps refreshes predictable.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Callable

import pandas as pd

CACHE_DIR = Path("data/cache/fundamentals")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# Default TTL: 1 day for macro/weekly data; fundamentals don't change
# intraday. Override per-call if you need fresher numbers.
DEFAULT_TTL_SECONDS = 24 * 3600


def _key(source: str, series: str, **params) -> Path:
    blob = json.dumps({"src": source, "series": series, **params}, sort_keys=True)
    h = hashlib.sha256(blob.encode()).hexdigest()[:16]
    safe_series = "".join(c if c.isalnum() or c in "._-" else "_" for c in series)
    return CACHE_DIR / f"{source}_{safe_series}_{h}.parquet"


def load_or_fetch(
    source: str,
    series: str,
    fetch_fn: Callable[[], pd.DataFrame],
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
    **params,
) -> pd.DataFrame:
    """Return cached DataFrame if fresh; else call fetch_fn() and cache."""
    path = _key(source, series, **params)
    if path.exists():
        age = time.time() - path.stat().st_mtime
        if age < ttl_seconds:
            return pd.read_parquet(path)

    df = fetch_fn()
    if df is not None and not df.empty:
        df.to_parquet(path)
    return df


def clear(source: str | None = None) -> int:
    """Remove cached files. If `source` is set, only remove that source's files."""
    n = 0
    for p in CACHE_DIR.glob("*.parquet"):
        if source is None or p.name.startswith(f"{source}_"):
            p.unlink()
            n += 1
    return n
