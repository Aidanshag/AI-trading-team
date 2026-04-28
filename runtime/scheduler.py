"""Market-hours scheduler.

Emits SESSION_OPEN, SESSION_CLOSE, and periodic TICK events based on each
symbol's trading session. Designed to be event-driven, not polling — idle
when no relevant session is active.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, time, timezone
from pathlib import Path
from typing import AsyncIterator
from zoneinfo import ZoneInfo

import yaml

from .events import Event, EventKind

# CME near-24h session: open Sun 17:00 CT, close Fri 16:00 CT, daily 45-min
# break typically 16:00–17:00 CT. This is a simplification — real-world
# session calendars differ per product family (Globex vs RTH, softs, etc).
CT = ZoneInfo("America/Chicago")
DAILY_BREAK_START = time(16, 0)
DAILY_BREAK_END = time(17, 0)


class Scheduler:
    def __init__(self, tick_minutes: int = 15) -> None:
        self.tick_minutes = tick_minutes

    def is_cme_open_now(self, now: datetime | None = None) -> bool:
        now = (now or datetime.now(tz=CT)).astimezone(CT)
        wday = now.weekday()  # Mon=0 .. Sun=6
        t = now.time()
        # Sunday: open at 17:00 CT
        if wday == 6:
            return t >= time(17, 0)
        # Friday: close at 16:00 CT
        if wday == 4:
            return t < time(16, 0)
        # Saturday: closed
        if wday == 5:
            return False
        # Mon–Thu: open except the daily break 16:00–17:00
        return not (DAILY_BREAK_START <= t < DAILY_BREAK_END)

    async def run(self) -> AsyncIterator[Event]:
        """Yield session + tick events forever. Caller decides when to stop."""
        last_open_state = None
        last_stress_date: str | None = None
        last_metrics_date: str | None = None

        while True:
            open_now = self.is_cme_open_now()
            now_ct = datetime.now(tz=CT)
            today = now_ct.strftime("%Y-%m-%d")

            if last_open_state is None:
                last_open_state = open_now
                if open_now:
                    yield Event(kind=EventKind.SESSION_OPEN, source="scheduler")
            elif open_now != last_open_state:
                yield Event(
                    kind=EventKind.SESSION_OPEN if open_now else EventKind.SESSION_CLOSE,
                    source="scheduler",
                )
                last_open_state = open_now

            # 06:00 CT daily — stress test event (only once per day)
            if (
                now_ct.time() >= time(6, 0)
                and now_ct.time() < time(6, 30)
                and last_stress_date != today
            ):
                yield Event(kind=EventKind.STRESS_TEST_DUE, source="scheduler")
                last_stress_date = today

            # 17:00 CT daily — Compliance metrics sweep (post-close)
            if (
                now_ct.time() >= time(17, 0)
                and now_ct.time() < time(17, 30)
                and last_metrics_date != today
            ):
                yield Event(kind=EventKind.DAILY_METRICS_DUE, source="scheduler")
                last_metrics_date = today

            if open_now:
                yield Event(kind=EventKind.TICK, source="scheduler")
            else:
                # Markets closed: emit IDLE_TICK so off-hours work can fire
                # (Fund Engineer brain-building, weekly review prep, etc).
                # The orchestrator gates this on config/fund.yaml:idle_work_enabled.
                yield Event(kind=EventKind.IDLE_TICK, source="scheduler")

            await asyncio.sleep(self.tick_minutes * 60)
