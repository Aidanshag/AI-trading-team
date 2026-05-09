"""Generate a structured session summary at end of Claude Code sessions.

Reads git activity in the last 24h (or since the last summary file) and
produces a markdown snapshot to `vault/sessions/<date>_session.md`.

Captures:
  - All commits in the session window with messages
  - Files added / modified
  - Memory entries that changed
  - Lesson files that changed
  - Today's trade activity from state/fund.db
  - Active live cells in the trader

The auto-commit Stop hook then pushes this file to git, where external
tools (Claude Cowork, future Claude sessions, etc.) can read it.

Run via:
  python scripts/session_summary.py             # write summary for today
  python scripts/session_summary.py --since 2h  # only last 2 hours
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = PROJECT_ROOT / "vault" / "sessions"


def git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args], cwd=str(PROJECT_ROOT),
            text=True, stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def commits_since(since_arg: str) -> list[dict]:
    """Get commits in the window. Returns list of {hash, ts, subject, files}."""
    out = git("log", f"--since={since_arg}",
              "--pretty=format:%H|%cI|%s", "--name-only")
    if not out:
        return []
    blocks = re.split(r"\n\n", out.strip())
    commits = []
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        first = lines[0]
        if "|" not in first:
            continue
        h, ts, subject = first.split("|", 2)
        files = [l for l in lines[1:] if l.strip()]
        commits.append({"hash": h[:8], "ts": ts, "subject": subject, "files": files})
    return commits


def trades_in_window(since: datetime) -> list[dict]:
    """Read trade activity from state/fund.db in the window."""
    db = PROJECT_ROOT / "state" / "fund.db"
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db))
    rows = conn.execute(
        "SELECT ts, symbol, summary FROM decisions "
        "WHERE kind='thesis' AND ts >= ? ORDER BY ts",
        (since.isoformat(timespec="seconds"),)
    ).fetchall()
    conn.close()
    return [{"ts": r[0], "symbol": r[1], "summary": r[2]} for r in rows]


def pl_in_window(since: datetime) -> dict:
    db = PROJECT_ROOT / "state" / "fund.db"
    if not db.exists():
        return {}
    conn = sqlite3.connect(str(db))
    first = conn.execute(
        "SELECT balance_usd, realized_pl_day_usd FROM account_snapshots "
        "WHERE ts >= ? ORDER BY ts ASC LIMIT 1",
        (since.isoformat(timespec="seconds"),)
    ).fetchone()
    last = conn.execute(
        "SELECT balance_usd, realized_pl_day_usd, ts FROM account_snapshots "
        "ORDER BY ts DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if not first or not last:
        return {}
    return {"balance_start": first[0], "balance_end": last[0],
            "realized_day_end": last[1], "ts_end": last[2]}


def active_live_cells() -> list[dict]:
    state_path = PROJECT_ROOT / "state" / "strategy_validation.json"
    if not state_path.exists():
        return []
    try:
        st = json.loads(state_path.read_text(encoding="utf-8"))
        return st.get("live_allowlist") or []
    except Exception:
        return []


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--since", default="24 hours ago",
                   help="Git --since argument (default '24 hours ago')")
    args = p.parse_args()

    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now(timezone.utc)
    today = now.strftime("%Y-%m-%d")

    # Compute the cutoff timestamp for trades / P&L
    if "hour" in args.since:
        n = int(args.since.split()[0])
        cutoff = now - timedelta(hours=n)
    elif "day" in args.since:
        n = int(args.since.split()[0])
        cutoff = now - timedelta(days=n)
    else:
        cutoff = now - timedelta(days=1)

    commits = commits_since(args.since)
    trades = trades_in_window(cutoff)
    pl = pl_in_window(cutoff)
    live_cells = active_live_cells()

    # Categorize commits by impact area (file paths)
    def categorize(files: list[str]) -> str:
        cats = set()
        for f in files:
            if f.startswith("scripts/") or f.startswith("tools/"):
                cats.add("code")
            elif f.startswith("config/"):
                cats.add("config")
            elif f.startswith("vault/lessons/"):
                cats.add("lesson")
            elif f.startswith("vault/research/"):
                cats.add("research")
            elif f.startswith("vault/_meta/memory_backup"):
                cats.add("memory")
            elif f.startswith("vault/"):
                cats.add("vault")
            elif f.startswith("hooks/") or f.startswith("runtime/"):
                cats.add("safety")
            elif f.startswith("tests/"):
                cats.add("tests")
            else:
                cats.add("other")
        return ", ".join(sorted(cats)) or "—"

    # Files that changed (deduped union)
    all_files: set[str] = set()
    for c in commits:
        all_files.update(c["files"])

    # Memory + lesson highlights
    memory_files = sorted(f for f in all_files
                           if f.startswith("vault/_meta/memory_backup/")
                           and f.endswith(".md"))
    lesson_files = sorted(f for f in all_files
                           if f.startswith("vault/lessons/")
                           and f.endswith(".md"))
    research_files = sorted(f for f in all_files
                             if f.startswith("vault/research/")
                             and f.endswith(".md"))

    # Build markdown
    out: list[str] = []
    out += ["---", "type: session_summary",
            f"date: {today}",
            f"window: since {args.since}",
            f"generated_at: {now.isoformat(timespec='seconds')}",
            f"commits: {len(commits)}",
            f"trades: {len(trades)}",
            "---", ""]
    out.append(f"# Session summary — {today}")
    out.append("")
    out.append(f"_Generated automatically. Window: {args.since}._")
    out.append("")

    # P&L bar
    if pl:
        delta = (pl.get("balance_end", 0) or 0) - (pl.get("balance_start", 0) or 0)
        out += ["## P&L over window", "",
                f"- Balance start: ${pl.get('balance_start', 0):,.2f}",
                f"- Balance end:   ${pl.get('balance_end', 0):,.2f}",
                f"- Δ window:      ${delta:+,.2f}",
                f"- Realized today (end-of-window): ${pl.get('realized_day_end', 0):+,.2f}",
                ""]

    # Commits
    if commits:
        out += ["## Commits", ""]
        out += ["| When | Hash | Subject | Areas |",
                "|---|---|---|---|"]
        for c in commits[:50]:
            ts = c["ts"][:16].replace("T", " ")
            out.append(f"| {ts} | `{c['hash']}` | {c['subject'][:80]} | "
                        f"{categorize(c['files'])} |")
        if len(commits) > 50:
            out.append(f"\n_(+{len(commits) - 50} more commits)_")
        out.append("")
    else:
        out += ["## Commits", "", "_No commits in window._", ""]

    # Trades
    if trades:
        out += ["## Trades placed", "",
                "| Time | Symbol | Thesis |", "|---|---|---|"]
        for t in trades[:50]:
            ts = t["ts"][:16].replace("T", " ")
            out.append(f"| {ts} | {t['symbol']} | {t['summary'][:90]} |")
        out.append("")
    else:
        out += ["## Trades placed", "", "_No new trade theses in window._", ""]

    # Active live cells (snapshot at session end)
    if live_cells:
        out += [f"## Active live cells (end-of-session: {len(live_cells)})", ""]
        out.append("```")
        for c in sorted(live_cells, key=lambda x: (x.get('strategy',''), x.get('symbol',''))):
            out.append(f"  {c.get('strategy','?')} | {c.get('symbol','?')} | "
                        f"{c.get('session','?')} | {c.get('side','?')}")
        out.append("```")
        out.append("")

    # Memory highlights
    if memory_files:
        out += ["## Memory entries created/updated", ""]
        for m in memory_files:
            out.append(f"- `{m}`")
        out.append("")

    # Lesson highlights
    if lesson_files:
        out += ["## Lessons written", ""]
        for l in lesson_files:
            out.append(f"- `{l}`")
        out.append("")

    # Research outputs
    if research_files:
        out += ["## Research outputs", ""]
        for r in research_files:
            out.append(f"- `{r}`")
        out.append("")

    out += ["---", "",
            "_This file is auto-generated by `scripts/session_summary.py` and "
            "preserved by the Stop-hook auto-commit. External tools (Claude "
            "Cowork, future Claude sessions, code reviewers) can read this "
            "directory to understand what happened in each session._"]

    out_path = SESSIONS_DIR / f"{today}_session.md"
    out_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"  session summary: {len(commits)} commits, {len(trades)} trades → "
          f"{out_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
