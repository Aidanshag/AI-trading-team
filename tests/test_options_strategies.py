"""Tests for tools/options/strategies.py and position.py."""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta

import pytest

from tools.options import strategies as strats
from tools.options.position import Leg, Position


def _expiry_30d():
    return (datetime.now(tz=timezone.utc) + timedelta(days=30)).date()


def _expiry_60d():
    return (datetime.now(tz=timezone.utc) + timedelta(days=60)).date()


# ── Iron condor ────────────────────────────────────────────────────

def test_iron_condor_has_4_legs():
    pos = strats.iron_condor(S=100, expiry=_expiry_30d())
    assert len(pos.legs) == 4


def test_iron_condor_is_net_credit():
    pos = strats.iron_condor(S=100, expiry=_expiry_30d())
    mtm = pos.mark_to_market(S=100, r=0.045,
                              sigma_by_leg={i: 0.20 for i in range(4)})
    # Net entry cost is negative (we received credit) — signed_qty handles signs
    # For an iron condor, total_entry_cost should be negative (= credit received)
    assert mtm["total_entry_cost"] < 0


def test_iron_condor_delta_near_zero_at_inception():
    pos = strats.iron_condor(S=100, expiry=_expiry_30d())
    g = pos.aggregate_greeks(S=100, r=0.045,
                              sigma_by_leg={i: 0.20 for i in range(4)})
    # Symmetric short call+put delta near zero
    assert abs(g["delta"]) < 50  # small relative to leg sizes


# ── Vertical credit spread ────────────────────────────────────────

def test_vertical_call_credit_spread():
    pos = strats.vertical_credit_spread(S=100, expiry=_expiry_30d(),
                                          option_type="c")
    assert len(pos.legs) == 2
    # Short call (lower K) + long call (higher K)
    short_leg = next(l for l in pos.legs if l.side == "short")
    long_leg = next(l for l in pos.legs if l.side == "long")
    assert short_leg.strike < long_leg.strike
    assert short_leg.option_type == "c" and long_leg.option_type == "c"


def test_vertical_put_credit_spread():
    pos = strats.vertical_credit_spread(S=100, expiry=_expiry_30d(),
                                          option_type="p")
    short_leg = next(l for l in pos.legs if l.side == "short")
    long_leg = next(l for l in pos.legs if l.side == "long")
    # For puts: short higher K, long lower K
    assert short_leg.strike > long_leg.strike


# ── Iron butterfly ────────────────────────────────────────────────

def test_iron_butterfly_atm_short_legs():
    pos = strats.iron_butterfly(S=100, expiry=_expiry_30d())
    assert len(pos.legs) == 4
    shorts = [l for l in pos.legs if l.side == "short"]
    assert all(l.strike == 100 for l in shorts), "Short legs at ATM"


# ── Calendar spread ────────────────────────────────────────────────

def test_calendar_spread_has_different_expiries():
    pos = strats.calendar_spread(S=100, near_expiry=_expiry_30d(),
                                   far_expiry=_expiry_60d())
    assert len(pos.legs) == 2
    near = next(l for l in pos.legs if l.side == "short")
    far = next(l for l in pos.legs if l.side == "long")
    assert near.expiry != far.expiry
    assert near.expiry < far.expiry


# ── Cash-secured put / covered call ───────────────────────────────

def test_cash_secured_put_single_short_put():
    pos = strats.cash_secured_put(S=100, expiry=_expiry_30d())
    assert len(pos.legs) == 1
    assert pos.legs[0].option_type == "p"
    assert pos.legs[0].side == "short"


def test_covered_call_qty_from_shares():
    pos = strats.covered_call(S=100, shares=300, expiry=_expiry_30d())
    assert pos.legs[0].option_type == "c"
    assert pos.legs[0].side == "short"
    assert pos.legs[0].qty == 3  # 300 shares / 100


# ── Straddles ────────────────────────────────────────────────────

def test_long_straddle_two_long_atm_legs():
    pos = strats.long_straddle(S=100, expiry=_expiry_30d())
    assert len(pos.legs) == 2
    assert all(l.side == "long" for l in pos.legs)
    assert all(l.strike == 100 for l in pos.legs)
    types = sorted(l.option_type for l in pos.legs)
    assert types == ["c", "p"]


def test_short_straddle_two_short_atm_legs():
    pos = strats.short_straddle(S=100, expiry=_expiry_30d())
    assert all(l.side == "short" for l in pos.legs)


# ── Position MTM ──────────────────────────────────────────────────

def test_position_pnl_zero_at_entry_with_same_sigma():
    """If we mark immediately after entry at the same IV used to price,
    P&L should be ~0 (modulo tiny time-decay over a few microseconds)."""
    pos = strats.iron_condor(S=100, expiry=_expiry_30d())
    mtm = pos.mark_to_market(S=100, r=0.045,
                              sigma_by_leg={i: 0.20 for i in range(4)})
    # Allow a few cents from the floating-point + tiny time elapsed
    assert abs(mtm["total_pnl"]) < 1.0


def test_position_long_straddle_gains_on_big_move():
    """Long straddle should gain meaningfully if spot moves 10% up."""
    pos = strats.long_straddle(S=100, expiry=_expiry_30d())
    mtm_flat = pos.mark_to_market(S=100, r=0.045,
                                    sigma_by_leg={0: 0.20, 1: 0.20})
    mtm_up = pos.mark_to_market(S=110, r=0.045,
                                  sigma_by_leg={0: 0.20, 1: 0.20})
    assert mtm_up["total_pnl"] > mtm_flat["total_pnl"]
