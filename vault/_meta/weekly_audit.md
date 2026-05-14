---
type: routine_instructions
schedule: weekly (Sundays ~18:00 ET, before Globex reopen)
purpose: Proactive trader+brain code audit
authorized_actions: edit, refactor, dedupe, write tests, file backlog items, auto-commit
forbidden_actions: edit HIGH_RISK_FILES (state/db.py, state/schema.sql, hooks/risk_gate.py, tools/topstep.py, tools/projectx_client.py, risk_limits.yaml:hard_rules), restart trader during active position, force-push
---

# Weekly trader+brain audit — instructions for Claude

Fund grew fast and code mistakes compound. This weekly audit is the
proactive cleanup that prevents the "Claude codebase is a mess" failure
mode the user described: multiple things doing the same thing, fixing
one thing breaks two others, brittle coupling.

**When you run this:** Sunday evening before Globex reopen. The trader
is dormant, no positions. Best window for refactoring without trader
state to worry about.

## Scope of the audit

Audit these files end-to-end:

**Trader (execution layer — keep <600 lines, see [[feedback_continuous_trader_trim]]):**
- `scripts/live_trader.py`
- `tools/bracket_placement.py`
- `tools/loss_cap.py`
- `tools/orphan_cleanup.py`
- `tools/snapshot_writer.py`
- `tools/profit_protect.py`
- `tools/signal_queue.py`
- `tools/trader_utils.py`
- `tools/trade_state.py`
- `tools/unrealized_pnl.py`
- `tools/bar_fetcher.py`
- `tools/hard_flatten_clock.py`
- `tools/position_protection.py`
- `tools/daily_profit_cap.py`
- `tools/account_stage.py`

**Brain (decision layer):**
- `scripts/brain_signaler.py`
- `tools/brain_logic.py`

**Risk floor (read-only — DO NOT EDIT):**
- `hooks/risk_gate.py`
- `state/db.py`
- `state/schema.sql`
- `tools/topstep.py`
- `tools/projectx_client.py`
- `config/risk_limits.yaml` (hard_rules block read-only)

## What to look for

1. **Duplicate functionality.** Same logic implemented in >1 place. Common pattern: a function in `tools/X.py` and a near-identical inline version in `scripts/live_trader.py`. Examples found historically:
   - `_position_signature` was in both `live_trader.py` and `tools/bracket_placement.py`
   - Tick economics defined separately in `_TICK_ECONOMICS` (profit_protect.py) AND `config/symbols.yaml`
   - Day-boundary computation duplicated between `snapshot_writer.py` and `trade_state.py` (fixed 2026-05-14)

   **Action:** consolidate to ONE source of truth. Re-export from the canonical location.

2. **Dead code.** Functions defined but never called. Check via `grep -r "function_name" --include="*.py" --exclude-dir=.venv`. If only the definition + tests match, delete.

3. **Pattern A bugs (silent fail-open defaults).** Any code path that reads a value, gets None/0/missing, and proceeds as if it were "safe to act." Examples:
   - `_TICK_ECONOMICS.get(symbol, (0.0, 0.0))` → if zero, position is silently unprotected
   - `acct.get("internal_dll_target_usd", 1000)` → default to Topstep DLL hides config absence
   - Any `if value: do_safety_check()` where value=0 skips the check

   **Action:** convert to fail-closed — raise on missing, OR add a LOUD log + Discord alert at the silent path.

4. **Pattern B bugs (wrong-context calibration).** Code that uses a threshold/calibration without verifying the deployment context matches the calibration context. Examples:
   - Strategy stop sizes calibrated in regime X applied in regime Y
   - Trade-count thresholds in UTC day vs Topstep day (fixed 2026-05-14)

   **Action:** explicit scope check, or document the assumption inline.

5. **Tight coupling / fragility.** "Fixing X breaks Y" symptoms:
   - Function A in module X imports a private helper from module Y. Refactoring Y breaks A.
   - Constants defined in one place AND referenced as literals elsewhere.
   - Tests that depend on implementation details rather than contracts.

   **Action:** make dependencies explicit (proper imports, named constants), make tests behavior-oriented.

6. **Size limits.**
   - `scripts/live_trader.py` should stay <600 lines (see [[feedback_continuous_trader_trim]]).
   - Any other file >700 lines: candidate for extraction.

7. **Test coverage gaps.** For each Pattern A/B regression historically encountered, ensure there's a build-failing test in `tests/test_pattern_regressions.py`.

8. **Memory drift.** Read `~/.claude/projects/.../memory/MEMORY.md`. Check that the rules in memory still match the code. If memory says "X is enforced" but code doesn't enforce X, surface the discrepancy.

## How to act on findings

- **Trivial cleanup** (delete dead function, fix typo, consolidate duplicate): auto-fix, run `python -m pytest tests/ -q --ignore=tests/test_overnight_fixes.py`, commit.
- **Refactor** (extract function, dedupe pattern): auto-fix if non-HIGH_RISK, tests must still pass, commit with descriptive message.
- **Risk-floor change** (would touch HIGH_RISK_FILES): file a `[P1]` entry in `vault/_meta/improvement_backlog.md` with `autonomous-eligible: no` so a human reviews.
- **Architectural concern** (e.g., "brain emits cells outside live_allowlist"): file a `[P2]` entry in the backlog.

## Outputs

End every audit run with a markdown report at:
`vault/_meta/weekly_audit_<YYYY-MM-DD>.md`

Format:
```markdown
# Weekly audit YYYY-MM-DD

## Status
- Trader line count: N (target <600)
- Test count: N (target: all pass)
- Files audited: list
- Active live_allowlist cells: count, breakdown by symbol

## Issues found and fixed
- [issue] → [action taken] → [commit]

## Issues filed in backlog
- [issue] → [backlog priority]

## Architectural notes
- [observations about coupling, technical debt, etc.]
```

Also: post a Discord summary via `tools/alert.py` so the user sees the
report exists.

## Standing principles (don't violate)

- **Brain decides, trader places.** Never put strategy/regime/session logic in the trader. See [[feedback_brain_owns_decisions]].
- **Don't raise MAX_SIGNAL_RISK_USD.** The $150 cap is the encoded lesson from 2026-05-12. See [[feedback_combine_vs_xfa_strategy]].
- **Never amend or force-push published commits.** Always make a new commit.
- **Never restart the trader during an active open position** — wait for flat.
- **Never edit HIGH_RISK_FILES without user approval.** File a backlog item instead.

## When in doubt

- File a backlog item with concrete reproduction steps. The user reviews on next session.
- Better to surface 10 small findings than miss 1 big bug.
