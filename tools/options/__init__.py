"""tools.options — options pricing, greeks, and strategy library.

Built 2026-05-17 per user direction:
  "for 12 build all and above. lets build the best strategies you can
   identify. use aspects of our own black scholes if you can build with
   edge as well as the greek library"

Structure:
  - black_scholes.py: our own BS implementation (educational + diffable)
  - greeks.py: delta, gamma, vega, theta, rho — analytical formulas
  - vol_surface.py: IV term-structure helpers (skew curve fitting)
  - strategies.py: multi-leg strategy library (iron condor, vertical
                   spreads, calendar, etc.)
  - position.py: multi-leg P&L aggregation
  - signals.py: when/how to fire each strategy (entry rules)

For IB workstream only. NOT wired to Topstep (futures-only, no options
support). Trader for IB options is a separate workstream entirely.

Verification harness uses py_vollib (if installed) to cross-check our
BS prices and greeks — if our impl drifts >0.1% from py_vollib, that's
a bug. Falls back gracefully when py_vollib isn't available.
"""
from __future__ import annotations

__all__ = [
    "black_scholes",
    "greeks",
    "vol_surface",
    "strategies",
    "position",
]
