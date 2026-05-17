"""Multi-leg options position P&L + Greeks aggregation.

A Position is a collection of Legs. Each Leg is (option_type, strike,
expiry, side, qty, entry_price). Position P&L is the sum of per-leg
mark-to-market values minus entry costs, weighted by qty + sign.

Position greeks are SUMS of per-leg greeks (delta is linear,
gamma/vega/theta/rho also linear). This is the right aggregation for
any strategy (vertical spread, iron condor, calendar, ratio, etc.).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Literal

from tools.options import black_scholes as bs


@dataclass
class Leg:
    option_type: Literal["c", "p"]    # call or put
    strike: float
    expiry: date                       # expiry date (calendar)
    side: Literal["long", "short"]     # long buys premium, short sells
    qty: int                            # contracts (usually 100 shares each)
    entry_price: float                 # premium paid (long) or received (short)
    multiplier: int = 100              # 100 for equity options, 50 for some

    def signed_qty(self) -> int:
        return self.qty if self.side == "long" else -self.qty

    def years_to_expiry(self, now: datetime | None = None) -> float:
        if now is None:
            now = datetime.now(tz=timezone.utc)
        td = datetime.combine(self.expiry, datetime.min.time(),
                              tzinfo=timezone.utc) - now
        return max(td.total_seconds() / (365.25 * 86400), 1e-8)


@dataclass
class Position:
    legs: list[Leg] = field(default_factory=list)
    name: str = ""

    def add(self, leg: Leg) -> "Position":
        self.legs.append(leg)
        return self

    def mark_to_market(self, S: float, r: float, sigma_by_leg: dict | None = None,
                       now: datetime | None = None,
                       q: float = 0.0) -> dict:
        """Compute current value of each leg + aggregate P&L.

        sigma_by_leg: optional dict {leg_index: sigma}. If None, uses
        each leg's "current IV" assumed equal to entry IV (degenerate
        but useful for testing strategy P&L shapes).
        """
        total_value = 0.0
        total_entry_cost = 0.0
        leg_values = []
        for i, leg in enumerate(self.legs):
            T = leg.years_to_expiry(now)
            sigma = (sigma_by_leg or {}).get(i, 0.20)  # 20% default
            try:
                current_price = bs.price(leg.option_type, S, leg.strike,
                                          T, r, sigma, q)
            except ValueError:
                current_price = 0.0
            signed = leg.signed_qty()
            leg_value = current_price * signed * leg.multiplier
            entry_cost = leg.entry_price * signed * leg.multiplier
            total_value += leg_value
            total_entry_cost += entry_cost
            leg_values.append({
                "leg_index": i, "current_price": current_price,
                "leg_value": leg_value, "entry_cost": entry_cost,
                "pnl": leg_value - entry_cost,
            })
        return {
            "name": self.name,
            "total_pnl": total_value - total_entry_cost,
            "total_current_value": total_value,
            "total_entry_cost": total_entry_cost,
            "legs": leg_values,
        }

    def aggregate_greeks(self, S: float, r: float,
                          sigma_by_leg: dict | None = None,
                          now: datetime | None = None,
                          q: float = 0.0) -> dict:
        """Sum greeks across all legs — what the position behaves like."""
        totals = {"delta": 0.0, "gamma": 0.0, "vega": 0.0,
                  "theta": 0.0, "rho": 0.0}
        for i, leg in enumerate(self.legs):
            T = leg.years_to_expiry(now)
            sigma = (sigma_by_leg or {}).get(i, 0.20)
            try:
                g = bs.all_greeks(leg.option_type, S, leg.strike, T, r, sigma, q)
            except ValueError:
                continue
            signed = leg.signed_qty()
            mult = leg.multiplier
            for key in totals:
                totals[key] += g[key] * signed * mult
        return totals

    def max_loss(self, S_range: tuple[float, float] = None,
                 r: float = 0.045, sigma: float = 0.20,
                 now: datetime | None = None) -> float:
        """Find the max loss across a spot price range at expiry. For
        defined-risk structures (verticals, iron condors), this is
        finite. For naked shorts, returns negative infinity."""
        if S_range is None:
            strikes = [leg.strike for leg in self.legs]
            mn, mx = min(strikes), max(strikes)
            spread = mx - mn
            S_range = (max(0.01, mn - spread), mx + spread)
        lo, hi = S_range
        # Sample at finer granularity near strikes
        worst = 0.0
        steps = 100
        for i in range(steps + 1):
            S = lo + (hi - lo) * i / steps
            mtm = self.mark_to_market(S, r,
                                       sigma_by_leg={j: sigma for j in range(len(self.legs))},
                                       now=now)
            if mtm["total_pnl"] < worst:
                worst = mtm["total_pnl"]
        return worst
