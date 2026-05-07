---
name: Coordinate with Claude Cowork — no 1-step-forward-2-back
description: User authorized 2026-05-06 to coordinate with Claude Cowork (which works on backend improvements). Both agents must respect each other's work and avoid undoing changes.
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User directive 2026-05-06: "make sure going forward that you coordinate
with Claude Cowork. Cowork will be working on certain back end things to
improve the system. Make sure that you both will be working in
conjunction and not taking a 1 step forward 2 steps back type situation."

## Source of truth

`vault/_meta/cowork_coordination.md` is the shared status doc. Read it
at session start, update it at session end. It defines:
- Ownership split (who owns what areas)
- Coordination rules (read-before-act, don't-revert, conflict resolution)
- Standing context Cowork should know about
- Handoff log (append-only)

## Per-session protocol (do this every session)

**At session start (before making changes):**
1. Read `vault/_meta/cowork_coordination.md` — see what Cowork has been doing
2. Run `git log --since='6 hours ago' --oneline --author=Cowork` (or similar
   pattern matching Cowork's commit author identity) to see Cowork commits
3. If Cowork made significant changes, READ those files before acting on
   anything in the same area
4. If a Cowork change conflicts with current trading state, surface to user
   instead of silently overriding

**During the session:**
- Don't revert Cowork's work without user direction
- If you must change something Cowork modified, rebase + preserve their
  intent where possible
- Add a note to the handoff log explaining your changes when working in
  Cowork's domain (refactoring, infrastructure)

**At session end (auto-handled by Stop hook):**
- `session_summary.py` writes structured recap to `vault/sessions/`
- `auto_commit_session.py` commits + pushes everything
- Next time Cowork pulls, they see the full session record

## 2026-05-07 update: autonomous fix policy

User directive 2026-05-07: "will you and/or cowork automatically fix
these, I don't want to have to tell you guys to fix it. Autonomously
fix these issues yourselves."

**Updated rule: whichever agent detects an issue, fixes it.** Don't
defer to the other agent's "lane" if that creates delay. The lane
ownership in `cowork_coordination.md` describes WHO PRIMARILY OWNS an
area, not "whose permission you need to fix a bug." If you find a
broken fetcher, broken script, broken config, just fix it.

The HARD boundaries below still apply (HIGH_RISK_FILES + live trading
state). Everything else: if it's broken, fix it.

## Hard boundaries — neither agent may violate

These are HIGH_RISK_FILES (per CLAUDE.md). NEITHER agent autonomously
modifies them; user approval required:
- `hooks/risk_gate.py`
- `state/db.py`, `state/schema.sql`
- `tools/topstep.py`, `tools/projectx_client.py`
- `config/risk_limits.yaml.hard_rules`

## Live trading state Cowork should NOT change

The user pinned these. Cowork modifying them = silent regression of
user direction:
- `live_strategies_filter` (gap_fill × ZN/ZT/ZB/ZF only, in `state/strategy_validation.json`)
- `TRAILING_PROFIT_TIERS` in `auto_trader.py`
- `LOSS_TIER_HARD_CAP_USD` = 200
- `daily_target_action` = "cancel_working"
- Position sizing = 1 contract (Phase 2 differential requires user approval)

## What Cowork is welcome to do without coordination

- Performance optimization
- Test coverage
- Refactoring (behavior-preserving)
- Documentation
- Dependency hygiene
- Logging / observability
- New backtest tooling that doesn't touch live trading
- Investigating known bugs (`orders.ts_filled` fill-back, Topstep OCO)
- Slippage measurement (queue item #5)

If they take on something from this list, they should append to the
handoff log in `cowork_coordination.md`.
