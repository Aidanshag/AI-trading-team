"""Tests for scripts/validate_live_filter._classify — the per-cell verdict
logic that decides KEEP / GATHER / DROP."""
from __future__ import annotations

from scripts.validate_live_filter import _classify


def _cell(strategy="fvg", symbol="GC", session="Asian", side="long"):
    return {"strategy": strategy, "symbol": symbol,
            "session": session, "side": side}


# ─── GATHER (insufficient data) ────────────────────────────────

def test_gather_when_n_below_threshold():
    verdict, _ = _classify(
        _cell(), stats={"n": 5, "exec_avg_r": -2.0, "theo_avg_r": -1.0,
                         "avg_risk_usd": 100, "avg_rr": 1.5},
        min_n=15, min_exec_r=-0.30,
        min_target_usd=80.0, max_fric_frac=0.30,
    )
    assert verdict == "GATHER"


# ─── DROP cases ────────────────────────────────────────────────

def test_drop_negative_exec_avg_r():
    """Exec mean below floor with sufficient n must DROP."""
    verdict, reason = _classify(
        _cell(symbol="GC"),
        stats={"n": 50, "exec_avg_r": -0.45, "theo_avg_r": +0.20,
                "avg_risk_usd": 500, "avg_rr": 2.0},
        min_n=15, min_exec_r=-0.30,
        min_target_usd=80.0, max_fric_frac=0.30,
    )
    assert verdict == "DROP"
    assert "exec_avg_r" in reason


def test_drop_target_below_first_tier_floor():
    """If avg_rr * avg_risk_usd is below the first profit-lock tier floor
    AND exec is negative → DROP (structurally clipped)."""
    # GC with $30 risk × 2.5 RR = $75 target; below $80 floor
    verdict, reason = _classify(
        _cell(symbol="GC"),
        stats={"n": 50, "exec_avg_r": -0.10, "theo_avg_r": +0.30,
                "avg_risk_usd": 30, "avg_rr": 2.5},
        min_n=15, min_exec_r=-0.30,
        min_target_usd=80.0, max_fric_frac=0.30,
    )
    assert verdict == "DROP"
    assert "target=$75" in reason


def test_drop_friction_too_large_fraction_of_risk():
    """6E with 6.25 tick_value × 1.5 round-trip slip + $2.84 fees = $12.21.
    Against a $30 risk that's 41% → DROP. Use rr=3.0 so target=$90 passes
    the target-floor gate, isolating the friction check."""
    verdict, reason = _classify(
        _cell(symbol="6E"),
        stats={"n": 50, "exec_avg_r": -0.15, "theo_avg_r": +0.10,
                "avg_risk_usd": 30.0, "avg_rr": 3.0},
        min_n=15, min_exec_r=-0.30,
        min_target_usd=80.0, max_fric_frac=0.30,
    )
    assert verdict == "DROP"
    assert "friction" in reason, f"expected friction reason, got: {reason}"


# ─── KEEP cases ────────────────────────────────────────────────

def test_keep_when_exec_meets_floor_and_target_reasonable():
    verdict, reason = _classify(
        _cell(symbol="GC"),
        stats={"n": 50, "exec_avg_r": +0.10, "theo_avg_r": +0.30,
                "avg_risk_usd": 500, "avg_rr": 2.0},
        min_n=15, min_exec_r=-0.30,
        min_target_usd=80.0, max_fric_frac=0.30,
    )
    assert verdict == "KEEP"
    assert "+0.10R" in reason


def test_keep_at_exact_floor():
    """exec_avg_r == min_exec_r is not below the floor; must KEEP."""
    verdict, _ = _classify(
        _cell(symbol="GC"),
        stats={"n": 50, "exec_avg_r": -0.30, "theo_avg_r": +0.20,
                "avg_risk_usd": 500, "avg_rr": 2.0},
        min_n=15, min_exec_r=-0.30,
        min_target_usd=80.0, max_fric_frac=0.30,
    )
    assert verdict == "KEEP"


def test_keep_when_target_below_floor_but_exec_positive():
    """Small-target cell that nonetheless squeezes positive exec_r → KEEP.
    The target-below-floor gate only triggers in conjunction with
    negative exec — a profitable squeeze isn't structurally broken."""
    verdict, _ = _classify(
        _cell(symbol="MCL"),
        stats={"n": 50, "exec_avg_r": +0.20, "theo_avg_r": +0.30,
                "avg_risk_usd": 30, "avg_rr": 2.0},
        min_n=15, min_exec_r=-0.30,
        min_target_usd=80.0, max_fric_frac=0.30,
    )
    assert verdict == "KEEP"
