"""Read vault/_meta/weekly_calendar.md, find items due in the next
7 days with status: open, post a Discord summary.

Wired as FundWeeklyReminder scheduled task: Sat 09:00 ET.
"""
from __future__ import annotations

import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CALENDAR = PROJECT_ROOT / "vault" / "_meta" / "weekly_calendar.md"


def main() -> int:
    if not CALENDAR.exists():
        print(f"ERROR: {CALENDAR} not found")
        return 1
    text = CALENDAR.read_text(encoding="utf-8", errors="replace")

    now = datetime.now(tz=timezone.utc)
    horizon = now + timedelta(days=7)

    # Parse items like: `- [2026-05-23] [open] **title**`
    pattern = re.compile(
        r"-\s+\[(\d{4}-\d{2}-\d{2})(?:\s+\d+:\d+\s+ET)?\]\s+"
        r"\[(open|scheduled-task)\]\s+\*\*([^*]+)\*\*"
    )
    upcoming = []
    for m in pattern.finditer(text):
        date_str, status, title = m.group(1), m.group(2), m.group(3)
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        if status != "open":
            continue
        # Within 7 days from now (including today)
        if now.date() <= d.date() <= horizon.date():
            days_out = (d.date() - now.date()).days
            upcoming.append((d.date(), days_out, title.strip()))

    if not upcoming:
        print("No reminders due this week.")
        return 0

    upcoming.sort()
    print(f"Reminders due in next 7 days: {len(upcoming)}")
    lines = [f":calendar_spiral: Weekly reminder ({len(upcoming)} item{'s' if len(upcoming) > 1 else ''} due in next 7 days)"]
    for date, days_out, title in upcoming:
        when = "TODAY" if days_out == 0 else f"in {days_out}d ({date.strftime('%a %m/%d')})"
        line = f"- **{when}**: {title[:120]}"
        lines.append(line)
        print(f"  {when}: {title}")
    lines.append(f"\nFull calendar: `vault/_meta/weekly_calendar.md`")

    # Post to Discord
    try:
        from tools.alert import send_alert
        send_alert("\n".join(lines), level="info")
        print("Discord alert sent.")
    except Exception as e:
        print(f"Discord send failed (non-fatal): {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
