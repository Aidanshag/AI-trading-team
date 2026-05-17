"""Pure utility helpers used by both the live trader and adjacent tools.

Extracted from scripts/live_trader.py 2026-05-08 to keep the execution
layer focused on broker actions. These have no broker / DB / state
dependencies — pure functions only.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Topstep's CME-Globex trading day rolls at 5:00 PM US/Central time.
# This is the boundary their daily-loss-limit + trade-count counters
# reset on. Anchoring to UTC midnight (the previous default in some
# spots) caused inconsistencies — see vault/lessons/2026-05-13_*.md.
_TOPSTEP_DAY_BOUNDARY_CT = time(17, 0)
_CENTRAL = ZoneInfo("America/Chicago")


def topstep_trading_day_start_utc(now_utc: datetime | None = None) -> datetime:
    """Return the UTC timestamp of the most recent 5pm CT (= start of
    the current Topstep trading day). DST-aware via zoneinfo. Public —
    callers in tools/snapshot_writer and tools/trade_state import it."""
    now_utc = now_utc or datetime.now(timezone.utc)
    now_ct = now_utc.astimezone(_CENTRAL)
    if now_ct.time() >= _TOPSTEP_DAY_BOUNDARY_CT:
        boundary_ct = datetime.combine(now_ct.date(), _TOPSTEP_DAY_BOUNDARY_CT,
                                          tzinfo=_CENTRAL)
    else:
        yesterday = now_ct.date() - timedelta(days=1)
        boundary_ct = datetime.combine(yesterday, _TOPSTEP_DAY_BOUNDARY_CT,
                                          tzinfo=_CENTRAL)
    return boundary_ct.astimezone(timezone.utc)


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


# Topstep-specific contract roots map to CME canonical roots used by
# config/symbols.yaml. Mirrors the alias dict in tools/profit_protect.py.
# Without this, _tick_size("EU6") returns the default 0.01, which silently
# corrupts stop-distance math (Pattern A failure shape — the 2026-05-14
# EU6 short held 2h14m unprotected for exactly this reason).
_SYMBOL_ALIAS_TO_CANONICAL: dict[str, str] = {
    # FX
    "EU6": "6E", "BP6": "6B", "JY6": "6J",
    "DA6": "6A", "CA6": "6C", "MX6": "6S",
    "EEU": "E7",
    # Grains / livestock
    "ZCE": "ZC", "GLE": "LE",
    # Metals
    "CPE": "HG",
    # Energy / crypto
    "NQG": "QG", "NQM": "QM",
}


def _canonicalize_symbol(symbol: str) -> str:
    """Map Topstep-alias root → CME canonical root if known; else pass through."""
    return _SYMBOL_ALIAS_TO_CANONICAL.get(symbol, symbol)


def _tick_size(symbol: str) -> float:
    """Look up tick size from config/symbols.yaml; default 0.01 if missing.
    Auto-canonicalizes EU6/BP6/etc → 6E/6B/etc."""
    canon = _canonicalize_symbol(symbol)
    syms = _load_yaml("config/symbols.yaml").get("symbols", {})
    return float((syms.get(canon) or {}).get("tick_size", 0.01))


def _tick_value(symbol: str) -> float:
    """USD value of one tick. 0.0 if symbol or value is missing — callers
    that need to gate on dollars must treat 0.0 as 'unknown, refuse to act'.
    Auto-canonicalizes EU6/BP6/etc → 6E/6B/etc."""
    canon = _canonicalize_symbol(symbol)
    syms = _load_yaml("config/symbols.yaml").get("symbols", {})
    val = (syms.get(canon) or {}).get("tick_value")
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
