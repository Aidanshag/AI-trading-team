---
type: meta
applies_to: [portfolio_manager, risk_manager]
status: active
---

# Pre-Trade Checklist

Every order proposal answers 12 questions. **Items are tiered: HARD items missing → BLOCK; SOFT items missing → APPROVE WITH NOTE (logged but not blocked).** This prevents the team from killing trades over context-only items while still enforcing safety items.

## Tiering (per `risk_limits.yaml:risk_framework`)

| Tier | Questions | Penalty if missing |
|---|---|---|
| **HARD** | Q1 strategy, Q4 stop, Q5 worst-case $, Q6 % equity, Q9 invalidation, Q12 execution plan | **BLOCK** |
| **SOFT** | Q2 trigger, Q3 entry, Q7 target, Q8 R:R, Q10 regime fit, Q11 correlation | **APPROVE WITH NOTE** |

The HARD items are the ones where missing answers create real safety holes (size cannot be computed, exit conditions unknown, etc). The SOFT items are context-quality items that improve trade quality but don't endanger capital.

## The 12 Questions

### Setup
1. **Which strategy from `vault/playbooks/strategies_*` is this?** Cite the file and section.
2. **What's the specific trigger?** A price level, a data print, a positioning extreme — quote the exact value.
3. **What's the entry price target?** Specific number, with tolerance ("at 78.40 or better").

### Risk
4. **What's the stop level and why is it placed there?** ATR-based? Structural support? Round number? Quote the math.
5. **What's the worst-case dollar loss?** Tick-distance × tick-value × contracts.
6. **What's the per-trade risk as % of equity?** Must be ≤ 50 bps (or 40 bps if Combine ladder is engaged).

### Reward
7. **What's the target?** Specific number, with rationale.
8. **What's the R-multiple at target?** Must be ≥ 2:1 for normal trades, ≥ 4:1 for Diamond Hunter.

### Invalidation
9. **What specific observation kills the thesis BEFORE the stop hits?** (e.g., "If Fed minutes show no dovish language", "If EIA prints a build > 2M")

### Context
10. **What's the regime fit?** With-regime / counter-regime / regime-neutral. Counter-regime requires explicit override.
11. **What's the correlation with existing book?** Does this stack with current exposure or is it independent?

### Execution
12. **What's the execution plan?** Market / limit / TWAP / iceberg. Time-of-day. Stop placement style. (Execution Specialist owns this; PM verifies).

## Format the PM uses

```yaml
---
type: order_proposal
analyst_source: <name>
strategy: vault/playbooks/strategies_X.md#<section>
---

## Setup
1. Strategy: ...
2. Trigger: ...
3. Entry: ...

## Risk
4. Stop: ...  Why: ...
5. Worst case: $...
6. % of equity: 0.XX%

## Reward
7. Target: ...  Why: ...
8. R-multiple: 2.X

## Invalidation
9. Kill signal: ...

## Context
10. Regime: ...
11. Correlation: ...

## Execution
12. Plan: ...
```

## Risk Manager's response to incomplete checklists

If any question is missing or vague:

> **BLOCK.** Pre-trade checklist incomplete. Questions [N, M, ...] missing or insufficient. Refer to `vault/_meta/pre_trade_checklist.md`. Resubmit with all 12 questions answered.

This is not bureaucracy. This is the discipline that separates traders who survive from those who don't. Every question answered is one fewer way to lose.
