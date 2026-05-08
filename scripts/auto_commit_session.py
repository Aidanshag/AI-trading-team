"""Stop-hook script: auto-commit and push any uncommitted changes at end of turn.

Wired up in `.claude/settings.json` under `hooks.Stop`. Reads stdin (the
hook event JSON, ignored), inspects `git status`, filters out machine-
state / draft / empty files, stages everything else, creates a local
commit, then pushes to `origin` (if remote is configured + credentials
are cached). User authorized auto-push 2026-05-05.

Output: JSON `{"systemMessage": "..."}` so the user sees one line of
confirmation in the Claude UI.

Exclusions:
- Machine state: `*.pid`, `*.lock`, `logs/runtime.pid`,
  `.claude/scheduled_tasks.lock`, `vault/economic_calendar/today.json`
- Obsidian drafts: `Untitled*.{base,canvas,md}`, top-level `*.canvas`,
  top-level `*.base` with default content
- Empty markdown files (0 bytes)

Push behavior:
- Push to `origin <current-branch>` after a successful commit
- Push runs with a 30s timeout; if it fails (network, auth, no remote),
  surface the error but don't block the Stop event
"""
from __future__ import annotations

import fnmatch
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)


# Files / patterns we never commit automatically
EXCLUDE_GLOBS = (
    "*.pid",
    "*.lock",
    "logs/runtime.pid",
    "logs/auto_trader.pid",
    ".claude/scheduled_tasks.lock",
    "vault/economic_calendar/today.json",
    "Untitled*.base",
    "Untitled*.canvas",
    "Untitled*.md",
    "Untitled.base",
    "Untitled.canvas",
    "*.canvas",   # Obsidian working files
    "*.base",     # Obsidian database files
)


def emit(msg: str, ok: bool = True) -> None:
    """Print one JSON line for the hook system to display to the user."""
    print(json.dumps({"systemMessage": msg, "suppressOutput": True}))
    sys.exit(0 if ok else 0)  # never block the Stop event


def is_excluded(path: str) -> bool:
    """True if a path matches any EXCLUDE_GLOBS pattern."""
    name = Path(path).name
    for pat in EXCLUDE_GLOBS:
        if fnmatch.fnmatch(path, pat) or fnmatch.fnmatch(name, pat):
            return True
    return False


def is_gitignored(paths: list[str]) -> set[str]:
    """Batch-call `git check-ignore` to find which paths are ignored.

    Files ignored by .gitignore but already tracked still appear in
    `git status` as modified. `git add` refuses them without -f. We
    don't want -f (it would defeat the ignore intent), so we skip them.
    """
    if not paths:
        return set()
    try:
        # --no-index: check the gitignore rules even for tracked files
        # exit code 0 = at least one path matched; 1 = no matches; 128 = error
        proc = subprocess.run(
            ["git", "check-ignore", "--no-index", "--", *paths],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        )
        if proc.returncode in (0, 1):
            return set(p for p in proc.stdout.splitlines() if p)
    except Exception:
        pass
    return set()


def is_empty_markdown(path: str) -> bool:
    """True if .md file exists and is 0 bytes (Obsidian 'new note' artifact)."""
    if not path.lower().endswith(".md"):
        return False
    try:
        return Path(path).stat().st_size == 0
    except OSError:
        return False


def parse_porcelain(out: str) -> list[tuple[str, str]]:
    """Parse `git status --porcelain` lines into (status, path) tuples.

    Handles renames (`R  old -> new`) by keeping only the new path.
    Quoted paths (with spaces) are unquoted.
    """
    rows: list[tuple[str, str]] = []
    for line in out.splitlines():
        if len(line) < 4:
            continue
        status = line[:2]
        rest = line[3:]
        # Rename / copy: "R  old -> new"
        if " -> " in rest:
            rest = rest.split(" -> ", 1)[1]
        # Strip surrounding quotes if git quoted the path
        if rest.startswith('"') and rest.endswith('"'):
            rest = rest[1:-1]
        rows.append((status, rest))
    return rows


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(PROJECT_ROOT), capture_output=True,
        text=True, check=check,
    )


def main() -> None:
    # Drain stdin (hook input JSON; we don't use it but we must consume it
    # so the hook system doesn't block on an unread pipe)
    try:
        sys.stdin.read()
    except Exception:
        pass

    # Generate session summary first so it's part of the commit. Capture
    # what happened this session as a structured markdown for external
    # tools (Claude Cowork, future sessions). Best-effort — never block.
    try:
        subprocess.run(
            ["python", str(PROJECT_ROOT / "scripts" / "session_summary.py")],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True, timeout=30,
        )
    except Exception:
        pass

    # Are we in a git repo?
    try:
        run(["git", "rev-parse", "--is-inside-work-tree"])
    except (subprocess.CalledProcessError, FileNotFoundError):
        emit("auto-commit: not a git repo, skipped")

    # What's uncommitted?
    try:
        status = run(["git", "status", "--porcelain"])
    except subprocess.CalledProcessError as e:
        emit(f"auto-commit: git status failed — {e.stderr[:120]}", ok=False)

    rows = parse_porcelain(status.stdout)
    if not rows:
        # Nothing to do — silent
        sys.exit(0)

    # Partition: include vs exclude
    to_stage: list[str] = []
    excluded: list[str] = []
    for st, path in rows:
        if is_excluded(path) or is_empty_markdown(path):
            excluded.append(path)
        else:
            to_stage.append(path)

    # Second filter: anything git considers ignored (e.g. tracked-but-now-
    # gitignored files like .claude/scheduled_tasks.lock or logs/*.pid).
    # `git add` would fail on those without -f; we never want -f here.
    ignored = is_gitignored(to_stage)
    if ignored:
        to_stage = [p for p in to_stage if p not in ignored]
        excluded.extend(sorted(ignored))

    if not to_stage:
        # Only excluded files dirty — silent
        sys.exit(0)

    # Stage and commit
    try:
        # Add files individually to handle paths with spaces and special chars
        for p in to_stage:
            run(["git", "add", "--", p])
    except subprocess.CalledProcessError as e:
        emit(f"auto-commit: git add failed — {e.stderr[:160]}", ok=False)

    # Verify something is actually staged (excluded-only case can leave
    # the index clean even if to_stage was non-empty — e.g. CRLF-only changes)
    try:
        diff = run(["git", "diff", "--cached", "--name-only"])
    except subprocess.CalledProcessError:
        diff = None
    staged = diff.stdout.strip().splitlines() if diff else []
    if not staged:
        sys.exit(0)

    # Build a commit message
    n = len(staged)
    sample = ", ".join(staged[:3])
    if n > 3:
        sample += f", +{n - 3} more"
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    title = f"session: auto-commit {n} file{'s' if n != 1 else ''} ({ts})"
    body = f"Files:\n" + "\n".join(f"- {p}" for p in staged)
    if excluded:
        body += "\n\nExcluded (machine state / drafts):\n" + "\n".join(
            f"- {p}" for p in excluded[:10]
        )
        if len(excluded) > 10:
            body += f"\n- (+{len(excluded) - 10} more)"
    msg = f"{title}\n\n{body}\n"

    try:
        run(["git", "commit", "-m", msg])
    except subprocess.CalledProcessError as e:
        # Pre-commit hook failure or similar — surface it but don't block
        err = (e.stderr or e.stdout or "").strip()[:200]
        emit(f"auto-commit: commit failed — {err}", ok=False)

    # Push to origin if a remote is configured. User authorized auto-push
    # 2026-05-05. 30s timeout — credential manager should make it
    # non-interactive; if it isn't, fail soft and surface the error.
    push_status = ""
    try:
        # Get current branch for explicit push target
        br = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        branch = br.stdout.strip() or "HEAD"
        # Confirm a remote exists before attempting push
        rem = run(["git", "remote"], check=False)
        if not rem.stdout.strip():
            push_status = " (no remote — local commit only)"
        else:
            push = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=str(PROJECT_ROOT), capture_output=True, text=True,
                timeout=30,
            )
            if push.returncode == 0:
                push_status = " + pushed"
            else:
                err = (push.stderr or push.stdout or "").strip()
                # Common case: divergent branches — leave for user to resolve
                push_status = f" (push failed: {err[:120]})"
    except subprocess.TimeoutExpired:
        push_status = " (push timed out — likely auth prompt)"
    except Exception as e:
        push_status = f" (push errored: {type(e).__name__})"

    summary = (f"auto-committed {n} file{'s' if n != 1 else ''}: "
               f"{sample}{push_status}")
    emit(summary)


if __name__ == "__main__":
    main()
