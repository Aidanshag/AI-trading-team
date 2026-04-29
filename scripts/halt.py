"""Single-command kill switch.

Usage:
    python -m scripts.halt 4h          # halt for 4 hours
    python -m scripts.halt 30m         # 30 minutes
    python -m scripts.halt next-open   # halt until ~next session open
    python -m scripts.halt clear       # clear halt (set timestamp to past)
    python -m scripts.halt status      # show current halt state

Edits config/risk_limits.yaml:hard_rules.trading_halt_until in place.
The risk hook reads this on every order — halts take effect immediately.

This is intended for both manual use ("I'm worried about overnight") and
for the autonomous safety nets (consecutive_loser_pause, agent_cascade_halt)
that already write the same field via auto_trader._engage_auto_halt.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)


def _parse_duration(s: str) -> timedelta | None:
    """Parse '4h', '30m', '2d', '90s' — case insensitive."""
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([smhd])\s*", s.lower())
    if not m:
        return None
    n = float(m.group(1))
    unit = m.group(2)
    return {
        "s": timedelta(seconds=n),
        "m": timedelta(minutes=n),
        "h": timedelta(hours=n),
        "d": timedelta(days=n),
    }[unit]


def _next_session_open_utc() -> datetime:
    """Next 06:30 ET (cash equity open) in UTC. Approximation — Globex
    actually runs through most of the night, but 06:30 ET is when the team
    usually starts."""
    from zoneinfo import ZoneInfo
    et = ZoneInfo("America/New_York")
    now_et = datetime.now(tz=et)
    target = now_et.replace(hour=6, minute=30, second=0, microsecond=0)
    if target <= now_et:
        target = target + timedelta(days=1)
    # Skip weekends — if target is Saturday/Sunday, push to Monday
    while target.weekday() >= 5:
        target = target + timedelta(days=1)
    return target.astimezone(timezone.utc)


def _write_halt(when_utc: datetime, *, reason: str) -> None:
    """Targeted text-only edit of the trading_halt_until line.

    Why text edit and not yaml.safe_dump: yaml.safe_dump strips ALL comments
    from the file, which destroys hand-curated explanations. The risk_limits
    YAML has hundreds of lines of explanation we never want to lose. So we
    do a regex match on the single line and rewrite ONLY that line.
    """
    path = Path("config/risk_limits.yaml")
    iso = when_utc.isoformat(timespec="seconds").replace("+00:00", "Z")
    text = path.read_text()
    # Match either `trading_halt_until: "..."`, `trading_halt_until: '...'`,
    # or `trading_halt_until: <unquoted>` followed by optional comment
    new_text, n = re.subn(
        r"(^[ \t]*trading_halt_until:[ \t]*)(?:\"[^\"]*\"|'[^']*'|\S+)([ \t]*(?:#.*)?)$",
        rf'\g<1>"{iso}"\g<2>',
        text, count=1, flags=re.MULTILINE,
    )
    if n != 1:
        # Fallback: if the line shape is unexpected, refuse to write rather
        # than corrupt the file. User can fix the YAML by hand.
        print(f"ERROR: could not find trading_halt_until in {path}. "
              f"Edit the file by hand and re-run.", file=sys.stderr)
        sys.exit(2)
    path.write_text(new_text)
    # Log to decisions table
    try:
        from state.db import get_db
        get_db().record_decision(
            agent="orchestrator", kind="manual_halt",
            summary=f"Halt set until {iso}",
            rationale=f"Reason: {reason}", model="cli",
        )
    except Exception:
        pass
    print(f"Halt set: trading_halt_until = {iso}")


def _show_status() -> int:
    path = Path("config/risk_limits.yaml")
    cfg = yaml.safe_load(path.read_text())
    halt = (cfg.get("hard_rules") or {}).get("trading_halt_until")
    halted_flag = (cfg.get("hard_rules") or {}).get("trading_halted")
    print(f"trading_halted (manual flag): {halted_flag}")
    print(f"trading_halt_until: {halt}")
    if halt:
        try:
            t = datetime.fromisoformat(str(halt).replace("Z", "+00:00"))
            now = datetime.now(tz=timezone.utc)
            if t > now:
                delta_h = (t - now).total_seconds() / 3600
                print(f"  -> halted, expires in {delta_h:+.1f} hours")
            else:
                delta_h = (now - t).total_seconds() / 3600
                print(f"  -> halt expired {delta_h:.1f} hours ago (trading allowed)")
        except Exception as e:
            print(f"  -> unparseable: {e}")
    return 0


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    arg = argv[0].strip()

    if arg in ("status", "show"):
        return _show_status()

    if arg in ("clear", "resume", "off"):
        # Set halt to a past timestamp
        _write_halt(datetime(2024, 1, 1, tzinfo=timezone.utc),
                    reason="manual clear")
        return 0

    if arg == "next-open":
        when = _next_session_open_utc()
        _write_halt(when, reason="halt until next session open")
        return 0

    delta = _parse_duration(arg)
    if delta is None:
        print(f"Cannot parse duration {arg!r}. Examples: 4h, 30m, 90s, 2d, "
              f"or 'next-open', 'clear', 'status'.", file=sys.stderr)
        return 2
    when = datetime.now(tz=timezone.utc) + delta
    reason = " ".join(argv[1:]) if len(argv) > 1 else f"manual halt {arg}"
    _write_halt(when, reason=reason)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
