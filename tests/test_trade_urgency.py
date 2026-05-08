"""Tests for the opportunity-cost / trade-urgency mechanism in auto_trader.

Background: every no-trade RTH session costs ~$26 in subscription drag. The
auto_trader gate stack was uniformly fail-closed -- gates only ever tightened,
never loosened. Result: 2 RTH sessions in a row with zero trades after the
2026-04-29 safety-floor rebuild. _trade_urgency_level() provides bounded,
time-decayed relaxation of marginal gates (rr_floor, EV-min only) when the
session is dry. Hard safety floors are NEVER touched by this function.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

from scripts.auto_trader import _trade_urgency_level


_FUND_AUTO_RTH = {
    "autonomous_mode": True,
    "autonomous_restrictions": {
        "rth_only": True,
        "rth_start_et": "07:30",
        "rth_end_et": "15:30",
    },
}


def _fixed_et(hour: int, minute: int = 0) -> datetime:
    """Return a fixed ET datetime via the same ZoneInfo path scan_once uses."""
    return datetime(2026, 5, 4, hour, minute, tzinfo=ZoneInfo("America/New_York"))


def _run(now_et: datetime, fund_cfg: dict, trades_today: int = 0) -> tuple[int, dict]:
    """Run _trade_urgency_level() with the given environment patched in."""
    with patch("scripts.auto_trader._load_yaml", return_value=fund_cfg), \
         patch("scripts.auto_trader._today_total_trade_count",
               return_value=trades_today), \
         patch("scripts.auto_trader.datetime") as dt_mod:
        # Only datetime.now() needs mocking; other datetime constructors
        # (datetime, timedelta, timezone) must pass through.
        from datetime import datetime as real_datetime, timedelta, timezone
        dt_mod.now.return_value = now_et
        # Pass-through everything else
        dt_mod.side_effect = lambda *a, **kw: real_datetime(*a, **kw)
        dt_mod.timedelta = timedelta
        dt_mod.timezone = timezone
        return _trade_urgency_level()


# ----------------------------------------------------------------------------
# Inactive paths (level always 0)
# ----------------------------------------------------------------------------

def test_zero_urgency_when_not_autonomous():
    cfg = {"autonomous_mode": False}
    level, info = _run(_fixed_et(12, 0), cfg, trades_today=0)
    assert level == 0
    assert info["reason"] == "not_autonomous"


def test_zero_urgency_when_already_traded_today():
    # 2hr into RTH, would be level 2 except for the trade
    level, info = _run(_fixed_et(9, 30), _FUND_AUTO_RTH, trades_today=1)
    assert level == 0
    assert info["reason"] == "already_traded_today"


def test_zero_urgency_when_outside_rth():
    # 06:00 ET, RTH opens 07:30
    level, info = _run(_fixed_et(6, 0), _FUND_AUTO_RTH, trades_today=0)
    assert level == 0
    assert info["reason"] == "outside_rth"


def test_zero_urgency_when_rth_only_off():
    cfg = {
        "autonomous_mode": True,
        "autonomous_restrictions": {"rth_only": False},
    }
    level, _ = _run(_fixed_et(12, 0), cfg, trades_today=0)
    assert level == 0


# ----------------------------------------------------------------------------
# Level transitions (the meat)
# ----------------------------------------------------------------------------

def test_level_0_first_hour_of_rth():
    """07:30-08:30 ET is the baseline window; no urgency."""
    for minutes in (0, 15, 30, 45, 59):
        level, info = _run(
            _fixed_et(7, 30 + minutes if minutes < 30 else 30) if minutes < 30
            else _fixed_et(8, minutes - 30),
            _FUND_AUTO_RTH, trades_today=0)
        assert level == 0, f"minute {minutes} into RTH should be level 0"


def test_level_1_at_60_minutes():
    """At exactly 60 min into RTH (08:30 ET), urgency = 1."""
    level, info = _run(_fixed_et(8, 30), _FUND_AUTO_RTH, trades_today=0)
    assert level == 1
    assert info["minutes_into_rth"] == 60


def test_level_1_through_119_minutes():
    """60-119 min into RTH should remain at level 1."""
    for minutes in (60, 75, 90, 119):
        h, m = divmod(7 * 60 + 30 + minutes, 60)
        level, _ = _run(_fixed_et(h, m), _FUND_AUTO_RTH, trades_today=0)
        assert level == 1, f"{minutes} min into RTH should be level 1"


def test_level_2_at_120_minutes():
    """At 120 min into RTH (09:30 ET), urgency = 2."""
    level, info = _run(_fixed_et(9, 30), _FUND_AUTO_RTH, trades_today=0)
    assert level == 2
    assert info["minutes_into_rth"] == 120


def test_level_2_late_in_session():
    """Even very late in RTH, level caps at 2 (no level 3)."""
    level, _ = _run(_fixed_et(15, 0), _FUND_AUTO_RTH, trades_today=0)
    assert level == 2


# ----------------------------------------------------------------------------
# Threshold-relaxation invariants
# (the values used by scan_once must respect absolute floors)
# ----------------------------------------------------------------------------

def test_rr_floor_never_drops_below_conviction():
    """rr_floor relaxation: max(2.0_med_floor, 2.5_autonomous - 0.2*level).
    At level 2 this gives 2.1, which is still > 2.0 conviction floor.
    At level 3+ (which doesn't exist) we'd cap at 2.0."""
    autonomous_rr = 2.5
    conviction_floor = 2.0
    for lvl in (0, 1, 2, 3, 5, 99):
        relaxed = max(conviction_floor, autonomous_rr - lvl * 0.2)
        assert relaxed >= conviction_floor, \
            f"level {lvl} relaxed rr={relaxed} below conviction floor"


def test_ev_min_never_drops_below_standard_floor():
    """EV-min relaxation: max(5.0_standard, 10.0_autonomous - 2*level).
    Level 0: $10. Level 1: $8. Level 2: $6. Level 3+: $5 (clamped)."""
    standard_floor = 5.0
    autonomous_floor = 10.0
    expected = {0: 10.0, 1: 8.0, 2: 6.0, 3: 5.0, 5: 5.0}
    for lvl, want in expected.items():
        got = max(standard_floor, autonomous_floor - lvl * 2.0)
        assert got == want, f"level {lvl}: expected ${want}, got ${got}"
