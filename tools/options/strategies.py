"""Options strategy library.

8 high-edge strategies user-prioritized 2026-05-17:
  1. Iron condor — sell ATM call+put spreads (theta capture)
  2. Vertical credit spread (call/put) — defined-risk premium income
  3. Iron butterfly — sell ATM straddle + buy OTM wings
  4. Calendar spread — sell near, buy far (IV term-structure plays)
  5. Cash-secured PUT — sell ATM/OTM put to earn premium or get assigned cheaper
  6. Covered call — long stock + sell OTM call for income
  7. Long straddle (pre-earnings) — buy ATM call + put for IV expansion
  8. Short straddle (post-earnings) — sell ATM call + put for IV crush

Each builder returns a Position (multi-leg). Strikes chosen per a
common convention: ATM = nearest available strike to spot; OTM_25
≈ 25-delta strike (computed via BS).

These builders are PURE: take spot + expiry + IV; return Position.
Entry pricing uses BS at the given sigma (= mid-price proxy). When
trading live, replace with actual market quotes.
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta, timezone

from tools.options import black_scholes as bs
from tools.options.position import Leg, Position


def _years_to_expiry(expiry: date, now: datetime | None = None) -> float:
    if now is None:
        now = datetime.now(tz=timezone.utc)
    td = datetime.combine(expiry, datetime.min.time(),
                          tzinfo=timezone.utc) - now
    return max(td.total_seconds() / (365.25 * 86400), 1e-8)


def _delta_strike(option_type: str, S: float, T: float, r: float,
                  sigma: float, target_delta: float, q: float = 0.0) -> float:
    """Bisection: find the strike whose absolute delta ≈ target_delta.
    target_delta should be between 0 and 1 (e.g., 0.25 for 25-delta)."""
    lo, hi = S * 0.5, S * 1.5
    for _ in range(60):
        mid = (lo + hi) / 2
        try:
            d = abs(bs.delta(option_type, S, mid, T, r, sigma, q))
        except ValueError:
            d = 0
        if abs(d - target_delta) < 1e-4:
            return mid
        if option_type.lower().startswith("c"):
            if d > target_delta:
                lo = mid  # higher strike = lower call delta
            else:
                hi = mid
        else:  # put
            if d > target_delta:
                hi = mid  # lower strike = lower put delta
            else:
                lo = mid
    return (lo + hi) / 2


# ── Strategy builders ─────────────────────────────────────────────


def iron_condor(S: float, expiry: date, r: float = 0.045,
                sigma: float = 0.20, target_short_delta: float = 0.20,
                wing_width_pct: float = 0.05) -> Position:
    """Sell short call/put at target_short_delta; buy long wings
    wing_width_pct further out. Net credit; max loss = wing_width - credit.
    """
    T = _years_to_expiry(expiry)
    short_call_K = _delta_strike("c", S, T, r, sigma, target_short_delta)
    short_put_K = _delta_strike("p", S, T, r, sigma, target_short_delta)
    long_call_K = short_call_K * (1 + wing_width_pct)
    long_put_K = short_put_K * (1 - wing_width_pct)
    return Position(
        name=f"iron_condor_{int(short_call_K)}c-{int(long_call_K)}c_{int(short_put_K)}p-{int(long_put_K)}p",
        legs=[
            Leg("c", long_call_K, expiry, "long", 1,
                bs.call_price(S, long_call_K, T, r, sigma)),
            Leg("c", short_call_K, expiry, "short", 1,
                bs.call_price(S, short_call_K, T, r, sigma)),
            Leg("p", short_put_K, expiry, "short", 1,
                bs.put_price(S, short_put_K, T, r, sigma)),
            Leg("p", long_put_K, expiry, "long", 1,
                bs.put_price(S, long_put_K, T, r, sigma)),
        ],
    )


def vertical_credit_spread(S: float, expiry: date, option_type: str,
                            r: float = 0.045, sigma: float = 0.20,
                            short_delta: float = 0.30,
                            width_pct: float = 0.05) -> Position:
    """Sell ATM/near-ATM option, buy further OTM for protection. Defined risk."""
    T = _years_to_expiry(expiry)
    short_K = _delta_strike(option_type, S, T, r, sigma, short_delta)
    if option_type.lower().startswith("c"):
        long_K = short_K * (1 + width_pct)
        short_px = bs.call_price(S, short_K, T, r, sigma)
        long_px = bs.call_price(S, long_K, T, r, sigma)
    else:
        long_K = short_K * (1 - width_pct)
        short_px = bs.put_price(S, short_K, T, r, sigma)
        long_px = bs.put_price(S, long_K, T, r, sigma)
    return Position(
        name=f"vertical_{option_type}_credit_{int(short_K)}-{int(long_K)}",
        legs=[
            Leg(option_type, short_K, expiry, "short", 1, short_px),
            Leg(option_type, long_K, expiry, "long", 1, long_px),
        ],
    )


def iron_butterfly(S: float, expiry: date, r: float = 0.045,
                    sigma: float = 0.20, wing_pct: float = 0.05) -> Position:
    """Sell ATM straddle + buy OTM wings. Tighter range than iron condor,
    higher credit, narrower profit zone."""
    T = _years_to_expiry(expiry)
    atm_K = S
    long_call_K = atm_K * (1 + wing_pct)
    long_put_K = atm_K * (1 - wing_pct)
    return Position(
        name=f"iron_butterfly_{int(atm_K)}",
        legs=[
            Leg("c", long_call_K, expiry, "long", 1,
                bs.call_price(S, long_call_K, T, r, sigma)),
            Leg("c", atm_K, expiry, "short", 1,
                bs.call_price(S, atm_K, T, r, sigma)),
            Leg("p", atm_K, expiry, "short", 1,
                bs.put_price(S, atm_K, T, r, sigma)),
            Leg("p", long_put_K, expiry, "long", 1,
                bs.put_price(S, long_put_K, T, r, sigma)),
        ],
    )


def calendar_spread(S: float, near_expiry: date, far_expiry: date,
                     r: float = 0.045, sigma_near: float = 0.20,
                     sigma_far: float = 0.18,
                     option_type: str = "c") -> Position:
    """Sell near-term ATM, buy longer-term same strike. Benefits from IV
    term-structure differential (near IV high after event → crush gives
    short leg premium; long leg retains vega)."""
    K = S  # ATM
    T_near = _years_to_expiry(near_expiry)
    T_far = _years_to_expiry(far_expiry)
    near_px = bs.price(option_type, S, K, T_near, r, sigma_near)
    far_px = bs.price(option_type, S, K, T_far, r, sigma_far)
    return Position(
        name=f"calendar_{option_type}_{int(K)}_{near_expiry}-{far_expiry}",
        legs=[
            Leg(option_type, K, near_expiry, "short", 1, near_px),
            Leg(option_type, K, far_expiry, "long", 1, far_px),
        ],
    )


def cash_secured_put(S: float, expiry: date, r: float = 0.045,
                      sigma: float = 0.20,
                      target_delta: float = 0.30) -> Position:
    """Sell a put at target_delta. If unassigned, keep the premium. If
    assigned, you get the stock at strike (cost-basis-adjusted by premium)."""
    T = _years_to_expiry(expiry)
    K = _delta_strike("p", S, T, r, sigma, target_delta)
    px = bs.put_price(S, K, T, r, sigma)
    return Position(
        name=f"cash_secured_put_{int(K)}",
        legs=[Leg("p", K, expiry, "short", 1, px)],
    )


def covered_call(S: float, shares: int, expiry: date, r: float = 0.045,
                  sigma: float = 0.20, target_delta: float = 0.25) -> Position:
    """Long stock + short OTM call. We model only the call leg here
    (stock leg lives elsewhere as a separate equity position)."""
    T = _years_to_expiry(expiry)
    K = _delta_strike("c", S, T, r, sigma, target_delta)
    px = bs.call_price(S, K, T, r, sigma)
    qty = max(1, shares // 100)
    return Position(
        name=f"covered_call_{int(K)}_x{qty}",
        legs=[Leg("c", K, expiry, "short", qty, px)],
    )


def long_straddle(S: float, expiry: date, r: float = 0.045,
                   sigma: float = 0.20) -> Position:
    """Buy ATM call + put. Pre-earnings IV expansion play.
    Loss = total premium paid if S stays at K through expiry."""
    K = S
    T = _years_to_expiry(expiry)
    return Position(
        name=f"long_straddle_{int(K)}",
        legs=[
            Leg("c", K, expiry, "long", 1, bs.call_price(S, K, T, r, sigma)),
            Leg("p", K, expiry, "long", 1, bs.put_price(S, K, T, r, sigma)),
        ],
    )


def short_straddle(S: float, expiry: date, r: float = 0.045,
                    sigma: float = 0.20) -> Position:
    """Sell ATM call + put. Post-earnings IV-crush play.
    UNDEFINED risk — only fire when capital permits naked sell.
    For defined risk, prefer iron_butterfly()."""
    K = S
    T = _years_to_expiry(expiry)
    return Position(
        name=f"short_straddle_{int(K)}",
        legs=[
            Leg("c", K, expiry, "short", 1, bs.call_price(S, K, T, r, sigma)),
            Leg("p", K, expiry, "short", 1, bs.put_price(S, K, T, r, sigma)),
        ],
    )


# Public API: dict of all builders for easy enumeration
STRATEGY_BUILDERS = {
    "iron_condor": iron_condor,
    "vertical_credit_spread": vertical_credit_spread,
    "iron_butterfly": iron_butterfly,
    "calendar_spread": calendar_spread,
    "cash_secured_put": cash_secured_put,
    "covered_call": covered_call,
    "long_straddle": long_straddle,
    "short_straddle": short_straddle,
}
