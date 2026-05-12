"""Tests for tools/exec_mirror — the production-execution simulator.

Strategy: fabricate a small bar series and check qualitative properties
(outcome label, friction sign, friction-vs-no-friction delta) rather
than exact R-numbers, which depend on tick_value × distance arithmetic
that's easy to mis-count in test setup.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tools.exec_mirror import evaluate_exec_mirror
from tools.shadow_realism import slippage_cost_usd, fees_round_trip_usd
from tools.profit_protect import _TICK_ECONOMICS


def _bar(ts: datetime, h: float, l: float, c: float, o: float | None = None) -> dict:
    return {"t": ts.isoformat(), "h": h, "l": l, "c": c, "o": o if o is not None else c}


def _t(minutes: int = 0) -> datetime:
    """UTC test timestamp: 14:00 UTC = 09:00 CT (well before 3:10 PM CT)."""
    return datetime(2026, 5, 12, 14, 0, tzinfo=timezone.utc) + timedelta(minutes=minutes)


# ─── outcome correctness ───────────────────────────────────────

def test_stop_hit_outcome_long():
    bars = [
        _bar(_t(0), h=4001, l=3999, c=4000),    # entry tags
        _bar(_t(1), h=4000, l=3989, c=3990),    # stop hits at 3990
    ]
    outcome, _, _ = evaluate_exec_mirror(
        bars, symbol="GC", side="long", entry=4000, stop=3990, qty=1,
    )
    assert outcome == "stop_hit"


def test_stop_hit_outcome_short():
    bars = [
        _bar(_t(0), h=3.001, l=2.999, c=3.000),
        _bar(_t(1), h=3.021, l=3.000, c=3.020),
    ]
    outcome, _, _ = evaluate_exec_mirror(
        bars, symbol="NG", side="short", entry=3.000, stop=3.020, qty=1,
    )
    assert outcome == "stop_hit"


def test_no_fill_when_entry_never_tagged():
    bars = [
        _bar(_t(0), h=4005, l=4002, c=4003),
        _bar(_t(1), h=4006, l=4001, c=4004),
    ]
    outcome, pnl_r, _ = evaluate_exec_mirror(
        bars, symbol="GC", side="long", entry=4010, stop=4000, qty=1,
    )
    assert outcome == "no_fill"
    assert pnl_r == 0.0


def test_invalidated_when_entry_equals_stop():
    bars = [_bar(_t(0), h=4001, l=3999, c=4000)]
    outcome, _, _ = evaluate_exec_mirror(
        bars, symbol="GC", side="long", entry=4000, stop=4000, qty=1,
    )
    assert outcome == "invalidated"


def test_invalidated_for_unknown_symbol():
    bars = [_bar(_t(0), h=4001, l=3999, c=4000)]
    outcome, _, _ = evaluate_exec_mirror(
        bars, symbol="ZZZ", side="long", entry=4000, stop=3990, qty=1,
    )
    assert outcome == "invalidated"


# ─── friction sign & magnitude ─────────────────────────────────

def test_friction_reduces_stop_hit_R():
    """Friction must drive stop_hit R below -1.0 (it makes losers worse)."""
    bars = [
        _bar(_t(0), h=4001, l=3999, c=4000),
        _bar(_t(1), h=4000, l=3989, c=3990),
    ]
    _, gross_r, _ = evaluate_exec_mirror(
        bars, symbol="GC", side="long", entry=4000, stop=3990, qty=1,
        apply_friction=False,
    )
    _, net_r, _ = evaluate_exec_mirror(
        bars, symbol="GC", side="long", entry=4000, stop=3990, qty=1,
    )
    assert gross_r == -1.0
    assert net_r < gross_r, (
        f"friction must make stop_hit WORSE: gross={gross_r} net={net_r}")


def test_stop_slippage_is_additional_on_top_of_round_trip():
    """A stop_hit trade should be hit by BOTH round-trip slippage AND
    stop slippage; a non-stop trade should only see round-trip + fees."""
    bars_stop = [
        _bar(_t(0), h=4001, l=3999, c=4000),
        _bar(_t(1), h=4000, l=3989, c=3990),  # stop hits
    ]
    bars_lock = [
        _bar(_t(0), h=4001, l=3999, c=4000),
        _bar(_t(1), h=4006, l=4000, c=4005),  # peak ~$600 → tier engaged
        _bar(_t(2), h=4005, l=3995, c=3996),  # retrace into a tier floor
    ]
    _, r_stop, _ = evaluate_exec_mirror(
        bars_stop, symbol="GC", side="long", entry=4000, stop=3990,
        qty=1, risk_usd=1000.0,
    )
    _, r_stop_no_extra, _ = evaluate_exec_mirror(
        bars_stop, symbol="GC", side="long", entry=4000, stop=3990,
        qty=1, risk_usd=1000.0, stop_slippage_ticks=0.0,
    )
    # With stop slippage on (default 1.0t), R is lower (more negative) than
    # with stop_slippage_ticks=0.0.
    assert r_stop < r_stop_no_extra, (
        f"extra stop slippage must make R MORE negative: "
        f"with={r_stop} without={r_stop_no_extra}")


def test_friction_components_match_shadow_realism():
    """The friction $ subtracted by exec_mirror should equal the components
    from shadow_realism (round-trip slippage + fees) plus the explicit
    stop slippage on stop_hit outcomes."""
    bars = [
        _bar(_t(0), h=4001, l=3999, c=4000),
        _bar(_t(1), h=4000, l=3989, c=3990),
    ]
    risk_usd = 1000.0
    _, gross_r, _ = evaluate_exec_mirror(
        bars, symbol="GC", side="long", entry=4000, stop=3990,
        qty=1, risk_usd=risk_usd, apply_friction=False,
    )
    _, net_r, _ = evaluate_exec_mirror(
        bars, symbol="GC", side="long", entry=4000, stop=3990,
        qty=1, risk_usd=risk_usd,
    )
    expected_friction_usd = (
        slippage_cost_usd("GC")              # 1.5 ticks × $10 = $15
        + fees_round_trip_usd("GC")          # $5
        + 1.0 * _TICK_ECONOMICS["GC"][1]      # 1.0 tick × $10 = $10 stop slippage
    )
    actual_decay_usd = (gross_r - net_r) * risk_usd
    assert abs(actual_decay_usd - expected_friction_usd) < 0.01, (
        f"friction $ mismatch: expected={expected_friction_usd} "
        f"actual={actual_decay_usd}")
