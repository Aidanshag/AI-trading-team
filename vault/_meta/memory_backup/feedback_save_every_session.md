---
name: Save every session for external readers
description: User authorized 2026-05-06 to make sure every conversation/session is captured to durable storage so external tools (Claude Cowork, future Claude sessions, code reviewers) see fully up-to-date context.
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User directive 2026-05-06: "going forward make sure you save everything we
do and every conversation we have. I will have things such as Claude
Cowork looking at them and want to make sure that everything it sees is
fully up to date based on what we do in here."

## Persistence layers in place

| Layer | What it captures | Where |
|---|---|---|
| **1. Code/config commits** | All file edits, configs, scripts | git → `origin/master` (auto-pushed via Stop hook) |
| **2. Memory backup** | All `~/.claude/projects/.../memory/` files | `vault/_meta/memory_backup/` (preflight step 13) → git |
| **3. Lessons** | Auto-promoted ADVISORY → PATTERN → RULE entries | `vault/lessons/` → git |
| **4. Research outputs** | Walk-forward reports, validation results, sweep results | `vault/research/` → git |
| **5. Session summaries** ⬅ NEW | Per-session structured snapshot of commits, trades, P&L, active cells | `vault/sessions/<date>_session.md` → git |
| **6. State database** | All trades, decisions, risk events, snapshots | `state/fund.db` (in OneDrive; not git) |
| **7. Auto-commit Stop hook** | Generates session summary + commits + pushes | runs on every Claude session-end |

## Session summary protocol

`scripts/session_summary.py` runs as first step of the Stop hook (before
the auto-commit). It captures:
- All git commits in the last 24h with messages + categorized impact
  areas (code/config/lesson/research/memory/safety/tests)
- All trade theses recorded
- P&L delta over the window
- Active live cells at session end
- Memory entries created/updated this session
- Lessons written this session
- Research outputs generated

The summary is saved to `vault/sessions/<date>_session.md` and gets
auto-committed + pushed to git, so external tools have a single
canonical "what happened today" file per day.

## What this means for external tools (Claude Cowork etc.)

Anyone reading the repo will find:
- `vault/sessions/` → human-readable per-session summaries, newest first
- `vault/_meta/memory_backup/` → all the `feedback_*` rules / standing authorizations
- `vault/lessons/` → what the system has learned (incidents + their fixes)
- `vault/research/backtests/` → walk-forward validation outputs
- `vault/research/validation/` → daily OOS refreshes
- `vault/research/live_vs_oos/` → live vs predicted R-multiple comparisons
- Git log → full file-change history

That's a complete, auditable record without needing access to Claude's
internal session transcripts.

## Optional: enable `autoUploadSessions` for cloud mirror

If user wants Anthropic's cloud-side session mirror as a separate backup
layer, edit `.claude/settings.json` to add:
```json
"autoUploadSessions": true
```
This mirrors local sessions to claude.ai as view-only (per the schema —
no remote control). Combined with the local persistence above, this
gives a third backup tier (project disk → OneDrive → git remote → Anthropic cloud).
NOT enabled by default; user-facing privacy decision.
