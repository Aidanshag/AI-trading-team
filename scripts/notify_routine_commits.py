"""Daily Discord notification for cloud-routine + cowork commits.

Runs once per day (via FundRoutineSummary scheduled task at ~10:00 UTC,
shortly after the cloud `/improve-fund` routine fires at 09:00 UTC). Greps
the last 25h of commits, filters out the user's session auto-commits, and
pings Discord with whatever autonomous work landed in the repo.

This bypasses the need to manually `git log` to see what got built.

Usage:
  python -m scripts.notify_routine_commits           # check + ping
  python -m scripts.notify_routine_commits --dry     # show what would ping
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.alert import send_alert


# Patterns that identify user/automatic commits we want to FILTER OUT
# (we only want to surface autonomous-routine + cowork commits)
_SKIP_PATTERNS = (
    "session: auto-commit",  # the local auto-commit hook
)


def _recent_interesting_commits(hours: int = 25) -> list[str]:
    """Return the subject lines of commits in the last N hours that are
    NOT the user's session auto-commits. Returns empty list on git error."""
    try:
        # Fetch remote first so we see cloud-routine commits before user pulls
        subprocess.run(["git", "fetch", "--quiet"], cwd=PROJECT_ROOT,
                       capture_output=True, timeout=30)
    except Exception:
        pass
    try:
        # Get oneline log across local + remote, last `hours` hours
        result = subprocess.run(
            ["git", "log", "--all", "--oneline", f"--since={hours} hours ago",
             "--pretty=format:%h %ar %an: %s"],
            cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=15,
        )
    except Exception as e:
        print(f"git log error: {e}", file=sys.stderr)
        return []
    if result.returncode != 0:
        print(f"git log returned {result.returncode}: {result.stderr}",
              file=sys.stderr)
        return []
    lines = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
    # Filter out user session auto-commits
    filtered = [ln for ln in lines if not any(p in ln for p in _SKIP_PATTERNS)]
    return filtered


def main() -> int:
    ap = argparse.ArgumentParser(prog="notify_routine_commits")
    ap.add_argument("--dry", action="store_true",
                    help="Show what would be sent without pinging Discord")
    ap.add_argument("--hours", type=int, default=25,
                    help="Lookback window in hours (default 25)")
    args = ap.parse_args()

    commits = _recent_interesting_commits(hours=args.hours)
    if not commits:
        print(f"No autonomous commits in last {args.hours}h.")
        return 0

    # Trim message to a Discord-friendly length
    header = (f":robot: Autonomous activity in last {args.hours}h "
              f"({len(commits)} commit(s)):")
    body = "\n".join(f"- {c}" for c in commits[:15])  # cap at 15
    if len(commits) > 15:
        body += f"\n... and {len(commits) - 15} more"
    message = f"{header}\n{body}"

    if args.dry:
        print("--- WOULD SEND ---")
        print(message)
        return 0

    ok = send_alert(message, level="info")
    print(f"ping sent: {ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
