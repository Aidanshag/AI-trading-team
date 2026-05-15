---
type: retirement_note
strategy: gap_fill (both gap_fill and gap_fill_wide variants)
retired_on: 2026-05-11
status: final — DO NOT redeploy without re-validation
references:
  - vault/research/analysis/2026-05-11_gap_fill_wide_validation_attempt.md (root cause)
  - vault/_meta/improvement_backlog.md (current live cells exclude gap_fill)
  - state/strategy_validation.json (live_strategies_filter — gap_fill absent)
  - vault/_meta/memory_backup/project_validated_edge_gap_fill.md (HISTORICAL — wrong)
---

# gap_fill / gap_fill_wide — retirement note

## TL;DR

**Both `gap_fill` and `gap_fill_wide` were REMOVED from `live_strategies_filter` on 2026-05-11.** They are NOT deployed to live trading. The earlier "validated headline edge" claims (memory file `project_validated_edge_gap_fill.md`, plus stale references in `strategic_roadmap.md`) were based on a buggy validation pipeline. Under the corrected pipeline, neither variant produces a deployable parameter set.

This file is the canonical source for the retirement narrative. Other documents should link here rather than restate the history.

## Why we thought it worked

Initial walk-forward results (pre-2026-05-11) showed `gap_fill_wide` on ZN/NG/6E producing t-stats in the +7.95 to +11.76 range — extraordinarily strong. The strategy was elevated to "lead validated edge" in the strategic roadmap and a 26-cell extended-set deployment was planned across the treasury and FX universe.

## What was actually broken

The validation pipeline had three compounding bugs (full analysis: `vault/research/analysis/2026-05-11_gap_fill_wide_validation_attempt.md`):

1. **Missing `tick_size` injection** — ATR-based stops collapsed sub-tick on quiet bars, producing degenerate stop distances near zero.
2. **`t.stop_price` typo** in the backtest harness — `t.stop` was being read instead, so the engine evaluated trades against the WRONG stop price.
3. **Silent division-by-tiny-epsilon** in the R-ratio computation — `max(stop_dist, 1e-9)` made every signal look "high conviction" when the stop had collapsed.

These compounded: a signal would be emitted with stop ≈ entry, the backtest would compute a massive R-multiple even on tiny price moves, and the t-stat would be inflated by orders of magnitude.

## What the corrected pipeline showed

Once the bugs were fixed (commits referenced in the analysis file):
- Neither `gap_fill` nor `gap_fill_wide` produces a parameter set meeting our graduation gates (n>=25, t>=1.5, E>0 OOS)
- The "edge" was entirely an artifact of the degenerate stop computation
- No deployment is justified at this time

## What changed in the codebase

- 2026-05-11 evening: `gap_fill` and `gap_fill_wide` removed from `state/strategy_validation.json:live_strategies_filter`
- Strategy code (`tools/backtest/strategies.gap_fill` + `gap_fill_wide`) **RETAINED** for future re-validation when the backtest engine is fully audited
- CI test `tests/test_pattern_regressions.py::test_pattern_b_gap_fill_floor_active_emits_no_sub_floor_signals` added to fail the build if a future signal-emitter regresses to sub-floor stops

## Pattern A/B classification

This was a **Pattern B (wrong-context validation)** failure. The metric was correct under certain assumptions but those assumptions were violated. The lessons-encoded fix is the n=3 CI test landed in `test_pattern_regressions.py`. See `vault/_meta/analysis/2026-05-07_lesson_meta_patterns.md` for the full Pattern A/B framework.

## Memory backup files that reference this — for cleanup

The following memory entries refer to the (now-retired) gap_fill validation. They should NOT be cited as current state:

- `vault/_meta/memory_backup/project_validated_edge_gap_fill.md` — HISTORICAL, **do not act on**
- `vault/_meta/memory_backup/project_strategy_focus_fvg.md` — references gap_fill peer-strategy comparisons; mostly OK but cross-check timestamps

The auto-maintenance vault_auditor (built 2026-05-15) will flag stale references like these going forward.
