---
type: process_doc
status: active
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, Cowork, Claude Code]
read_on_first_wake: true
purpose: |
  Formal stages every trading hypothesis must clear before reaching
  live capital. Closes the gap between "looks great in backtest" and
  "actually works good in production" (per user reframe 2026-05-08).
  Every promotion has explicit gates and rollback rules.
updated: 2026-05-09
---

# Hypothesis-to-live pipeline

## Why this exists

The fund's primary mission per the 2026-05-08 reframe:

> **Close the gap between "looks great" and "actually works in production."**

Validating live behavior against backtest predictions is now ranked
above maximizing edge. This document formalizes the stages a hypothesis
moves through from idea to live capital, the gates between them, and
the rollback rules at each stage.

A hypothesis that hasn't earned its way through every stage cannot
trade real capital. Cells currently in `live_strategies_filter` were
grandfathered through some of these stages before this doc existed —
that's acknowledged. Future additions follow the full pipeline.

## The stages

```
[1. IDEA]
   ├─ promotion gate ──→
[2. BACKTEST]
   ├─ promotion gate ──→
[3. WALK-FORWARD]
   ├─ promotion gate ──→
[4. STRESS TEST]
   ├─ promotion gate ──→
[5. PAPER LIVE]
   ├─ promotion gate ──→
[6. LIVE SMALL]
   ├─ promotion gate ──→
[7. LIVE FULL]
       │
       └─ continuous re-validation, demote on decay
```

Each gate has explicit pass criteria. Each stage has explicit
rollback rules.

---

## Stage 1 — IDEA

**What happens:** an analyst, researcher, agent, or human writes down
a trading hypothesis. The hypothesis includes:

- A specific signal trigger (price/structure/event-based)
- Expected hit rate and average R or $ outcome
- Hypothesized regime where it works (vol, trend, time-of-day, news)
- Hypothesized regime where it fails

**Output artifact:** `vault/research/hypotheses/<date>_<slug>.md`

**Promotion gate to BACKTEST:**
- The hypothesis is specific enough that someone else can implement
  it without further input
- The expected behavior is quantified (not "should be profitable")
- Failure modes are named (not "if it doesn't work I don't know why")

**Rollback at this stage:** none — ideas are free.

---

## Stage 2 — BACKTEST

**What happens:** the hypothesis is implemented as a Python function in
`tools/backtest/strategies.py`, registered in `STRATEGY_REGISTRY`, and
backtested on historical bars (typically 60d × 5m intraday for
intraday strategies, longer for swing).

**Output artifact:** raw backtest report in
`vault/research/backtests/<date>_<slug>.md` showing:

- Per-cell (symbol × session × side) trade count, hit rate, mean R,
  mean $ at slip=0
- Comparison vs the literature prior (if applicable) or vs the
  hypothesis's predicted hit rate / R

**Promotion gate to WALK-FORWARD:**
- Aggregate-level positive expectancy on at least one symbol cell
  with n ≥ 50
- Hit rate within ±15 percentage points of hypothesis's prediction
  (i.e., the strategy is doing what it was supposed to)

**Rollback rules:**
- If aggregate-level negative expectancy across all symbols, retire to
  `vault/research/_archive/` with a one-line note. Don't waste
  walk-forward compute on it.
- If hit rate diverges > 15pp from hypothesis, the strategy code may
  not match the hypothesis. Revisit.

---

## Stage 3 — WALK-FORWARD

**What happens:** `scripts/param_sweep.py` runs the strategy with the
candidate parameter grid and produces train/OOS split (typically
75/25) for each cell. Per-cell expectancy is reported in **dollars
adjusted for slippage at 0.25 ticks/side** (the deployment-relevant
metric, not R).

**Output artifact:** `vault/research/param_sweeps/<strategy>_<ts>.{md,csv}`

**Promotion gate to STRESS TEST:**
- At least one cell with `OOS n ≥ 30`, `OOS t-stat ≥ 1.5`, AND
  `mean_net_usd_at_slip_0.25 > 0`
- The cell's `breakeven_slip_ticks` must be ≥ 0.25 (otherwise typical
  slippage eats the edge)
- Train and OOS expectancies should be in the same direction (both
  positive); OOS that's > 2× train suggests overfitting fluke

**Rollback rules:**
- If OOS at slippage 0.25 is negative for every cell, the strategy
  is paper-only edge — do not promote. Document in
  `vault/_meta/analysis/` as a lesson and retire the candidate.
- If OOS holds at slip=0 but fails at slip=0.25, the strategy is
  slippage-intolerant by design. Either redesign with wider stops
  (see `gap_fill_wide` for an example) or retire.

---

## Stage 4 — STRESS TEST

**What happens:** `scripts/stress_test.py` runs the candidate cells
under adversarial conditions: 2× expected slippage, half liquidity,
1.5× ATR. Each scenario produces a degradation pct vs baseline.

**Output artifact:** `vault/research/stress_tests/<date>_stress_test.md`

**Promotion gate to PAPER LIVE:**
- PASS at the `low_slip` (0.25 ticks/side) scenario (status: PASS,
  meaning < 30% degradation from baseline)
- WARN allowed at `mid_slip` (0.5 ticks/side); FAIL at `mid_slip`
  is acceptable only if the cell's `breakeven_slip_ticks` was already
  near 0.25 from walk-forward (then 0.5 is expected to hurt)
- Sign-flip (positive baseline → negative under any reasonable
  stress) is automatic disqualification

**Rollback rules:**
- Sign-flip → don't promote. Cell goes to shadow indefinitely.
- Multiple FAIL scenarios → demote to "research only" status; the
  strategy may still be useful for other instruments but not in the
  current locked universe.

---

## Stage 5 — PAPER LIVE

**What happens:** the cell is added to a "paper" allowlist that the
trader scans + emits signals for, but `FUND_MODE=paper` prevents
actual order placement. Fills are simulated using the same logic as
the backtest engine. Run for at least 5 trading days.

**Output artifact:** `vault/research/paper_live/<cell>_<date>.md` —
trade-by-trade comparison of paper-fill behavior to backtest
expectations.

**Promotion gate to LIVE SMALL:**
- Paper fills produce expectancy within ±20% of walk-forward OOS dollar
  prediction (at slippage 0.25)
- No paper trades that would have violated the risk gate (they should
  have been blocked, not filled)
- ≥ 5 paper fills accumulated

**Rollback rules:**
- If paper expectancy diverges > 50% from walk-forward, the backtest
  doesn't model live order mechanics correctly. Investigate before
  paper resume.
- If a paper trade fires that should have been blocked by the risk
  gate, that's a gate bug — fix gate first, restart paper.

---

## Stage 6 — LIVE SMALL

**What happens:** the cell is added to `live_allowlist` with
`max_contracts_per_trade = 1` (already the project default per
`risk_limits.yaml:per_trade`). Real orders fire on real capital.
Trade size is small by design — the goal is calibration, not P&L.

**Output artifact:** continuous via:
- `scripts/slippage_tracker.py` — per-cell slippage per fill
- `scripts/slippage_tracker_extended.py` — per-symbol/hour/regime
  breakdowns with variance triggers
- `scripts/cost_ledger.py` — daily NET P&L
- `scripts/cell_auto_promote.py` — promote/demote rules consume the
  measured live data

**Promotion gate to LIVE FULL:**
- ≥ 30 live fills accumulated
- Mean live R within ±0.5R of OOS prediction
- Measured slippage within ±0.10 ticks/side of prediction (per
  `slippage_calibration.py:PREDICTED_PER_SYMBOL_TICKS`)
- No CRITICAL variance flags from `slippage_tracker_extended.py`

**Rollback rules:**
- If live R deviates from OOS by > 1R after 10+ fills, demote to
  shadow per `cell_auto_promote.py` rules.
- If measured slippage > predicted by > 0.20 ticks/side over 10+
  fills, the cell is more slippage-exposed than the calibration
  assumed. Demote pending recalibration.
- If a single live trade hits the LOSS_TIER_HARD_CAP ($200 software
  belt), pause the cell for 24h pending review.

**LIVE SMALL is the longest stage.** Most strategies will live here for
weeks or months. That's intentional — calibration takes time.

---

## Stage 7 — LIVE FULL

**What happens:** the cell graduates to full sizing per
`risk_limits.yaml`. Sizing increases (typically 2-3 contracts on the
$50K Combine; more on the funded account post-pass) but other gates
remain.

**Currently not in scope on the Combine.** Combine rules cap position
to 5 contracts total; "full" sizing in the Combine context means 1-2
contracts per trade. Real LIVE FULL only opens up post-Combine on the
funded account.

**Promotion gate to LIVE FULL:**
- ≥ 100 live fills with consistent edge (live R vs OOS R variance
  < 0.3R)
- Sustained positive net dollars after fees + slippage + fixed cost
  for ≥ 4 weeks
- No CRITICAL variance flags in the past 4 weeks

**Rollback rules:**
- Same as LIVE SMALL but tighter — any decay is expensive at full
  sizing. Demote on first 3-consecutive-loser streak instead of
  the LIVE SMALL rule of negative cell expectancy with streak ≥ 3.

---

## Continuous re-validation (post LIVE FULL)

Even at LIVE FULL, the brain keeps testing. Every Sunday's session
runs:

1. `slippage_calibration.py` — refresh measured slippage
2. `cell_auto_promote.py` — demote any cell that decays
3. `cost_ledger.py` — confirm net dollars match weekly target
4. `live_vs_oos_tracker.py` — compare per-cell live R to OOS prediction

If any cell diverges from prediction beyond the variance trigger, the
brain auto-demotes per `cell_auto_promote.py` — no manual intervention.

---

## How currently-live cells map to these stages

The 16 cells in `live_strategies_filter` (gap_fill on ZN/ZT/ZB/ZF, all
sessions both sides) were promoted before this doc existed. They are
*nominally* at **LIVE SMALL** stage. As of 2026-05-09 they have **0
live fills** — the Sunday 5/10 17:00 ET kickstart is their first real
test against the LIVE SMALL gate.

After 30 fills, they'll either:
- meet the LIVE FULL gate and stay live, or
- show variance > triggers and auto-demote to shadow

The strategies I shipped this week (`session_vwap_reversion`,
`range_consolidation_bounce`, `wide_session_drive`) are **at WALK-FORWARD
stage** awaiting param_sweep + stress_test + paper-live runs before any
consideration of live promotion. Per CC's 2026-05-08 reframe, no new
strategies move to LIVE until the existing 16 cells are validated.

## Variance is the headline metric

> Per the 2026-05-08 reframe: "Variance is the headline output, not P&L."

Whether the brain is doing what it predicted matters more than whether
the brain is making money. A losing strategy that loses *as predicted*
is a system that's working — the model is right. A winning strategy
that wins for unexpected reasons is a system to be skeptical of —
the model is wrong even if today's P&L is green.

The pipeline's promotion gates all key on **prediction match**, not on
P&L magnitude. That's deliberate. P&L is a consequence; prediction
match is the actual goal.

## How agents use this doc

CIO at session open: read this doc to know what stage each candidate
is at, decide whether today's session is calibration (cell at LIVE
SMALL) or production (LIVE FULL). The trading bias differs.

Risk Manager: reject any proposal that names a strategy not currently
at LIVE SMALL or LIVE FULL stage. The gate isn't soft.

Quant Researcher: when designing a new hypothesis, write the IDEA
artifact first. Don't go straight to BACKTEST.

Cowork + Claude Code: when promoting a cell across stages, update
`vault/_meta/cell_lifecycle.md` (TBD — companion doc to this one
listing each cell's current stage + last gate-pass date).

## Open questions

1. `vault/_meta/cell_lifecycle.md` — should it exist as a separate
   per-cell tracking doc, or is the audit trail in
   `vault/research/cell_promotion_log.md` enough? Decide after first
   round of cells reach gate decisions.
2. The IDEA → BACKTEST gate is currently subjective. Should it have
   a structured template (frontmatter fields)? Probably yes after
   we accumulate 5+ hypothesis docs.
3. PAPER LIVE stage requires a paper-fill simulator that matches the
   live broker's behavior. The PaperAdapter stub in
   `tools/broker_adapter.py` is the architectural placeholder; an
   actual implementation is queued P5 (post-Combine).

## See also

- [[learning_system]] — the lesson-confidence ladder this pipeline
  composes with.
- [[cowork_coordination]] — coordination rules including the new
  Prediction + Measurement + Variance triple every backlog item must
  carry.
- [[../research/slippage_mitigation_playbook]] — the slippage levers
  that gate stages 4-6.
- [[analysis/2026-05-07_lesson_meta_patterns]] — Pattern A, B, C
  failure modes that this pipeline is designed to catch.
