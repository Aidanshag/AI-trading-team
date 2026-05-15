"""Auto-archive stale auto-generated vault files to keep _meta/ navigable.

Runs daily as FundVaultMaintenance task. Idempotent.

Rules:
  - sentinel_YYYY-MM-DD.md  — rotate after 7 days  → _meta/archive/
  - macro_brief_YYYY-MM-DD.md — rotate after 14 days → _meta/archive/
  - rth_audit_*.md           — rotate after 30 days → _meta/archive/
  - daily_summaries/*.md     — never rotate (kept indefinitely)

Files that look auto-generated but are author-modified (mtime > creation
date by >5 min) are SKIPPED — never archive human edits.

Usage:
    .venv/Scripts/python.exe -m tools.vault_archive [--dry]
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
META_DIR = PROJECT_ROOT / "vault" / "_meta"
ARCHIVE_DIR = META_DIR / "archive"

# (filename_glob_regex, rotation_days)
ROTATION_RULES = [
    (re.compile(r"^sentinel_(\d{4}-\d{2}-\d{2})\.md$"), 7),
    (re.compile(r"^macro_brief_(\d{4}-\d{2}-\d{2})\.md$"), 14),
    (re.compile(r"^rth_audit_(\d{4}-\d{2}-\d{2})\.md$"), 30),
    (re.compile(r"^vault_audit_(\d{4}-\d{2}-\d{2})\.md$"), 30),
]


def file_date_from_name(filename: str) -> tuple[datetime, int] | None:
    """Return (file_date_utc, rotation_days) if filename matches a rotation
    rule, else None."""
    for pattern, days in ROTATION_RULES:
        m = pattern.match(filename)
        if m:
            date_str = m.group(1)
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                return d, days
            except ValueError:
                continue
    return None


def should_archive(filepath: Path, now: datetime) -> tuple[bool, str]:
    """Decide if file should move to archive/. Returns (decision, reason)."""
    parsed = file_date_from_name(filepath.name)
    if not parsed:
        return False, "no rotation rule"
    file_date, rotation_days = parsed
    age_days = (now - file_date).days
    if age_days < rotation_days:
        return False, f"age {age_days}d < {rotation_days}d threshold"

    # Safety: check if the file was hand-edited (mtime far after the date in filename)
    try:
        mtime = datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc)
    except Exception:
        return False, "could not stat mtime"
    expected_mtime = file_date + timedelta(hours=24)  # generated within 24h of date
    drift = (mtime - expected_mtime).total_seconds()
    if drift > 5 * 60:  # 5 min grace
        return False, f"file mtime drifted +{drift/3600:.1f}h past expected — may be hand-edited"
    return True, f"age {age_days}d >= {rotation_days}d"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry", action="store_true",
                     help="report what would be moved; don't move")
    args = p.parse_args()

    now = datetime.now(tz=timezone.utc)
    if not META_DIR.exists():
        print(f"ERROR: {META_DIR} not found")
        return 1

    archive_target = ARCHIVE_DIR
    if not args.dry:
        archive_target.mkdir(parents=True, exist_ok=True)

    moved = 0
    skipped = 0
    examined = 0
    for filepath in sorted(META_DIR.iterdir()):
        if filepath.is_dir():
            continue
        examined += 1
        decision, reason = should_archive(filepath, now)
        if not decision:
            if file_date_from_name(filepath.name) is not None:
                # File matched a rule but isn't ready to rotate
                skipped += 1
            continue
        dest = archive_target / filepath.name
        if args.dry:
            print(f"  WOULD MOVE {filepath.name} -> archive/ ({reason})")
        else:
            shutil.move(str(filepath), str(dest))
            print(f"  MOVED      {filepath.name} -> archive/ ({reason})")
        moved += 1

    print()
    print(f"examined: {examined} files in _meta/")
    print(f"moved: {moved}")
    print(f"skipped (rule-matched but not ready): {skipped}")
    if args.dry:
        print("(dry-run: no files actually moved)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
