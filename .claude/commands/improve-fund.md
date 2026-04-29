---
description: Autonomous improvement cycle — audit the fund, propose ONE improvement, test in worktree, report
---

# /improve-fund

You are running an autonomous improvement cycle on the AI trading fund. **You operate in propose-only mode by default.** Do not merge changes to main without an explicit instruction in the prompt.

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

## Step 4 — Report

Post a structured summary:
- What was attempted
- Whether tests pass
- The diff stat
- Whether you recommend merging (default: NO; user reviews)
- Any unexpected things found in the audit

## Step 5 — Update the backlog

Mark the item `proposed` (NOT merged) with a pointer to the worktree branch. The user merges manually after review.

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
