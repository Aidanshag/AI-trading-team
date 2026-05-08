"""Backup auto-memory files into the project repo so they survive a
machine loss / get pushed to git via the auto-commit hook.

The auto-memory directory at `~/.claude/projects/<sanitized-cwd>/memory/`
lives in the user profile, NOT in OneDrive or git. If the user loses
their machine, those memory files are gone — and they encode every
"feedback" / "project" / "user" / "reference" entry future Claude
sessions rely on to behave correctly.

This script copies the memory directory into `vault/_meta/memory_backup/`
on each preflight run. The vault is in git AND in OneDrive, so both
mirrors get the snapshot.

Run via:
  python scripts/backup_memory.py
Or wired into preflight (next preflight step).
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MEMORY_DIR = (Path.home() / ".claude" / "projects"
              / "C--Users-Owner-OneDrive-Personal-AI-AI-Trading" / "memory")
BACKUP_DIR = PROJECT_ROOT / "vault" / "_meta" / "memory_backup"


def main() -> int:
    if not MEMORY_DIR.exists():
        print(f"  memory dir not found: {MEMORY_DIR}")
        return 0

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    # Copy each .md file
    files_copied = 0
    files_unchanged = 0
    for src in MEMORY_DIR.glob("*.md"):
        dst = BACKUP_DIR / src.name
        if dst.exists() and dst.read_bytes() == src.read_bytes():
            files_unchanged += 1
            continue
        shutil.copy2(src, dst)
        files_copied += 1

    # Write a manifest
    manifest = BACKUP_DIR / "_manifest.md"
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    files = sorted(BACKUP_DIR.glob("*.md"))
    manifest_text = (
        f"# Memory backup manifest\n\n"
        f"Last sync: **{ts}**\n\n"
        f"Source: `{MEMORY_DIR}`\n"
        f"Backup: `{BACKUP_DIR.relative_to(PROJECT_ROOT)}`\n\n"
        f"Files: **{len(files) - 1}** (excluding this manifest)\n\n"
        f"| File | Size | Modified |\n"
        f"|---|---:|---|\n"
    )
    for f in files:
        if f.name == "_manifest.md":
            continue
        sz = f.stat().st_size
        mt = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(timespec="seconds")
        manifest_text += f"| `{f.name}` | {sz} | {mt} |\n"
    manifest.write_text(manifest_text, encoding="utf-8")

    print(f"  memory backup: {files_copied} copied, {files_unchanged} unchanged → "
          f"{BACKUP_DIR.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
