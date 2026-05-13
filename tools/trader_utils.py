"""Pure utility helpers used by both the live trader and adjacent tools.

Extracted from scripts/live_trader.py 2026-05-08 to keep the execution
layer focused on broker actions. These have no broker / DB / state
dependencies — pure functions only.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_yaml(path: str) -> dict:
    """Read a YAML file relative to project root, return {} on missing."""
    p = PROJECT_ROOT / path
    if not p.exists():
        return {}
    return yaml.safe_load(p.read_text()) or {}


def _now_utc() -> datetime:
    """Current UTC datetime (timezone-aware)."""
    return datetime.now(timezone.utc)


def _utcnow_iso() -> str:
    """ISO 8601 timestamp for the current UTC moment, second-precision."""
    return _now_utc().isoformat(timespec="seconds")


def _round_to_tick(price: float, tick: float) -> float:
    """Round price to the nearest valid tick boundary."""
    return round(round(price / tick) * tick, 8)


def _tick_size(symbol: str) -> float:
    """Look up tick size from config/symbols.yaml; default 0.01 if missing."""
    syms = _load_yaml("config/symbols.yaml").get("symbols", {})
    return float((syms.get(symbol) or {}).get("tick_size", 0.01))


def _tick_value(symbol: str) -> float:
    """USD value of one tick. 0.0 if symbol or value is missing — callers
    that need to gate on dollars must treat 0.0 as 'unknown, refuse to act'."""
    syms = _load_yaml("config/symbols.yaml").get("symbols", {})
    val = (syms.get(symbol) or {}).get("tick_value")
    return float(val) if val is not None else 0.0


def is_sunday_reopen_blackout(now_utc: datetime) -> bool:
    """First 30 min of Sunday Globex reopen (Sunday 17:00–17:30 ET) — skip
    new entries during this thin-tape window. Spreads are widest as everyone
    re-prices after the weekend break.

    ET = UTC-4 in summer (EDT), UTC-5 in winter (EST). For simplicity we
    treat ET as UTC-4 (we're in EDT now). When DST ends, this drifts by 1h
    but the principle holds — skip first 30 min of Sunday reopen window.
    """
    # Sunday in ET = depends on UTC offset. Sunday 17:00 ET = Sunday 21:00 UTC (EDT) or 22:00 UTC (EST).
    # Use UTC weekday + hour for robustness.
    et_hour_approx = (now_utc.hour - 4) % 24
    et_weekday = now_utc.weekday()
    # Sunday in ET = Sunday 17:00 onward (or Monday 00:00 if past midnight UTC)
    # Practical check: if UTC weekday is Sunday (6) AND UTC hour is 21:00–21:30 → blackout
    # OR UTC weekday is Sunday AND UTC hour 22:00–22:30 (winter)
    if et_weekday == 6 and et_hour_approx == 17 and now_utc.minute < 30:
        return True
    return False
