"""Fetch the Federal Reserve speaker / event calendar for the upcoming
window. Writes a structured calendar file that the high-impact blackout
gate (and macro brief generator) can consume.

Why: front-end Treasury futures (ZT, ZF) react sharply to Fed speaker
language. The current high-impact-blackout gate handles the obvious
data prints (NFP, CPI, FOMC) but doesn't track Fed speaker schedules.
Adding a speaker calendar to the gate widens its coverage to include
the kind of intraday news flow that turns gap_fill fades into losers.

Data source: federalreserve.gov publishes an iCalendar (.ics) feed of
events — no API key required. We parse the .ics directly.

Speakers are tagged by influence tier:
  HIGH    : Chair, vice chair, NY Fed president
  MEDIUM  : Voting governors and regional presidents
  LOW     : Non-voting / governance events / staff appearances

Writes:
  vault/economic_calendar/fed_speakers.json
  vault/economic_calendar/fed_speakers.md

USAGE:
  python -m scripts.fetch_fed_speakers
  python -m scripts.fetch_fed_speakers --days 14
  python -m scripts.fetch_fed_speakers --print
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)

# Federal Reserve master events ICS feed (verify URL — Fed has historically
# served at least an HTML calendar. If the .ics endpoint isn't available,
# fall back to scraping the HTML calendar.)
FED_ICS_URL = "https://www.federalreserve.gov/calendar/feed.ics"
FED_HTML_CAL = "https://www.federalreserve.gov/newsevents/calendar.htm"

# Influence tiers — extended over time as we learn which speakers move
# the front-end most.
HIGH_INFLUENCE_NAMES = {
    "powell",          # Chair
    "jefferson",       # Vice Chair (verify role at runtime)
    "williams",        # NY Fed President
}
MEDIUM_INFLUENCE_KEYWORDS = (
    "governor", "president", "vice chair",
)


def fetch_ics() -> str:
    r = requests.get(FED_ICS_URL, timeout=30,
                     headers={"User-Agent": "ai-trading-fund/1.0"})
    r.raise_for_status()
    return r.text


def parse_ics(text: str) -> list[dict]:
    """Minimal iCalendar parser — pulls VEVENT blocks with SUMMARY,
    DTSTART, DTEND, DESCRIPTION, LOCATION."""
    events: list[dict] = []
    current: dict | None = None
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current is not None:
                events.append(current)
                current = None
        elif current is not None and ":" in line:
            key, _, val = line.partition(":")
            key = key.split(";")[0]  # drop param like DTSTART;TZID=America/New_York
            current[key] = val
    return events


def classify_influence(summary: str, description: str) -> str:
    blob = (summary + " " + description).lower()
    for name in HIGH_INFLUENCE_NAMES:
        if name in blob:
            return "HIGH"
    for kw in MEDIUM_INFLUENCE_KEYWORDS:
        if kw in blob:
            return "MEDIUM"
    return "LOW"


def _parse_dtstart(s: str) -> datetime | None:
    if not s:
        return None
    # Accepts: 20260507T133000Z, 20260507T133000, 20260507
    s = s.replace(":", "").replace("-", "")
    try:
        if s.endswith("Z"):
            return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        if "T" in s:
            return datetime.strptime(s, "%Y%m%dT%H%M%S")
        return datetime.strptime(s, "%Y%m%d")
    except Exception:
        return None


def filter_and_normalize(events: list[dict], days: int) -> list[dict]:
    today = datetime.now(tz=timezone.utc)
    cutoff = today + timedelta(days=days)
    out: list[dict] = []
    for e in events:
        dt = _parse_dtstart(e.get("DTSTART", ""))
        if dt is None:
            continue
        # Make tz-aware if not already (assume UTC)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        if not (today <= dt <= cutoff):
            continue
        summary = e.get("SUMMARY", "").strip()
        description = e.get("DESCRIPTION", "").strip()
        influence = classify_influence(summary, description)
        out.append({
            "ts_utc": dt.isoformat(),
            "summary": summary,
            "description": description[:300],
            "location": e.get("LOCATION", ""),
            "influence": influence,
        })
    out.sort(key=lambda x: x["ts_utc"])
    return out


def write_outputs(records: list[dict]) -> None:
    out_dir = _HERE / "vault" / "economic_calendar"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "fed_speakers.json"
    md_path = out_dir / "fed_speakers.md"

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": FED_ICS_URL,
        "events": records,
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    L = ["---", "type: fed_speaker_calendar",
         f"generated_at: {payload['generated_at']}",
         f"count: {len(records)}",
         "---", "",
         "# Fed speakers / events — upcoming",
         "",
         "HIGH-influence speakers (Chair, Vice Chair, NY Fed) move the "
         "front end of the curve sharply. Front-end gap_fill cells (ZT, "
         "ZF) should respect a ±30min blackout around HIGH events.",
         "",
         "| When (UTC) | Influence | Summary | Location |",
         "|---|---|---|---|"]
    for r in records:
        L.append(f"| {r['ts_utc']} | {r['influence']} | {r['summary']} "
                 f"| {r['location']} |")
    md_path.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"Wrote {json_path.relative_to(_HERE)}")
    print(f"Wrote {md_path.relative_to(_HERE)}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--days", type=int, default=14)
    p.add_argument("--print", dest="do_print", action="store_true")
    args = p.parse_args()

    try:
        text = fetch_ics()
    except Exception as e:
        print(f"ERROR: failed to fetch Fed ICS: {e}", file=sys.stderr)
        print(f"Falling back: HTML page at {FED_HTML_CAL} (parser not yet "
              f"implemented — add when needed).", file=sys.stderr)
        return 2

    events = parse_ics(text)
    filtered = filter_and_normalize(events, args.days)
    print(f"Parsed {len(events)} events, kept {len(filtered)} in next {args.days} days.")
    write_outputs(filtered)

    if args.do_print:
        print()
        for r in filtered:
            print(f"  {r['ts_utc']}  [{r['influence']}]  {r['summary'][:80]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
