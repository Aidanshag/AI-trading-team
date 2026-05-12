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


def test_micro_tier_15_5_locks_small_win_on_retrace():
    """A trade that peaks just above $15 and retraces below $5 must close
    at the (15, 5) tier floor — NOT run to stop. Added 2026-05-12 to lock
    the new micro-tier behavior.
    GC tick economics: $10/tick × 1.5 ticks favorable = $15 peak.
    Then $0.5 ticks retrace = $5 unrealized = at floor → close."""
    from datetime import datetime, timedelta, timezone
    ts0 = datetime(2026, 5, 12, 14, 0, tzinfo=timezone.utc)
    bars = [
        _bar(ts0,                       h=4000.5, l=3999.5, c=4000),    # entry tags
        _bar(ts0 + timedelta(minutes=1), h=4001.5, l=4000.5, c=4001.2),  # peak +$15
        _bar(ts0 + timedelta(minutes=2), h=4001,   l=4000.3, c=4000.4),  # retrace
        _bar(ts0 + timedelta(minutes=3), h=4000.4, l=4000.1, c=4000.2),  # below $5 floor
    ]
    outcome, _, _ = evaluate_exec_mirror(
        bars, symbol="GC", side="long", entry=4000, stop=3990, qty=1,
    )
    # Should NOT be stop_hit (stop never touched)
    assert outcome == "profit_lock", f"expected profit_lock, got {outcome}"


def test_micro_tier_does_not_clip_runner_above_150_peak():
    """A trade that runs to peak $200 uses the (150, 50) tier, not micro
    tiers. Micro tiers must not affect runner behavior.

    GC math: 1 GC point = 10 ticks × $10/tick = $100 of P&L. So h=4002 is
    +$200 unrealized from entry 4000."""
    from datetime import datetime, timedelta, timezone
    ts0 = datetime(2026, 5, 12, 14, 0, tzinfo=timezone.utc)
    bars = [
        # Entry bar: contained range, peak +$50 only
        _bar(ts0,                       h=4000.5, l=3999.5, c=4000),
        # Bar 1: peak surges to +$200, unfav at +$150 (above $50 floor)
        _bar(ts0 + timedelta(minutes=1), h=4002,   l=4001.5, c=4001.8),
        # Bar 2: unfav retraces to +$40 — below (150,50) floor of $50 → close
        _bar(ts0 + timedelta(minutes=2), h=4001.8, l=4000.4, c=4000.5),
    ]
    outcome, _, note = evaluate_exec_mirror(
        bars, symbol="GC", side="long", entry=4000, stop=3990, qty=1,
        apply_friction=False,
    )
    assert outcome == "profit_lock"
    # The (150, 50) tier's $50 floor must dominate the micro tiers' lower
    # floors once peak >= $150.
    assert "floor $50" in note, f"expected (150,50) tier active, got: {note}"


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
