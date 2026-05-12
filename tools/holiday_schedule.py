"""CME holiday + abbreviated-session schedule for Topstep enforcement.

Topstep abbreviates trading hours on some holidays. Holding positions past
the abbreviated close = same rule violation as past 3:10 PM CT on a normal
day. This module:

  1. Maintains a static schedule of known US holidays + abbreviated CME hours
  2. Returns the effective `hard_flatten_time_ct` for any given date
  3. Exposes `is_holiday(date)` for skip-trading-entirely decisions

Source: CME Group holiday schedule (manually curated, verify yearly at
https://www.cmegroup.com/tools-information/holiday-calendar.html).

2026-05-12: built per Topstep Combine rules requirement.
"""
from __future__ import annotations

from datetime import date, time
from typing import NamedTuple


class HolidayRule(NamedTuple):
    """Per-date override for trading hours."""
    closed: bool                # True = NO trading session at all
    abbreviated_close_ct: time | None  # If session abbreviated, closes here CT


# ── CME / Topstep holiday schedule (2026) ───────────────────────
# Sourced from CMEGroup.com/holiday-calendar — UPDATE EACH YEAR.
# When `closed=True`, do not trade at all. When `abbreviated_close_ct` is
# set, hard-flatten at that time CT instead of the normal 15:10 CT.

_HOLIDAY_SCHEDULE_2026: dict[date, HolidayRule] = {
    # New Year's Day observed
    date(2026, 1, 1):  HolidayRule(closed=True, abbreviated_close_ct=None),
    # MLK Day — equities holiday but futures usually trade abbreviated
    date(2026, 1, 19): HolidayRule(closed=False, abbreviated_close_ct=time(12, 0)),
    # Presidents Day — same pattern
    date(2026, 2, 16): HolidayRule(closed=False, abbreviated_close_ct=time(12, 0)),
    # Good Friday — most markets closed
    date(2026, 4, 3):  HolidayRule(closed=True, abbreviated_close_ct=None),
    # Memorial Day
    date(2026, 5, 25): HolidayRule(closed=False, abbreviated_close_ct=time(12, 0)),
    # Independence Day observed
    date(2026, 7, 3):  HolidayRule(closed=False, abbreviated_close_ct=time(12, 0)),
    # Labor Day
    date(2026, 9, 7):  HolidayRule(closed=False, abbreviated_close_ct=time(12, 0)),
    # Thanksgiving
    date(2026, 11, 26): HolidayRule(closed=True, abbreviated_close_ct=None),
    # Day after Thanksgiving — abbreviated
    date(2026, 11, 27): HolidayRule(closed=False, abbreviated_close_ct=time(12, 15)),
    # Christmas Eve
    date(2026, 12, 24): HolidayRule(closed=False, abbreviated_close_ct=time(12, 15)),
    # Christmas Day
    date(2026, 12, 25): HolidayRule(closed=True, abbreviated_close_ct=None),
    # New Year's Eve
    date(2026, 12, 31): HolidayRule(closed=False, abbreviated_close_ct=time(12, 15)),
}


def rule_for_date(d: date) -> HolidayRule | None:
    """Return the holiday rule for `d`, or None if it's a normal trading day."""
    return _HOLIDAY_SCHEDULE_2026.get(d)


def is_holiday(d: date) -> bool:
    """Is this a CME holiday (closed or abbreviated)?"""
    return d in _HOLIDAY_SCHEDULE_2026


def is_fully_closed(d: date) -> bool:
    """Is this a full-close holiday (no trading at all)?"""
    rule = rule_for_date(d)
    return rule is not None and rule.closed


def hard_flatten_time_ct(d: date, default_time_ct: time = time(15, 10)) -> time:
    """Effective hard-flatten time CT for a given date. Normal days return
    the default 3:10 PM CT. Abbreviated holidays return their earlier close.
    Fully-closed days return midnight (since we shouldn't be trading anyway)."""
    rule = rule_for_date(d)
    if rule is None:
        return default_time_ct
    if rule.closed:
        return time(0, 1)   # treat as "deadline already past" — flatten immediately
    if rule.abbreviated_close_ct is not None:
        return rule.abbreviated_close_ct
    return default_time_ct


def hard_flatten_time_minus_5min(d: date) -> time:
    """Proactive flatten time = hard close minus 5 min. Used by the trader's
    proactive flatten window."""
    t = hard_flatten_time_ct(d)
    hr = t.hour
    mn = t.minute - 5
    if mn < 0:
        mn += 60
        hr -= 1
    if hr < 0:
        return time(0, 0)  # very early morning — treat as immediate
    return time(hr, mn)
