"""Build today's economic-event calendar.

Writes `vault/economic_calendar/today.json` — the file the high-impact
blackout in `hooks/risk_gate.py` reads to block trading around major
data releases.

Sources combined:
  1. RECURRING_PATTERNS — hardcoded periodic events (EIA Thursday,
     Jobless Claims Thursday, NFP first-Friday, etc.). Free, no API.
  2. config/economic_overrides.yaml — manually curated one-off events
     (FOMC dates, special speeches, FOMC minutes). User edits this file
     once a quarter when the BLS / FOMC release their schedules.

Output schema (matches what the risk hook expects):
  [{"ts_utc": "2026-04-30T12:30:00Z", "impact": "high",
    "event": "Initial Jobless Claims", "symbols_affected": ["ZN", "ES"]}]

Usage:
  python -m scripts.build_economic_calendar [--days 1]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml


CAL_DIR = Path("vault/economic_calendar")
OVERRIDES = Path("config/economic_overrides.yaml")
ET = ZoneInfo("America/New_York")
CT = ZoneInfo("America/Chicago")


def _et_to_utc(date: datetime, hh: int, mm: int) -> str:
    """Take a calendar date + ET time, return UTC ISO-8601 with Z suffix."""
    local = datetime.combine(date.date(), time(hh, mm), tzinfo=ET)
    return local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_business_day(d: datetime) -> bool:
    return d.weekday() < 5


def _first_business_day_of_month(d: datetime) -> datetime:
    cand = d.replace(day=1)
    while not _is_business_day(cand):
        cand += timedelta(days=1)
    return cand


def _first_friday_of_month(d: datetime) -> datetime:
    """NFP — first Friday of month at 8:30 ET."""
    cand = d.replace(day=1)
    while cand.weekday() != 4:  # Friday
        cand += timedelta(days=1)
    return cand


def _events_for_date(d: datetime) -> list[dict]:
    """Recurring high-impact events that fall on date d."""
    events: list[dict] = []
    weekday = d.weekday()

    # Thursday 8:30 ET — Initial Jobless Claims (every week)
    if weekday == 3:
        events.append({
            "ts_utc": _et_to_utc(d, 8, 30),
            "impact": "high",
            "event": "Initial Jobless Claims",
            "symbols_affected": ["ZN", "ZB", "ES", "MES", "6E"],
        })
        # Thursday 10:30 ET — EIA Natural Gas Storage
        events.append({
            "ts_utc": _et_to_utc(d, 10, 30),
            "impact": "high",
            "event": "EIA Natural Gas Storage",
            "symbols_affected": ["NG", "MNG", "QG"],
        })

    # Wednesday 10:30 ET — EIA Crude Oil Inventory
    if weekday == 2:
        events.append({
            "ts_utc": _et_to_utc(d, 10, 30),
            "impact": "high",
            "event": "EIA Crude Oil Inventory",
            "symbols_affected": ["CL", "MCL", "QM", "RB", "HO"],
        })

    # First Friday of month, 8:30 ET — Nonfarm Payrolls (NFP)
    if d == _first_friday_of_month(d):
        events.append({
            "ts_utc": _et_to_utc(d, 8, 30),
            "impact": "high",
            "event": "Nonfarm Payrolls (NFP)",
            "symbols_affected": ["ZN", "ZB", "ES", "MES", "6E", "GC"],
        })

    # First business day of month, 10:00 ET — ISM Manufacturing
    if d == _first_business_day_of_month(d):
        events.append({
            "ts_utc": _et_to_utc(d, 10, 0),
            "impact": "high",
            "event": "ISM Manufacturing PMI",
            "symbols_affected": ["ES", "MES", "ZN"],
        })

    return events


def _load_overrides() -> list[dict]:
    if not OVERRIDES.exists():
        return []
    try:
        data = yaml.safe_load(OVERRIDES.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    return list(data.get("events", []) or [])


def build_for_date(d: datetime) -> list[dict]:
    """Return all high-impact events on calendar date d."""
    target_day = d.strftime("%Y-%m-%d")
    events = _events_for_date(d)
    for ov in _load_overrides():
        ts = str(ov.get("ts_utc", ""))
        if ts.startswith(target_day):
            events.append({
                "ts_utc": ts,
                "impact": ov.get("impact", "high"),
                "event": ov.get("event", "(unnamed override)"),
                "symbols_affected": ov.get("symbols_affected", []),
            })
    events.sort(key=lambda e: e["ts_utc"])
    return events


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=1,
                   help="how many days forward to generate (default 1)")
    p.add_argument("--quiet", action="store_true")
    args = p.parse_args()

    CAL_DIR.mkdir(parents=True, exist_ok=True)
    today = datetime.now(tz=timezone.utc)
    written: list[Path] = []
    for offset in range(args.days):
        d = today + timedelta(days=offset)
        events = build_for_date(d)
        # today.json always points to today; future days as YYYY-MM-DD.json
        if offset == 0:
            path = CAL_DIR / "today.json"
        else:
            path = CAL_DIR / f"{d.strftime('%Y-%m-%d')}.json"
        path.write_text(json.dumps(events, indent=2), encoding="utf-8")
        written.append(path)
        if not args.quiet:
            print(f"  {path} → {len(events)} event(s)")
            for ev in events:
                print(f"    {ev['ts_utc']:20s}  {ev['event']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
