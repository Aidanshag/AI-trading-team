"""DB-backed trade-state queries — extracted from scripts/live_trader.py
2026-05-08 (continuous trim).

These query the orders table for cooldown enforcement and daily trade
counting. Pure DB reads; no broker / state mutation.
"""
from __future__ import annotations

from datetime import timedelta

from state.db import get_db
from tools.trader_utils import _now_utc, topstep_trading_day_start_utc


def recent_thesis_for(symbol: str, minutes: int) -> bool:
    """True if this symbol has fired within the cooldown window.

    Excludes stop/target legs (only counts entry orders).
    """
    cutoff = (_now_utc() - timedelta(minutes=minutes)).isoformat(timespec="seconds")
    db = get_db()
    row = db.connect().execute(
        "SELECT 1 FROM orders WHERE symbol=? AND agent='live_trader' "
        "AND client_order_id NOT LIKE '%_stop' AND client_order_id NOT LIKE '%_target' "
        "AND ts_proposed >= ? LIMIT 1",
        (symbol, cutoff),
    ).fetchone()
    return row is not None


def todays_trade_count() -> int:
    """Count of entry orders placed in the current TOPSTEP trading day
    (5pm CT to 5pm CT) by the live_trader.

    2026-05-14 fix: was counting from UTC midnight, which is 3-4h after
    Topstep's trading-day reset (5pm CT = 22 UTC EDT). Caused inconsistency
    with the snapshot anchor (which already uses Topstep day) and locked
    the trader out for 3-4h every night.

    Excludes stop/target legs (only counts entry orders).
    """
    boundary = topstep_trading_day_start_utc()
    cutoff_iso = boundary.strftime("%Y-%m-%dT%H:%M:%S")
    db = get_db()
    row = db.connect().execute(
        "SELECT COUNT(*) FROM orders WHERE agent='live_trader' "
        "AND ts_proposed >= ? "
        "AND client_order_id NOT LIKE '%_stop' AND client_order_id NOT LIKE '%_target'",
        (cutoff_iso,),
    ).fetchone()
    return int(row[0]) if row else 0
