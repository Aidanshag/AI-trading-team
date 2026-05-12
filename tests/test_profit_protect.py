"""Unit tests for tools/profit_protect.py — trailing-profit-lock decisions.

Tests target the PURE decision logic (decide function); end-to-end
check_and_close uses fakes for broker interaction.
"""
from __future__ import annotations

import pandas as pd
import pytest

from tools import profit_protect as pp


# ── decide() — pure decision logic ────────────────────────────

def test_decide_no_action_below_first_tier():
    """Unrealized below any tier threshold and within loss/gain caps -> no close."""
    should, reason = pp.decide(unrealized=10.0, prev_peak=10.0)
    assert should is False
    assert reason == ""


def test_decide_no_hard_gain_cap_by_default():
    """2026-05-11: hard cap removed by default (None). Big peaks should
    not auto-close just because they're big — trailing tier governs."""
    # unrealized $500, peak $500 → tier (750, 400) NOT crossed,
    # tier (400, 200) crossed → floor $200, $500 > $200, no close
    should, reason = pp.decide(unrealized=500.0, prev_peak=500.0)
    assert should is False


def test_decide_hard_gain_cap_when_explicitly_set():
    """Caller can still opt into a hard cap by passing gain_cap value."""
    should, reason = pp.decide(unrealized=500.0, prev_peak=500.0, gain_cap=400.0)
    assert should is True
    assert "hard_cap" in reason


def test_decide_hard_loss_cap_closes():
    """Unrealized <= -LOSS_TIER_HARD_CAP_USD -> close."""
    should, reason = pp.decide(unrealized=-200.0, prev_peak=50.0)
    assert should is True
    assert "loss_hard_cap" in reason


def test_decide_lowest_tier_breakeven_protection():
    """Peak crossed $30, current dropped below $0 (negative) -> close
    (the 'never let a gain become a loss' rule)."""
    should, reason = pp.decide(unrealized=-5.0, prev_peak=50.0)
    assert should is True
    assert "trailing_lock" in reason
    assert "$50" in reason  # peak shown
    assert "$30" in reason  # tier threshold


def test_decide_mid_tier_protection():
    """Peak crossed $150 (= floor $50). Current $40 < $50 -> close."""
    should, reason = pp.decide(unrealized=40.0, prev_peak=160.0)
    assert should is True
    assert "$50" in reason  # floor


def test_decide_peak_below_lowest_tier_no_lock():
    """Peak only reached $20 -- below the $30 tier threshold. No lock.
    Even if current drops to negative, no close (loss cap still applies)."""
    should, reason = pp.decide(unrealized=-10.0, prev_peak=20.0)
    assert should is False  # tier doesn't engage; loss cap not breached


def test_decide_picks_highest_active_tier():
    """If peak crosses multiple tiers, the tightest active tier applies.
    Peak $300 (crosses $250 -> floor $100). Current $80 < $100 -> close."""
    should, reason = pp.decide(unrealized=80.0, prev_peak=300.0)
    assert should is True
    assert "$100" in reason  # floor=$100 from peak>=$250 tier


def test_decide_above_active_floor_no_close():
    """Peak $300 (floor $100), current $120 > $100 -> no close yet."""
    should, reason = pp.decide(unrealized=120.0, prev_peak=300.0)
    assert should is False


# ── Runner-zone tiers (2026-05-11 expansion) ──────────────────

def test_decide_runner_tier_2500_locks_1500():
    """Peak $2700 crosses (2500, 1500) tier. Current $1400 < $1500 → close."""
    should, reason = pp.decide(unrealized=1400.0, prev_peak=2700.0)
    assert should is True
    assert "$1500" in reason  # floor


def test_decide_runner_tier_5000_locks_3000():
    """Peak $5500 crosses (5000, 3000) tier. Current $2900 < $3000 → close."""
    should, reason = pp.decide(unrealized=2900.0, prev_peak=5500.0)
    assert should is True
    assert "$3000" in reason


def test_decide_giant_winner_can_run():
    """Today's GC trade peaked at +$2,616. With current $2,000 (still
    >$1500 floor for the $2500 tier), no close — let it run."""
    should, reason = pp.decide(unrealized=2000.0, prev_peak=2616.0)
    assert should is False


def test_decide_giant_winner_closes_on_proper_retracement():
    """Same GC peak ($2616). Current drops to $1200 < $1500 → close
    on the (2500, 1500) tier. Tightest active floor wins even when
    multiple tiers are crossed."""
    should, reason = pp.decide(unrealized=1200.0, prev_peak=2616.0)
    assert should is True
    assert "$1500" in reason


# ── check_and_close() — end-to-end with fake broker ───────────

class _FakeBars:
    """Minimal bars stand-in: just exposes a Close series."""
    def __init__(self, prices):
        self._df = pd.DataFrame({"Close": prices})
    def __len__(self):
        return len(self._df)
    def __getitem__(self, key):
        return self._df[key]


class _FakeClient:
    def __init__(self, positions, bars_by_symbol):
        self._positions = positions
        self._bars = bars_by_symbol
        self.placed: list[dict] = []
    def get_positions(self, account_id):
        return self._positions
    def place_order(self, **kwargs):
        self.placed.append(kwargs)
        return {"orderId": 999}


def _fake_fetch(client, symbol, minutes, lookback):
    return client._bars.get(symbol)


def setup_function(_):
    """Reset high-water dict between tests so state doesn't leak."""
    pp._position_high_water.clear()


def test_check_and_close_no_positions_returns_empty():
    client = _FakeClient(positions=[], bars_by_symbol={})
    closed = pp.check_and_close(client, account_id=1, fetch_bars_fn=_fake_fetch)
    assert closed == []
    assert client.placed == []


def test_check_and_close_lets_big_winner_run():
    """2026-05-11: hard cap removed. GC long at 4750, now 4790 = +$4000.
    Without hard cap, position should NOT auto-close — trailing tier
    floor at $1500 is well below current. Let it run."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
                    "averagePrice": 4750.0}],
        bars_by_symbol={"GC": _FakeBars([4790.0])},
    )
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert closed == []  # no close: $4000 unrealized > $1500 floor
    assert client.placed == []
    # Peak captured for next-scan trailing logic
    assert pp._position_high_water.get("GC_long", 0) == pytest.approx(4000, abs=1)


def test_check_and_close_closes_runaway_after_retracement():
    """Same setup but two scans: first push to $4000 peak, then drop to
    $1000 — below the (2500, 1500) tier floor → close."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
                    "averagePrice": 4750.0}],
        bars_by_symbol={"GC": _FakeBars([4790.0])},  # +$4000
    )
    pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert pp._position_high_water["GC_long"] >= 3999
    client._bars["GC"] = _FakeBars([4760.0])  # +10 pts = +$1000
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert len(closed) == 1
    assert closed[0]["unrealized"] <= 1100
    assert "trailing_lock" in closed[0]["reason"]
    assert client.placed[0]["order_type"] == "market"


def test_check_and_close_locks_breakeven_after_30_peak():
    """Sim two calls: first push unrealized to +$50 (peak captured),
    then drop to -$5 -> trailing lock fires (never let gain become loss).

    GC tick=0.10, tick_value=$10. +5 ticks = +$50. So bar 4750.5 = +$50."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.GCE.M26", "size": 1, "type": 1,
                    "averagePrice": 4750.0}],
        bars_by_symbol={"GC": _FakeBars([4750.5])},  # +0.5 pts = +5 ticks = +$50
    )
    # First check: peak captured, no close
    pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert client.placed == []
    # Second check: price drops to -$5 -> close
    client._bars["GC"] = _FakeBars([4749.95])  # -0.05 pts = -0.5 ticks = -$5
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert len(closed) == 1
    assert "trailing_lock" in closed[0]["reason"]


def test_check_and_close_short_position_math():
    """Short MNQ: avg 29500, now 29490 = +10 pts profit on short. With MNQ
    tick=0.25 value=$0.50: 40 ticks × $0.50 = +$20. Below $30 tier so no
    close yet but high-water captured correctly."""
    client = _FakeClient(
        positions=[{"contractId": "CON.F.US.MNQ.M26", "size": 1, "type": 2,
                    "averagePrice": 29500.0}],
        bars_by_symbol={"MNQ": _FakeBars([29490.0])},
    )
    closed = pp.check_and_close(client, 1, fetch_bars_fn=_fake_fetch)
    assert closed == []
    # Peak captured
    assert pp._position_high_water.get("MNQ_short", 0) == pytest.approx(20.0, abs=0.01)
