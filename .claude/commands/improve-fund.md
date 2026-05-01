---
description: Autonomous improvement cycle — audit, implement, test, AUTO-MERGE non-risky changes
---

# /improve-fund

You are running an autonomous improvement cycle on the AI trading fund. **AUTO-MERGE MODE: as of 2026-04-30 user authorized direct merges to master for non-risky changes.** Do not wait for human review on changes that don't touch the high-risk file blocklist.

## Top priority — read first

**`vault/_meta/current_goal.md`** is the team's #1 directive. Right now: pass the $50K Topstep Combine. Above everything. Every improvement you propose should be evaluated against: *"does this move the fund closer to passing the Combine?"* Improvements that don't are deferred until after the Combine is passed.

## Goal

Pick ONE high-leverage improvement (Combine-relevant first), implement it in an isolated git worktree, run all tests, and post a clean diff + summary back. Don't try to fix everything in one cycle — one focused change, fully tested.

## Step 1 — Read the backlog

Read `vault/_meta/improvement_backlog.md`. The backlog is a prioritized list of improvements with:
- **Priority**: P0 (critical) / P1 (high) / P2 (medium) / P3 (low)
- **Effort**: estimate in minutes
- **Status**: `open` / `in-progress` / `proposed` / `merged`
- **Risk**: `low` / `medium` / `high` (touches what — config? code? broker? hooks?)

If multiple items are tagged `in-progress`, finish the oldest one before starting new work.

## Step 2 — Pick one item

Selection criteria (in order):
1. P0 items first
2. Within a priority, prefer `low` risk + small effort
3. Skip items requiring user input (e.g., "user must provide Discord webhook URL")
4. Skip items touching `hooks/`, `state/db.py`, broker code, or `risk_limits.yaml.hard_rules` unless they're explicitly tagged `auto-merge: true`

If no items are pickable, audit the codebase for a NEW improvement candidate, append it to the backlog with a proposal-only entry, and stop. Do not implement freshly-identified items in the same cycle (gives the user a chance to veto).

## Step 3 — Work in an isolated worktree

Use the Agent tool with `isolation: "worktree"` to do the implementation in a fresh checkout. The agent should:
1. Mark the backlog item `in-progress` (so concurrent cycles don't double-implement)
2. Make the code/config change
3. Add or update tests covering the new behavior
4. Run `python -m pytest tests/ -q --ignore=tests/test_overnight_fixes.py`
5. Run `python -m scripts.preflight` — must still produce a sensible result (not a regression)
6. Return a summary including: files changed (count + list), test result, lines added/removed

## Step 4 — Decide: auto-merge or propose

**Auto-merge if ALL of:**
- Tests pass (no regressions)
- Files changed are NOT in the HIGH_RISK_FILES list (below)
- The change reduces risk, fixes a bug, or improves NET monthly P&L by a clear mechanism
- Change size < 200 lines

If auto-merge → commit to master, push. PR not needed.
If propose-only → push branch, open PR via `gh pr create`, await user review.

### HIGH_RISK_FILES (always propose-only; never auto-merge)
- `hooks/risk_gate.py` — the safety hook itself
- `state/db.py` — persistence layer
- `state/schema.sql` — schema (migrations need care)
- `runtime/orchestrator.py` — agent orchestration core
- `tools/projectx_client.py`, `tools/topstep.py` — broker code
- `risk_limits.yaml` `hard_rules` section (the kill switches)
- Anything in `.env*` or `.git*` (config/permissions)

### LOW_RISK_FILES (auto-merge OK)
- `vault/**` — docs, lessons, principles, backlog
- `agents/**` — agent prompts (text-only)
- `tests/**` — adding tests
- `config/*.yaml` non-hard-rule sections (tuning)
- `scripts/**` — new scripts or improvements to existing ones
- `.claude/commands/**` — slash command definitions
- `tools/strategy_performance.py` and other non-broker tools

## Step 5 — Update the backlog

Mark the item `merged` (with the commit SHA) on auto-merge, or `proposed` (with PR link) on propose-only.

**You have explicit authorization to edit `vault/_meta/improvement_backlog.md` directly** — both updating status fields on existing items and appending newly-discovered items. Do not ask permission for these edits; they're part of the cycle. (See `.claude/settings.json` allowlist.)

## Budget cap

This cycle should consume < $1.00 of API spend. If you find yourself approaching that, stop and report what you have. Cost discipline is itself one of the rules we encode.

## Safety rules

- **Never** edit `hooks/risk_gate.py`, `state/db.py`, or `risk_limits.yaml.hard_rules.*` without explicit per-cycle approval in the prompt
- **Never** force-push, reset --hard, or delete branches
- **Never** commit changes to main during the cycle — only worktree branches
- **Always** preserve the test suite as a regression net — if a change breaks a test, the change is the problem, not the test
- **If anything seems unsafe or beyond scope**, abort the cycle and report what you found

## What "high leverage" means here

The point of this loop is NOT to refactor for elegance. It's to make the fund **more profitable, more stable, or both.** Every proposed change should answer: "what bug, gap, or inefficiency does this close, and how much does it move the NET monthly P&L?"

A 30-minute fix that adds $50/month in expected value is worth shipping. A 4-hour refactor that doesn't change any output isn't.
