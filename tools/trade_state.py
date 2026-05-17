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


def _last_trade_for_symbol(symbol: str) -> dict | None:
    """Return the most recent completed entry+close pair for `symbol`, with
    the metadata `tools.cooldown_policy` needs to classify the outcome.

    Returns None if no recent trade found, or if the closing decision
    isn't readable. This is best-effort — used for shadow A/B logging,
    not for any live gating decisions.

    Returned dict shape:
      {
        "realized_r": float | None,  # r-multiple from the last close
        "exit_reason": str | None,   # 'target_hit' | 'stop_hit' | ...
        "minutes_since": float,      # min since the close
      }
    """
    db = get_db()
    cur = db.connect().cursor()
    # Find the most recent profit_lock close decision for this symbol
    row = cur.execute(
        "SELECT ts, rationale FROM decisions "
        "WHERE symbol=? AND agent='profit_lock' AND kind='close' "
        "ORDER BY ts DESC LIMIT 1",
        (symbol,),
    ).fetchone()
    if not row:
        return None
    ts_str, rationale = row
    if not rationale:
        return None
    # Parse "reason=X | peak=$Y | realized=$Z | peak_pct_captured=W | ..."
    parts = {}
    for token in str(rationale).split("|"):
        token = token.strip()
        if "=" in token:
            k, v = token.split("=", 1)
            parts[k.strip()] = v.strip()
    exit_reason = parts.get("reason", "").split(":")[0].strip() or None
    realized = parts.get("realized")
    realized_dollars = None
    if realized:
        try:
            realized_dollars = float(realized.lstrip("$+").rstrip(","))
        except Exception:
            pass
    # Convert dollar P&L → R-multiple. Need entry risk_usd from orders
    # — best-effort: look up the matching filled entry order
    risk_usd = None
    entry = cur.execute(
        "SELECT limit_price, stop_price FROM orders "
        "WHERE symbol=? AND agent='live_trader' AND status='filled' "
        "AND client_order_id NOT LIKE '%_stop' AND client_order_id NOT LIKE '%_target' "
        "ORDER BY ts_filled DESC LIMIT 1",
        (symbol,),
    ).fetchone()
    realized_r = None
    if entry and entry[0] and entry[1] and realized_dollars is not None:
        try:
            # Rough R = realized / (|price - stop| × tick_value)
            from tools.trader_utils import _tick_size, _tick_value
            tsz = _tick_size(symbol)
            tval = _tick_value(symbol)
            if tsz > 0 and tval > 0:
                stop_distance = abs(float(entry[0]) - float(entry[1]))
                risk_usd = (stop_distance / tsz) * tval
                if risk_usd > 0:
                    realized_r = realized_dollars / risk_usd
        except Exception:
            pass
    minutes_since = 0.0
    try:
        from datetime import datetime, timezone
        ts_dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        minutes_since = (datetime.now(tz=timezone.utc) - ts_dt).total_seconds() / 60.0
    except Exception:
        pass
    return {
        "realized_r": realized_r,
        "exit_reason": exit_reason,
        "minutes_since": minutes_since,
    }


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
