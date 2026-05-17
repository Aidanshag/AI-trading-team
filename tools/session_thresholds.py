"""session_thresholds — session-aware threshold multipliers.

Closes the "open encoding gap" flagged in CLAUDE.md Pattern B section:
  "volume thresholds aren't yet session-aware (calibrate-then-deploy
   version of the principle isn't enforced for volume)."

Strategies that use rolling baselines (e.g., volume_spike_reversal's
20-bar rolling average) partially adapt — the baseline self-scales to
the local regime. But the MULTIPLIER applied to the baseline ("3× the
baseline = spike") is constant across sessions. Asian sessions have
30-50% lower base volume; what looks like a 3× spike in Asian noise
is a routine RTH bar.

This module provides:
  - VOLUME_SPIKE_MULT_BY_SESSION: per-session multipliers
  - volume_spike_mult_for_session(session): wrapper
  - ATR_FLOOR_BY_SESSION: minimum ATR-distance multipliers (e.g., for
    stop placement — Asian needs wider relative stops to escape noise)
  - atr_mult_for_session(session): wrapper

Calibration: Asian = 4× (was 3×, tighter to filter noise),
RTH/London = 3× baseline, PostClose = 3.5×. These can be tuned per
sec_type later (energy futures need different floors than equities).
"""
from __future__ import annotations


# Volume-spike multipliers per session
# (= what counts as "abnormal volume" given the session's baseline)
VOLUME_SPIKE_MULT_BY_SESSION: dict[str, float] = {
    "Asian":     4.0,   # Asian bars are 30-50% lower volume → need higher
                         # multiplier so we don't fire on routine noise
    "London":    3.0,   # baseline
    "RTH":       3.0,   # baseline (this is where the 3.0 was calibrated)
    "PostClose": 3.5,   # between RTH and Asian
}
DEFAULT_VOLUME_SPIKE_MULT: float = 3.0


# ATR-distance multipliers per session
# (= how many ATRs of stop distance to use for entry/exit)
ATR_FLOOR_BY_SESSION: dict[str, float] = {
    "Asian":     1.5,   # smaller TR → need more cushion to escape noise
    "London":    1.0,   # baseline
    "RTH":       1.0,   # baseline
    "PostClose": 1.2,   # slightly wider than RTH
}
DEFAULT_ATR_MULT: float = 1.0


def volume_spike_mult_for_session(session: str | None) -> float:
    """Return the volume-spike threshold multiplier for the given session.
    Defaults to DEFAULT_VOLUME_SPIKE_MULT (3.0) for unknown / missing."""
    if not session:
        return DEFAULT_VOLUME_SPIKE_MULT
    return VOLUME_SPIKE_MULT_BY_SESSION.get(session, DEFAULT_VOLUME_SPIKE_MULT)


def atr_mult_for_session(session: str | None) -> float:
    """Return the ATR-distance multiplier (for stops, gap detection, etc.)
    for the given session. Defaults to DEFAULT_ATR_MULT (1.0)."""
    if not session:
        return DEFAULT_ATR_MULT
    return ATR_FLOOR_BY_SESSION.get(session, DEFAULT_ATR_MULT)
