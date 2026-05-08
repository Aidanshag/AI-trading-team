---
type: analysis
date: 2026-05-07
author: Cowork (Claude)
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, Cowork, Claude Code]
sources:
  - vault/lessons/2026-04-29_zn_orb_overnight_failed.md
  - vault/lessons/2026-04-29_gc_narrow_range_break_winner.md
  - vault/lessons/2026-05-05_profit_lock_disabled_overnight.md
  - vault/lessons/2026-05-05_strategy_validation_lockdown.md
confidence: PATTERN
status: open
---

# Meta-patterns across the lessons library

## Why this exists

Four lessons have accumulated since 4/29 — three negative (incidents),
one positive (a winner). Each one has its own specific corrective
actions. But reading them together as a stack reveals **two distinct
recurring failure modes** that are bigger than any single incident.
Naming them as structural design principles, not just tactical
fixes, lets future code changes (by Cowork, Claude Code, or any
agent) catch the same shape *before* it becomes the next lesson.

The 5/5 profit-lock lesson already named one of them in passing
("silent telemetry → load-bearing gate degrades → loss accumulates
undetected"). This piece promotes that observation into an active
design principle and surfaces a second one that hasn't been named.

## Pattern A — Fail-silent defaults

### The shape

A risk gate or operational check reads a value (snapshot field, config
flag, validation table). When the value is missing — empty table,
hardcoded zero, no row, deleted entry — the gate's downstream logic
treats `None` or `0` as "everything fine, allow." The trader proceeds
without the protection the gate was supposed to provide. The failure
mode is invisible until something goes wrong, because the gate didn't
fire a warning when its input went away — it just no-op'd into allow.

### Where this has bitten us

**2026-04-29 (ZN ORB / catastrophe day).** Per the lesson body:
*"The PreToolUse risk hook had several P&L-aware rules that looked
armed in config but silently no-op'd because the data they read didn't
exist. Before this, the table was empty — DLL, TDD, defensive ladder,
daily-target-lock, and consistency-rule checks all early-returned."*
Empty `account_snapshots` table. Five gates blind. $1,013 drawdown.

**2026-05-05 (profit-lock disabled overnight).** Two compounding
fail-silent failures:
1. `daily_hard_target_usd: 0` written by an uncommitted config edit.
   The hook reads the value; `0` reads as "no cap configured" rather
   than "cap explicitly disabled, sound the alarm." Profit-lock blind.
2. `unrealized_pl_usd` hardcoded to `0.0` in `_capture_account_snapshot`
   (comment said "orchestrator does it" but orchestrator was dormant).
   DLL/TDD/ladder projections all read unrealized=0 while NG bled to
   −$702 over 7 hours. Every projection said "fine."

Both incidents trace to the same shape: **a field has a sensible
default in the absence of data, but that default reads as 'safe' to a
gate that should treat absence as 'unsafe.'**

### The principle (PATTERN tier — promote to design rule)

> **Treat missing inputs as fail-closed, not fail-open.** When a gate
> depends on a field, the field's default value must NOT be the same as
> "all good." Either (a) the gate refuses to allow trades when its
> input is missing/zero, or (b) it emits a high-severity event so the
> EOD audit catches the silent-disable.

### Concrete encodings already in place

`_audit_risk_config_drift` (added 2026-05-05) addresses one half of
this — it scans `risk_limits.yaml` for critical gates that have been
zeroed and emits a `risk_config_drift` warn event. The
`degraded_heartbeat` pattern Claude Code added today (2026-05-07,
commit `c08ce73`) addresses another half — `snapshot_capture_failed`
now writes a synthetic snapshot with `can_trade=False` instead of
returning None, so downstream age-checks don't see "fresh enough" data
that doesn't exist.

### Concrete checklist for future changes

When reviewing or writing code (Cowork or Claude Code), apply this
test to any new field, query, or default:

1. *If this value is missing or 0, what gates depend on it?*
2. *Do those gates currently read missing/0 as "safe to proceed"?*
3. *If yes, either change the default to a fail-closed marker, or add
   an explicit assertion that fires loudly when the value isn't fresh.*

This belongs in the next iteration of `CLAUDE.md` and the
`/improve-fund` cycle's review prompt.

---

## Pattern B — Wrong-context validation

### The shape

A metric is calibrated under one set of conditions and applied under
a different set. The calibration is correct *somewhere* but wrong
*here*. The trade looks signal-confirmed by the metric, but the
metric's signal is meaningless in the actual deployment regime.

### Where this has bitten us

**2026-04-29 (ZN ORB).** Multiple wrong-context failures stacked:
- *Volume thresholds calibrated for RTH applied to overnight.* QR
  cited "3× baseline volume" as confirmation. RTH baseline = 1500-3000
  contracts/bar. Overnight baseline = 5-15 contracts/bar. The
  "confirmation" was 597 contracts, normal evening volume but
  3× a very different baseline.
- *ORB signal formed during peak liquidity, fired 10 hours later in
  thin tape.* The strategy's edge depends on same-session momentum
  confirmation. Cross-session firing applies the strategy in a
  context where its edge mechanic doesn't operate.
- *Hawkes intensity self-excitation* used as a regime indicator
  across regimes. Self-excitation works as a signal when liquidity
  is consistent. When the regime flips (RTH → overnight), the
  intensity number compares apples to oranges.

**2026-05-05 (strategy validation lockdown).** Aggregate-level
walk-forward passed; cell-level failed. The trader was firing on
(symbol, session, side) cells outside the validated subsets because
the live gate was symbol-level only and default-allow. Quote from
the lesson: *"aggregate fails while specific cells pass. Always
validate at the granularity at which you'll deploy."*

### The principle (PATTERN tier — promote to design rule)

> **Validate at the granularity at which you'll deploy. Calibrate
> metrics within the regime where they'll be evaluated.**
>
> If you're going to fire on (symbol, session, side), validate at
> (symbol, session, side) — not aggregated across all sessions and
> sides. If you're going to read volume in overnight tape, calibrate
> volume thresholds against overnight history — not RTH. If you're
> going to act on a signal hours after formation, validate the
> signal's persistence over that delay window.

### Concrete encoding partially in place

The 5/5 lockdown encoded this for strategy validation:
`STRATEGY_CELL_ALLOWLIST` enforces (symbol × session × side)
granularity. The live `live_strategies_filter` lock takes it further
— even validated cells are restricted to a hand-picked subset.

What's NOT yet encoded is the volume-calibration version. Per the
4/29 lesson, signals should require **same-time-of-day historical
volume comparison**, not absolute thresholds. No code currently
enforces this. Worth tagging as a future improvement.

### Concrete checklist for future changes

For any new strategy, validation cell, or signal threshold:

1. *Where will this be deployed?* (symbol set, session window, side)
2. *Where was the threshold calibrated?* (data source, regime, time
   range)
3. *Are the deployment regime and the calibration regime the same?*
4. *If not, recalibrate against the deployment regime, OR carry the
   calibration scope as an explicit constraint that gates firing.*

---

## Pattern C (single positive observation)

The 4/29 GC narrow_range_break winner identified one repeatable
positive condition, but it's a single trade — too small a sample to
elevate to design principle. Worth flagging so it doesn't get lost:
*compressed-range setup + liquidity-transition window (post-Asian
hand-off, just past midnight UTC) + symbol-fit (GC's clean mean-reversion
+ deep book) + R:R discipline.* If 3+ further GC NR7 winners stack at
this same shape, this becomes Pattern C with PATTERN-tier confidence
and the structure should be tagged as a high-conviction sub-cell.

## How this analysis becomes learning

Both Pattern A and Pattern B are at PATTERN tier (n=2 distinct lesson
incidents each). The promotion path:

1. **Cowork (this piece)** — naming and stating the principle.
2. **Code review checklist** — add Pattern A and Pattern B as items
   in `/improve-fund`'s review prompt and in `CLAUDE.md`. Any agent
   reviewing a code or config change runs the checklist.
3. **Promotion to RULE tier** if either pattern catches a third
   incident OR successfully prevents one. Track via the analysis
   INDEX.md `promotion log`.
4. **Hard encoding** — if a third occurrence of either pattern emerges
   despite the checklist, escalate to a hard test that fails CI.

## Recommended next-session actions

For Claude Code or Cowork's next session, in priority order:

1. **Update CLAUDE.md and `/improve-fund` review prompt** to include
   Pattern A and Pattern B as explicit checklist items. (Cowork lane;
   vault/agents/CLAUDE.md is not HIGH_RISK.)

2. **Volume-context calibration upgrade** (Pattern B's open encoding):
   add session-aware volume thresholds to the strategy gating in
   `auto_trader.py`. Tag as a proposal in
   `vault/_meta/analysis/proposed_changes/` rather than implementing
   without review — touches the live trading hot path.

3. **Watch for Pattern A occurrences over the next 30 days.** Any
   risk_config_drift, snapshot_capture_failed, or
   strategy_validation_drift event is a Pattern A incident. Update the
   INDEX.md promotion log when one occurs.

## Confidence and lifecycle

PATTERN (n=2 distinct incidents per pattern). Promotes to RULE if a
third instance of either pattern emerges. The patterns themselves are
domain-general — they apply to any code that reads telemetry or
calibrates thresholds. They are NOT specific to gap_fill or any
single strategy.

## See also

- [[2026-05-07_treasury_cell_decay_read]]
- [[2026-05-07_risk_event_distribution]]
- [[../../lessons/2026-04-29_zn_orb_overnight_failed]]
- [[../../lessons/2026-05-05_profit_lock_disabled_overnight]]
- [[../../lessons/2026-05-05_strategy_validation_lockdown]]
- [[../learning_system]]
