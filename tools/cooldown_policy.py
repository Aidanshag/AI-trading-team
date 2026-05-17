"""cooldown_policy — outcome-aware per-symbol cooldown.

User direction (2026-05-11 evening + 2026-05-17 follow-up): replace the
flat SAME_SYMBOL_COOLDOWN_MIN = 45 with a table that depends on the
LAST trade's outcome. Hypothesis: a winning streak on a trending symbol
shouldn't block follow-ons for 45min — that hands the trend back to the
market. A losing streak deserves a longer cooldown to prevent tilt.

Policy v1 (2026-05-17, ships in SHADOW MODE):
  last_outcome     base_cooldown_min  rationale
  win              15                 same-symbol momentum — re-enter sooner
  small_loss       45                 baseline cool-off
  big_loss         90                 deeper cool-off, anti-tilt
  stop_clean       30                 stop hit cleanly — normal rotation
  unknown          45                 default (matches old flat behavior)

A loss is "big" if the realized R-multiple is <= -1.5 (more than 1.5×
the per-trade risk). Otherwise "small_loss".

A trade is "stop_clean" if exit reason is 'stop_hit' or 'broker_stop'
without intra-bar drama.

Per-symbol overrides (from live_trader.SAME_SYMBOL_COOLDOWN_OVERRIDES)
multiply the base by `symbol_factor`. E.g., MGC = 0.33× (15min → 5min,
45min → 15min, etc.) because its 1/10 risk per contract means re-entries
are cheaper.

This module is PURE: takes last-trade info, returns int minutes. Both the
trader (live) and a shadow-trader pattern can use it. The shadow path
queues signals into shadow_trades when the live cooldown blocks them,
so we can A/B compare: would the new policy have caught more winners?
"""
from __future__ import annotations

from typing import Optional


# ── Outcome-aware base cooldowns (minutes) ─────────────────────────

BASE_COOLDOWN_MIN: dict[str, int] = {
    "win":         15,   # winning streaks shouldn't block follow-ons hard
    "small_loss":  45,   # baseline cool-off (matches old flat behavior)
    "big_loss":    90,   # anti-tilt — wait for reset
    "stop_clean":  30,   # stop hit cleanly; symbol still tradeable
    "unknown":     45,   # default fallback
}

# Per-symbol multipliers (applied to BASE_COOLDOWN_MIN)
SYMBOL_FACTORS: dict[str, float] = {
    "MGC":  0.33,  # micro gold — 1/10 risk → 3× more re-entry frequency
    "MNQ":  0.33,
    "MES":  0.33,
    "M2K":  0.33,
    "MYM":  0.33,
    "M6E":  0.33,
    "M6B":  0.33,
    "MCL":  0.33,
    "MNG":  0.33,
    "MHG":  0.33,
    "SIL":  0.33,
}

BIG_LOSS_R_THRESHOLD: float = -1.5  # r-multiple at-or-below = "big_loss"


# ── Outcome classifier ────────────────────────────────────────────

def classify_outcome(realized_r: float | None,
                     exit_reason: str | None) -> str:
    """Map (R-multiple, exit reason) → one of the cooldown keys above.

    realized_r: trade's r-multiple. Positive = win, negative = loss.
    exit_reason: 'target_hit', 'stop_hit', 'trailing_lock', 'time_decay',
                 'reversal_exit', 'broker_stop', etc.

    Returns one of: 'win', 'small_loss', 'big_loss', 'stop_clean', 'unknown'.
    """
    if realized_r is None:
        return "unknown"
    if realized_r > 0:
        return "win"
    if realized_r <= BIG_LOSS_R_THRESHOLD:
        return "big_loss"
    # Stop-hit losses are "cleaner" than trailing-lock or time-decay losses
    if exit_reason in ("stop_hit", "broker_stop"):
        return "stop_clean"
    return "small_loss"


def cooldown_minutes(symbol: str,
                     last_outcome: str | None,
                     symbol_factor_override: float | None = None) -> int:
    """Return the cooldown in minutes for `symbol` given the LAST trade's
    outcome class. Applies per-symbol multiplier.

    `symbol_factor_override`: optional explicit multiplier (e.g., for
    tests). Otherwise falls back to SYMBOL_FACTORS[symbol] or 1.0.
    """
    outcome = last_outcome or "unknown"
    base = BASE_COOLDOWN_MIN.get(outcome, BASE_COOLDOWN_MIN["unknown"])
    factor = (symbol_factor_override
              if symbol_factor_override is not None
              else SYMBOL_FACTORS.get(symbol, 1.0))
    return max(1, int(round(base * factor)))


# ── Shadow-mode helper ────────────────────────────────────────────

def cooldown_decision(symbol: str,
                      live_cooldown_min: int,
                      last_outcome: str | None,
                      minutes_since_last: float) -> dict:
    """Compare the live (flat) cooldown to the new outcome-aware one.
    Returns a dict for shadow logging:

      {
        "live_block": bool,
        "policy_v1_block": bool,
        "delta_min": int,   # negative = policy_v1 unblocks sooner
        "outcome": str,
      }

    `live_cooldown_min`: the current production cooldown for this symbol
      (e.g., SAME_SYMBOL_COOLDOWN_MIN or its override).
    `last_outcome`: classify_outcome() result.
    `minutes_since_last`: minutes elapsed since the last trade on this symbol.
    """
    policy_min = cooldown_minutes(symbol, last_outcome)
    return {
        "live_block": minutes_since_last < live_cooldown_min,
        "policy_v1_block": minutes_since_last < policy_min,
        "delta_min": policy_min - live_cooldown_min,
        "outcome": last_outcome or "unknown",
        "live_cooldown_min": live_cooldown_min,
        "policy_v1_cooldown_min": policy_min,
        "minutes_since_last": round(minutes_since_last, 1),
    }
