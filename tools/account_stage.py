"""Account-stage configuration helpers.

Reads `config/account_stage.yaml` to determine which Combine-specific
safety rules currently apply. Defaults fail-safe to `combine` (most
restrictive) if the file is missing or unreadable.

2026-05-12: added so combine-only safeties (daily profit cap to manage
the 50% consistency rule) auto-disable on XFA/Live transition without
code changes.
"""
from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_FILE = _PROJECT_ROOT / "config" / "account_stage.yaml"


def _load() -> dict:
    """Read the stage config, returning defaults on any failure."""
    defaults = {
        "stage": "combine",
        "combine_daily_profit_cap_usd": 600.0,
        "daily_window_reset_hour_ct": 17,
    }
    if not _CONFIG_FILE.exists():
        return defaults
    try:
        import yaml
    except ImportError:
        return defaults
    try:
        data = yaml.safe_load(_CONFIG_FILE.read_text(encoding="utf-8")) or {}
    except Exception:
        return defaults
    out = dict(defaults)
    out.update({k: v for k, v in data.items() if v is not None})
    return out


def current_stage() -> str:
    """Return 'combine' | 'xfa' | 'live'. Defaults to 'combine' (safest)."""
    stage = str(_load().get("stage", "combine")).lower().strip()
    if stage not in ("combine", "xfa", "live"):
        return "combine"
    return stage


def is_combine() -> bool:
    return current_stage() == "combine"


def combine_daily_profit_cap_usd() -> float | None:
    """Daily profit cap in USD when in combine stage; None when stage != combine
    OR when explicitly disabled (cap = 0 / null in config)."""
    if not is_combine():
        return None
    raw = _load().get("combine_daily_profit_cap_usd")
    if raw is None or raw == 0:
        return None
    try:
        v = float(raw)
        return v if v > 0 else None
    except (TypeError, ValueError):
        return None


def daily_window_reset_hour_ct() -> int:
    """Hour (0-23) in CT at which the daily P&L window resets.
    Defaults to 17 (5 PM CT, matches Topstep DLL reset)."""
    try:
        return int(_load().get("daily_window_reset_hour_ct", 17))
    except (TypeError, ValueError):
        return 17
