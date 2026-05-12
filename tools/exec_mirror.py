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

FRICTION (v2 — added 2026-05-12):
The simulator now subtracts realistic execution costs from every
outcome:
  * Round-trip slippage = 1.5 ticks (entry + normal exit, 0.75 each side)
  * Fees per `tools/shadow_realism.FEES_PER_ROUND_TRIP`
  * Additional stop-slippage = 1.0 tick when `outcome=stop_hit`
    (broker stops slip past trigger price in fast tape)
This makes `exec_mirror_pnl_r` the closest we can get to what
production would actually realize on a fill-for-fill basis. The two
slippage constants are conservative — biased toward under-promising.

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
from tools.shadow_realism import (
    slippage_cost_usd,
    fees_round_trip_usd,
    DEFAULT_SLIPPAGE_TICKS_ROUND_TRIP,
)

# How long to walk before time-stopping (mirrors theoretical resolver default).
DEFAULT_TIMEOUT_HOURS = 8

# Hard-flatten time CT (mirrors tools/hard_flatten_clock.DEADLINE_TIME_CT).
HARD_FLATTEN_TIME_CT = dtime(15, 10)

# Default extra slippage when broker stop fires. Stops convert to market on
# touch and tend to slip past trigger price by 1-2 ticks in fast tape.
# Conservative default = 1.0 tick.
DEFAULT_STOP_SLIPPAGE_TICKS: float = 1.0


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
        ts_ct = ts_utc - _td(hours=5)
    try:
        from tools.holiday_schedule import hard_flatten_time_ct
        deadline = hard_flatten_time_ct(ts_ct.date())
    except Exception:
        deadline = HARD_FLATTEN_TIME_CT
    return ts_ct.time() >= deadline and ts_ct.weekday() < 5


def _apply_friction(
    outcome: str,
    gross_r: float,
    symbol: str,
    risk_usd: float,
    qty: int,
    *,
    round_trip_slippage_ticks: float,
    stop_slippage_ticks: float,
    apply_friction: bool,
) -> tuple[float, str]:
    """Convert idealized R to realized R after slippage + fees + optional
    stop-slippage. Returns (net_r, friction_breakdown_str)."""
    if not apply_friction:
        return gross_r, ""
    if risk_usd <= 0:
        return gross_r, " | friction_skipped(zero_risk)"

    gross_usd = gross_r * risk_usd
    slip_usd = slippage_cost_usd(symbol, round_trip_slippage_ticks, qty)
    fees_usd = fees_round_trip_usd(symbol, qty)
    stop_slip_usd = 0.0
    if outcome == "stop_hit" and stop_slippage_ticks > 0:
        _, tick_value = _TICK_ECONOMICS.get(symbol, (0.0, 0.0))
        stop_slip_usd = stop_slippage_ticks * tick_value * qty

    net_usd = gross_usd - slip_usd - fees_usd - stop_slip_usd
    net_r = net_usd / risk_usd
    breakdown = (
        f" | friction: gross=${gross_usd:+.2f} "
        f"slip=-${slip_usd:.2f} fees=-${fees_usd:.2f}"
    )
    if stop_slip_usd > 0:
        breakdown += f" stop_slip=-${stop_slip_usd:.2f}"
    breakdown += f" net=${net_usd:+.2f} ({net_r:+.2f}R)"
    return net_r, breakdown


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
    apply_friction: bool = True,
    round_trip_slippage_ticks: float = DEFAULT_SLIPPAGE_TICKS_ROUND_TRIP,
    stop_slippage_ticks: float = DEFAULT_STOP_SLIPPAGE_TICKS,
    # 2026-05-12: agent veto callback for shadow-replay (scripts/shadow_replay_agent.py).
    # Signature: (peak_usd, current_unrealized_usd, floor_usd, holds_so_far,
    #             bar_index, bar_ts) -> "CLOSE" | "HOLD"
    # Returning HOLD skips the close and continues the simulation; the
    # number of HOLD overrides is capped at max_agent_holds.
    exit_decision_fn: Optional[callable] = None,
    max_agent_holds: int = 3,
) -> tuple[str, float, str]:
    """Replay bars under production exit logic.

    Returns (outcome, exec_mirror_pnl_r, notes).

    Outcome codes:
      stop_hit        — broker stop hit first (adds stop-slippage)
      profit_lock     — trailing-profit-lock tier triggered (typical winner path)
      loss_cap        — LOSS_TIER_HARD_CAP_USD floor (belt-and-suspenders)
      gain_cap        — GAIN_TIER_HARD_CAP_USD ceiling (if set)
      hard_flatten    — 3:10 PM CT enforcement
      time_stopped    — ran the timeout without any exit; mark-to-market
      no_fill         — entry never tagged within fill window
      invalidated     — missing bars / risk_usd / tick economics

    Friction (applied by default, set apply_friction=False to disable):
      * round-trip slippage = 1.5 ticks (0.75 entry + 0.75 exit)
      * per-symbol fees = tools/shadow_realism.FEES_PER_ROUND_TRIP
      * additional stop-slippage = 1.0 tick when outcome=stop_hit
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

    if risk_usd is None or risk_usd <= 0:
        risk_usd = (risk_per_unit / tick_size) * tick_value * qty
    if risk_usd <= 0:
        return "invalidated", 0.0, "could not compute risk_usd"

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

    parsed.sort(key=lambda p: p[0] if p[0] else datetime.min.replace(tzinfo=timezone.utc))

    entry_filled_idx: Optional[int] = None
    entry_ts: Optional[datetime] = None
    for i, (ts, hi, lo, cl) in enumerate(parsed):
        if lo <= entry <= hi:
            entry_filled_idx = i
            entry_ts = ts
            break
    if entry_filled_idx is None:
        return "no_fill", 0.0, "entry not tagged in shadow window"

    peak_unrealized = 0.0
    timeout_ts: Optional[datetime] = None
    if entry_ts is not None:
        timeout_ts = entry_ts + timedelta(hours=timeout_hours)
    holds_so_far = 0   # counter for agent HOLD overrides this trade

    def _finalize(outcome: str, gross_r: float, note: str) -> tuple[str, float, str]:
        net_r, breakdown = _apply_friction(
            outcome, gross_r, symbol, risk_usd, qty,
            round_trip_slippage_ticks=round_trip_slippage_ticks,
            stop_slippage_ticks=stop_slippage_ticks,
            apply_friction=apply_friction,
        )
        return outcome, net_r, (note + breakdown)[:240]

    for i in range(entry_filled_idx, len(parsed)):
        ts, hi, lo, cl = parsed[i]

        if side == "long" and lo <= stop:
            return _finalize("stop_hit", -1.0, f"stop @ {stop} bar={ts.isoformat() if ts else '?'}")
        if side == "short" and hi >= stop:
            return _finalize("stop_hit", -1.0, f"stop @ {stop} bar={ts.isoformat() if ts else '?'}")

        if ts is not None and _is_past_hard_flatten(ts):
            move = (cl - entry) if side == "long" else (entry - cl)
            usd = (move / tick_size) * tick_value * qty
            gross_r = usd / risk_usd
            return _finalize("hard_flatten", gross_r,
                              f"3:10 PM CT close={cl} pnl=${usd:+.2f}")

        favorable = hi if side == "long" else lo
        move_fav = (favorable - entry) if side == "long" else (entry - favorable)
        fav_usd = (move_fav / tick_size) * tick_value * qty
        if fav_usd > peak_unrealized:
            peak_unrealized = fav_usd

        # Skip profit-protect / loss-cap evaluation on the entry bar itself.
        # In production the position has just opened; profit_protect runs on
        # subsequent scans. Checking it on the entry bar's unfavorable extreme
        # creates a false same-bar close that production wouldn't produce.
        if i == entry_filled_idx:
            continue

        unfavorable = lo if side == "long" else hi
        move_unfav = (unfavorable - entry) if side == "long" else (entry - unfavorable)
        unfav_usd = (move_unfav / tick_size) * tick_value * qty

        should_close, reason = decide(unrealized=unfav_usd, prev_peak=peak_unrealized,
                                       tiers=tiers, gain_cap=gain_cap_usd,
                                       loss_cap=loss_cap_usd)
        if should_close:
            if "trailing_lock" in reason:
                import re as _re
                m = _re.search(r"floor \$(-?\d+(?:\.\d+)?)", reason)
                exit_usd = float(m.group(1)) if m else unfav_usd
                outcome = "profit_lock"
                # Agent veto for trailing_lock only — never overrides
                # loss_cap or gain_cap (those stay mechanical).
                # NOTE: unfav_usd here is the close-or-extreme of the bar,
                # which is what decide() saw. We pass it as current_unrealized.
                if (exit_decision_fn is not None
                        and holds_so_far < max_agent_holds):
                    try:
                        decision = exit_decision_fn(
                            peak_unrealized, unfav_usd, exit_usd,
                            holds_so_far, i, ts,
                        )
                    except Exception:
                        decision = "CLOSE"
                    if decision == "HOLD":
                        holds_so_far += 1
                        continue   # skip this close, walk forward
            elif "loss_hard_cap" in reason:
                exit_usd = -float(loss_cap_usd)
                outcome = "loss_cap"
            elif "hard_cap" in reason:
                exit_usd = float(gain_cap_usd) if gain_cap_usd else unfav_usd
                outcome = "gain_cap"
            else:
                exit_usd = unfav_usd
                outcome = "exit_unknown"
            gross_r = exit_usd / risk_usd
            return _finalize(outcome, gross_r, reason[:120])

        if timeout_ts is not None and ts is not None and ts >= timeout_ts:
            move = (cl - entry) if side == "long" else (entry - cl)
            usd = (move / tick_size) * tick_value * qty
            gross_r = usd / risk_usd
            return _finalize("time_stopped", gross_r,
                              f"timeout {timeout_hours}h close={cl} pnl=${usd:+.2f}")

    _, _, _, last_close = parsed[-1]
    move = (last_close - entry) if side == "long" else (entry - last_close)
    usd = (move / tick_size) * tick_value * qty
    gross_r = usd / risk_usd
    return _finalize("time_stopped", gross_r,
                      f"end-of-bars mtm @ {last_close} pnl=${usd:+.2f}")
