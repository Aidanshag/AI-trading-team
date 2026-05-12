"""Replay a shadow signal through production exit logic.

WHY:
The theoretical resolver (`scripts/resolve_shadow_trades._evaluate_path`)
walks bars and tags target_hit / stop_hit using the signal's
target_price and stop_price. That measures strategy edge under an
idealized "place target + stop bracket" execution model.

Production today operates differently:
  * `SKIP_TARGET_LEG = True` — no target order is placed at the broker
    (workaround for the 2026-05-11 broker target-fill anomaly). So a
    runner can never close at target_hit naturally — only the stop, the
    trailing-profit-lock tiers, the loss hard cap, or the 3:10 PM CT
    hard-flatten can close it.
  * Trailing-profit-lock (`tools/profit_protect.TRAILING_PROFIT_TIERS`)
    tracks the position's peak unrealized $ and closes if it retraces
    past a tier's floor. This is what actually realizes most winners.
  * `LOSS_TIER_HARD_CAP_USD = 150` — second-line stop in case the
    broker stop doesn't fire.
  * Hard-flatten clock — every intraday position closes by 3:10 PM CT
    (or earlier on abbreviated holidays).

This module simulates that ladder against shadow signal bars, so we get
an apples-to-apples "what would production have realized" number
(`exec_mirror_pnl_r`) alongside the theoretical pnl_r.

Built 2026-05-12 in response to the user's request to make shadow data
match production reality.
"""
from __future__ import annotations

from datetime import datetime, time as dtime, timedelta, timezone
from typing import Optional

from tools.profit_protect import (
    TRAILING_PROFIT_TIERS,
    LOSS_TIER_HARD_CAP_USD,
    GAIN_TIER_HARD_CAP_USD,
    decide,
    _TICK_ECONOMICS,
)

# How long to walk before time-stopping (mirrors theoretical resolver default).
DEFAULT_TIMEOUT_HOURS = 8

# Hard-flatten time CT (mirrors tools/hard_flatten_clock.DEADLINE_TIME_CT).
HARD_FLATTEN_TIME_CT = dtime(15, 10)


def _bar_ts(b: dict) -> Optional[datetime]:
    ts = b.get("t") or b.get("ts") or b.get("time")
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
    if isinstance(ts, datetime):
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    return None


def _is_past_hard_flatten(ts_utc: datetime) -> bool:
    """True if ts is at or after today's 3:10 PM CT. Uses the holiday
    schedule if available."""
    try:
        from zoneinfo import ZoneInfo
        ts_ct = ts_utc.astimezone(ZoneInfo("America/Chicago"))
    except Exception:
        from datetime import timedelta as _td
        # Rough fallback: UTC-5
        ts_ct = ts_utc - _td(hours=5)
    try:
        from tools.holiday_schedule import hard_flatten_time_ct
        deadline = hard_flatten_time_ct(ts_ct.date())
    except Exception:
        deadline = HARD_FLATTEN_TIME_CT
    return ts_ct.time() >= deadline and ts_ct.weekday() < 5


def evaluate_exec_mirror(
    bars: list[dict],
    *,
    symbol: str,
    side: str,
    entry: float,
    stop: float,
    risk_usd: Optional[float] = None,
    timeout_hours: int = DEFAULT_TIMEOUT_HOURS,
    tiers: tuple[tuple[float, float], ...] = TRAILING_PROFIT_TIERS,
    loss_cap_usd: float = LOSS_TIER_HARD_CAP_USD,
    gain_cap_usd: Optional[float] = GAIN_TIER_HARD_CAP_USD,
    qty: int = 1,
) -> tuple[str, float, str]:
    """Replay bars under production exit logic.

    Returns (outcome, exec_mirror_pnl_r, notes).

    Outcome codes:
      stop_hit        — broker stop hit first
      profit_lock     — trailing-profit-lock tier triggered (the typical winner path)
      loss_cap        — LOSS_TIER_HARD_CAP_USD floor (belt-and-suspenders)
      gain_cap        — GAIN_TIER_HARD_CAP_USD ceiling (if set)
      hard_flatten    — 3:10 PM CT enforcement
      time_stopped    — ran the timeout without any exit; mark-to-market
      no_fill         — entry never tagged within fill window
      invalidated     — missing bars / risk_usd / tick economics
    """
    side = (side or "").lower()
    if not bars or side not in ("long", "short"):
        return "invalidated", 0.0, "missing bars or invalid side"
    if entry <= 0 or stop <= 0:
        return "invalidated", 0.0, "missing entry/stop"

    risk_per_unit = abs(entry - stop)
    if risk_per_unit <= 0:
        return "invalidated", 0.0, "zero risk distance"

    tick_size, tick_value = _TICK_ECONOMICS.get(symbol, (0.0, 0.0))
    if tick_size <= 0 or tick_value <= 0:
        return "invalidated", 0.0, f"no tick economics for {symbol}"

    # Risk in USD (R-denominator). Prefer the row's recorded risk_usd; if
    # missing, compute from tick economics + qty.
    if risk_usd is None or risk_usd <= 0:
        risk_usd = (risk_per_unit / tick_size) * tick_value * qty
    if risk_usd <= 0:
        return "invalidated", 0.0, "could not compute risk_usd"

    # Pre-parse bars: keep only those after entry-fill window.
    parsed: list[tuple[Optional[datetime], float, float, float]] = []
    for b in bars:
        try:
            ts = _bar_ts(b)
            hi = float(b.get("h") or b.get("high"))
            lo = float(b.get("l") or b.get("low"))
            cl = float(b.get("c") or b.get("close"))
            parsed.append((ts, hi, lo, cl))
        except (TypeError, ValueError):
            continue
    if not parsed:
        return "invalidated", 0.0, "no parseable bars"

    # Sort by ts (some feeds return newest-first)
    parsed.sort(key=lambda p: p[0] if p[0] else datetime.min.replace(tzinfo=timezone.utc))

    # Find entry-fill: first bar that tags entry price.
    entry_filled_idx: Optional[int] = None
    entry_ts: Optional[datetime] = None
    for i, (ts, hi, lo, cl) in enumerate(parsed):
        if lo <= entry <= hi:
            entry_filled_idx = i
            entry_ts = ts
            break
    if entry_filled_idx is None:
        return "no_fill", 0.0, "entry not tagged in shadow window"

    # Walk forward from entry. Track peak unrealized $.
    peak_unrealized = 0.0
    timeout_ts: Optional[datetime] = None
    if entry_ts is not None:
        timeout_ts = entry_ts + timedelta(hours=timeout_hours)

    def _to_r(usd: float) -> float:
        return usd / float(risk_usd)

    for i in range(entry_filled_idx, len(parsed)):
        ts, hi, lo, cl = parsed[i]

        # 1) Stop-hit check (matches broker stop logic — lo for long, hi for short).
        #    If hit on the entry bar, conservative same-bar tie: assume stop fires
        #    before tier checks.
        if side == "long" and lo <= stop:
            return "stop_hit", -1.0, f"stop @ {stop} bar={ts.isoformat() if ts else '?'}"
        if side == "short" and hi >= stop:
            return "stop_hit", -1.0, f"stop @ {stop} bar={ts.isoformat() if ts else '?'}"

        # 2) Hard-flatten clock: if past 3:10 PM CT, close at this bar's close.
        if ts is not None and _is_past_hard_flatten(ts):
            move = (cl - entry) if side == "long" else (entry - cl)
            usd = (move / tick_size) * tick_value * qty
            return "hard_flatten", _to_r(usd), (
                f"3:10 PM CT enforcement, close=${cl} pnl=${usd:+.2f}")

        # 3) Tier evaluation against this bar's extreme (high for long, low for short).
        #    Peak is the most favorable point yet reached. We approximate by
        #    using the bar's most favorable extreme — which is what production
        #    would have seen as the position's high-water.
        favorable = hi if side == "long" else lo
        move_fav = (favorable - entry) if side == "long" else (entry - favorable)
        fav_usd = (move_fav / tick_size) * tick_value * qty
        if fav_usd > peak_unrealized:
            peak_unrealized = fav_usd

        # Decide on this bar's UNFAVORABLE extreme (low for long, high for short).
        # If the close-or-retrace within this bar fell below an active floor,
        # production would have market-closed mid-bar at that floor (or worse).
        unfavorable = lo if side == "long" else hi
        move_unfav = (unfavorable - entry) if side == "long" else (entry - unfavorable)
        unfav_usd = (move_unfav / tick_size) * tick_value * qty

        should_close, reason = decide(unrealized=unfav_usd, prev_peak=peak_unrealized,
                                       tiers=tiers, gain_cap=gain_cap_usd,
                                       loss_cap=loss_cap_usd)
        if should_close:
            # The realized exit isn't necessarily at unfav_usd — for a trailing
            # lock close, the bot fires at the floor. Estimate exit usd:
            if "trailing_lock" in reason:
                # Pull floor out of the reason string. Cheap parse; we know the
                # decide() format.
                import re as _re
                m = _re.search(r"floor \$(-?\d+(?:\.\d+)?)", reason)
                exit_usd = float(m.group(1)) if m else unfav_usd
            elif "loss_hard_cap" in reason:
                exit_usd = -float(loss_cap_usd)
            elif "hard_cap" in reason:
                exit_usd = float(gain_cap_usd) if gain_cap_usd else unfav_usd
            else:
                exit_usd = unfav_usd

            outcome = ("profit_lock" if "trailing_lock" in reason
                        else "loss_cap" if "loss_hard_cap" in reason
                        else "gain_cap" if "hard_cap" in reason
                        else "exit_unknown")
            return outcome, _to_r(exit_usd), reason[:160]

        # 4) Timeout
        if timeout_ts is not None and ts is not None and ts >= timeout_ts:
            move = (cl - entry) if side == "long" else (entry - cl)
            usd = (move / tick_size) * tick_value * qty
            return "time_stopped", _to_r(usd), (
                f"timeout {timeout_hours}h, close=${cl} pnl=${usd:+.2f}")

    # Ran out of bars without a clean exit. Mark-to-market against last close.
    _, _, _, last_close = parsed[-1]
    move = (last_close - entry) if side == "long" else (entry - last_close)
    usd = (move / tick_size) * tick_value * qty
    return "time_stopped", _to_r(usd), f"end-of-bars mtm @ {last_close} pnl=${usd:+.2f}"
