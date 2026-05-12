"""Tests for tools/holiday_schedule + holiday integration with hard_flatten_clock."""
from __future__ import annotations

from datetime import date, datetime, time

from tools import holiday_schedule as hs
from tools import hard_flatten_clock as hfc


def _ct(year, month, day, hh, mm) -> datetime:
    try:
        from zoneinfo import ZoneInfo
        return datetime(year, month, day, hh, mm, tzinfo=ZoneInfo("America/Chicago"))
    except Exception:
        from datetime import timezone, timedelta
        return datetime(year, month, day, hh, mm, tzinfo=timezone(timedelta(hours=-5)))


# ── holiday_schedule basics ─────────────────────────────────────

def test_memorial_day_2026_is_abbreviated():
    """Memorial Day 2026-05-25: abbreviated close at 12:00 CT."""
    rule = hs.rule_for_date(date(2026, 5, 25))
    assert rule is not None
    assert rule.closed is False
    assert rule.abbreviated_close_ct == time(12, 0)


def test_christmas_day_is_closed():
    """Christmas Day: full close, no trading."""
    rule = hs.rule_for_date(date(2026, 12, 25))
    assert rule is not None
    assert rule.closed is True
    assert hs.is_fully_closed(date(2026, 12, 25))


def test_normal_day_has_no_rule():
    """Random Tuesday: no holiday rule."""
    assert hs.rule_for_date(date(2026, 5, 12)) is None
    assert hs.is_holiday(date(2026, 5, 12)) is False


def test_hard_flatten_time_normal_day():
    """Normal day → default 3:10 PM CT."""
    assert hs.hard_flatten_time_ct(date(2026, 5, 12)) == time(15, 10)


def test_hard_flatten_time_abbreviated_day():
    """Memorial Day → 12:00 CT close."""
    assert hs.hard_flatten_time_ct(date(2026, 5, 25)) == time(12, 0)


def test_hard_flatten_time_full_close_day():
    """Christmas → ~midnight (immediate flatten if trading at all)."""
    assert hs.hard_flatten_time_ct(date(2026, 12, 25)) == time(0, 1)


# ── hard_flatten_clock holiday integration ─────────────────────

def test_clock_recognizes_memorial_day_abbreviated_close():
    """Memorial Day 2026 11:40 CT → normal (before block window).
    11:45 CT → no_new_entries (10 min before 12:00 close).
    11:55 CT → flatten (5 min before close).
    12:01 CT → past_deadline."""
    md = lambda h, m: _ct(2026, 5, 25, h, m)
    assert hfc.current_window(md(11, 40)) == "normal"
    assert hfc.current_window(md(11, 45)) == "no_new_entries"
    assert hfc.current_window(md(11, 55)) == "flatten"
    assert hfc.current_window(md(12, 1)) == "past_deadline"


def test_clock_normal_window_unchanged_on_normal_day():
    """Normal weekday → 15:10 close, 14:55 block."""
    nd = lambda h, m: _ct(2026, 5, 12, h, m)  # 5/12 = normal Tuesday
    assert hfc.current_window(nd(14, 54)) == "normal"
    assert hfc.current_window(nd(14, 55)) == "no_new_entries"
    assert hfc.current_window(nd(15, 5)) == "flatten"
    assert hfc.current_window(nd(15, 10)) == "past_deadline"


def test_clock_full_close_day_always_flatten():
    """Christmas: closed=True → 'flatten' all day (don't trade)."""
    cd = lambda h, m: _ct(2026, 12, 25, h, m)
    assert hfc.current_window(cd(10, 0)) == "flatten"
    assert hfc.current_window(cd(14, 0)) == "flatten"
    assert hfc.current_window(cd(19, 0)) == "flatten"
