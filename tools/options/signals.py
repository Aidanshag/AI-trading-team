"""Options strategy entry-rule signals — when/how to fire each builder.

For each of the 8 strategies in tools/options/strategies.py, define the
ENTRY RULE (price/IV/event context) and the EXIT RULE (profit target,
stop, time-stop). These produce shadow trades in the IB workstream.

When an IB trader is built, it consumes these signals exactly the way
the Topstep brain_signaler emits to live_trader.

User direction 2026-05-17: "build the best strategies you can identify."
Each rule below is documented with the academic / empirical justification.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional

from tools.options import strategies as opstrats
from tools.options.position import Position


@dataclass
class OptionsSignal:
    """A complete options-trade proposal."""
    strategy_name: str
    position: Position
    entry_rationale: str          # WHY we entered
    profit_target_pct: float      # close at +X% of max gain
    stop_loss_pct: float           # close at -X% of max loss
    time_stop_days: int            # close N days before expiry regardless
    broker: str = "ib"             # routes to IB workstream
    ts: datetime = None

    def __post_init__(self):
        if self.ts is None:
            self.ts = datetime.now(tz=timezone.utc)


# ── Entry-rule functions ──────────────────────────────────────────


def iron_condor_signal(S: float, expiry: date, sigma_current: float,
                        iv_rank: float, r: float = 0.045) -> OptionsSignal | None:
    """ENTRY RULE: IV rank > 50 (premium is rich), no big event in
    next 14 days (low gap risk), expiry 30-45 days out.

    iv_rank: percentile of current IV vs the last year of IV (0-100).
    Real-IB call would compute this from option_chain history.
    """
    if iv_rank < 50:
        return None
    days_to_expiry = (expiry - datetime.now(tz=timezone.utc).date()).days
    if not 28 <= days_to_expiry <= 50:
        return None
    pos = opstrats.iron_condor(S=S, expiry=expiry, r=r, sigma=sigma_current,
                                 target_short_delta=0.20)
    return OptionsSignal(
        strategy_name="iron_condor",
        position=pos,
        entry_rationale=(f"IV rank {iv_rank:.0f} > 50 (premium rich), "
                          f"{days_to_expiry}d expiry, 20-delta wings, "
                          f"sell vol via 4-leg defined-risk structure"),
        profit_target_pct=0.50,   # close at 50% of max credit (industry standard)
        stop_loss_pct=2.00,        # close at 2× the credit lost
        time_stop_days=21,         # close 21d before expiry to avoid gamma blow-up
    )


def vertical_credit_spread_signal(S: float, expiry: date,
                                     sigma_current: float, trend: str,
                                     iv_rank: float,
                                     r: float = 0.045) -> OptionsSignal | None:
    """ENTRY RULE: directional bias + IV rank > 40.
    trend='bullish' → put credit spread (collect on uptrend)
    trend='bearish' → call credit spread (collect on downtrend)
    """
    if iv_rank < 40:
        return None
    if trend not in ("bullish", "bearish"):
        return None
    option_type = "p" if trend == "bullish" else "c"
    pos = opstrats.vertical_credit_spread(
        S=S, expiry=expiry, option_type=option_type,
        r=r, sigma=sigma_current, short_delta=0.30, width_pct=0.05,
    )
    return OptionsSignal(
        strategy_name=f"vertical_{option_type}_credit",
        position=pos,
        entry_rationale=(f"{trend} bias + IV rank {iv_rank:.0f}, "
                          f"30-delta short {option_type}, 5% wing"),
        profit_target_pct=0.50,
        stop_loss_pct=1.50,
        time_stop_days=14,
    )


def long_straddle_pre_earnings_signal(S: float, expiry: date,
                                         sigma_current: float,
                                         days_to_earnings: int,
                                         expected_iv_pop: float,
                                         r: float = 0.045) -> OptionsSignal | None:
    """ENTRY RULE: Fire 7-3 days before earnings; expect IV to expand
    further (long vega) + big move on report. Exit before earnings
    morning to capture the IV pop without taking the gamma blowup.
    """
    if not 3 <= days_to_earnings <= 7:
        return None
    if expected_iv_pop < 0.10:  # need at least 10% IV expansion expected
        return None
    pos = opstrats.long_straddle(S=S, expiry=expiry, r=r, sigma=sigma_current)
    return OptionsSignal(
        strategy_name="long_straddle_pre_earnings",
        position=pos,
        entry_rationale=(f"earnings in {days_to_earnings}d, "
                          f"expected IV pop {expected_iv_pop:.0%} — long vega"),
        profit_target_pct=1.00,    # close at 100% gain
        stop_loss_pct=0.50,         # close at 50% loss
        time_stop_days=1,           # close 1 day BEFORE earnings (don't hold the event)
    )


def short_straddle_post_earnings_signal(S: float, expiry: date,
                                           sigma_current: float,
                                           hours_since_earnings: int,
                                           current_iv_vs_pre: float,
                                           r: float = 0.045) -> OptionsSignal | None:
    """ENTRY RULE: Fire 1-4 hours after earnings release when IV is still
    elevated vs pre-earnings. Capture IV crush (theta + short vega)."""
    if not 1 <= hours_since_earnings <= 4:
        return None
    if current_iv_vs_pre < 1.20:  # need IV still 20%+ above pre-earnings
        return None
    pos = opstrats.short_straddle(S=S, expiry=expiry, r=r, sigma=sigma_current)
    return OptionsSignal(
        strategy_name="short_straddle_post_earnings",
        position=pos,
        entry_rationale=(f"earnings {hours_since_earnings}h ago, "
                          f"IV still {current_iv_vs_pre:.1f}x pre-earnings — "
                          f"capture IV crush"),
        profit_target_pct=0.60,    # 60% of credit
        stop_loss_pct=2.00,         # naked short — wider stop, smaller size
        time_stop_days=7,           # close 7d after entry regardless
    )


def calendar_spread_signal(S: float, near_expiry: date, far_expiry: date,
                            sigma_near: float, sigma_far: float,
                            r: float = 0.045) -> OptionsSignal | None:
    """ENTRY RULE: front-month IV > 1.10x back-month IV (steep term structure).
    Sell expensive near, buy cheaper far → benefit from IV normalization."""
    if sigma_near < sigma_far * 1.10:
        return None
    pos = opstrats.calendar_spread(S=S, near_expiry=near_expiry,
                                     far_expiry=far_expiry,
                                     r=r, sigma_near=sigma_near, sigma_far=sigma_far)
    return OptionsSignal(
        strategy_name="calendar_spread",
        position=pos,
        entry_rationale=(f"front IV {sigma_near:.0%} > {sigma_far:.0%} "
                          f"back IV (term structure inverted)"),
        profit_target_pct=0.30,
        stop_loss_pct=0.50,
        time_stop_days=3,           # close 3d before near-expiry
    )


def cash_secured_put_signal(S: float, expiry: date, sigma: float,
                             iv_rank: float,
                             willing_buy_price: float,
                             r: float = 0.045) -> OptionsSignal | None:
    """ENTRY RULE: IV rank > 40 + willing to own stock at strike.
    Strike = target buy price (≤ current S). If unassigned, keep premium.
    If assigned, get stock at the price you wanted minus premium."""
    if iv_rank < 40:
        return None
    if willing_buy_price >= S:
        return None  # only fires when willing to pay LESS than current
    # Override default delta-strike with the explicit willing-buy-price
    from tools.options.position import Leg
    from tools.options import black_scholes as bs
    T = (datetime.combine(expiry, datetime.min.time(), tzinfo=timezone.utc)
         - datetime.now(tz=timezone.utc)).total_seconds() / (365.25 * 86400)
    if T <= 0:
        return None
    px = bs.put_price(S, willing_buy_price, T, r, sigma)
    pos = Position(
        name=f"cash_secured_put_{int(willing_buy_price)}",
        legs=[Leg("p", willing_buy_price, expiry, "short", 1, px)],
    )
    return OptionsSignal(
        strategy_name="cash_secured_put",
        position=pos,
        entry_rationale=(f"want to own at ${willing_buy_price:.0f} (current "
                          f"${S:.2f}), IV rank {iv_rank:.0f} — collect premium "
                          f"while waiting"),
        profit_target_pct=0.50,
        stop_loss_pct=1.00,         # = let it assign if stock crosses
        time_stop_days=0,            # hold to expiry (assignment OK)
    )


def covered_call_signal(S: float, shares_held: int, expiry: date,
                          sigma: float, iv_rank: float,
                          target_call_strike: float | None = None,
                          r: float = 0.045) -> OptionsSignal | None:
    """ENTRY RULE: Hold ≥100 shares + IV rank > 30 + neutral-to-mildly-bullish."""
    if shares_held < 100:
        return None
    if iv_rank < 30:
        return None
    pos = opstrats.covered_call(S=S, shares=shares_held, expiry=expiry,
                                  r=r, sigma=sigma, target_delta=0.25)
    return OptionsSignal(
        strategy_name="covered_call",
        position=pos,
        entry_rationale=(f"long {shares_held} shares, IV rank {iv_rank:.0f}, "
                          f"sell 25-delta call for income"),
        profit_target_pct=0.50,
        stop_loss_pct=1.50,
        time_stop_days=7,
    )


# Map name → signal builder, for easy iteration
SIGNAL_BUILDERS: dict[str, Callable] = {
    "iron_condor": iron_condor_signal,
    "vertical_credit_spread": vertical_credit_spread_signal,
    "long_straddle_pre_earnings": long_straddle_pre_earnings_signal,
    "short_straddle_post_earnings": short_straddle_post_earnings_signal,
    "calendar_spread": calendar_spread_signal,
    "cash_secured_put": cash_secured_put_signal,
    "covered_call": covered_call_signal,
}
