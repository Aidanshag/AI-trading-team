---
type: meta_index
updated: 2026-05-07
---

# Analysis index — newest first

Append entries when new analysis pieces are added. When a piece's
`status:` field changes (promoted, superseded, archived), update the
row here too.

| Date | Slug | Author | Confidence | Status | Topic |
|---|---|---|---|---|---|
| 2026-05-07 | lesson_meta_patterns | Cowork | PATTERN | open | Two structural design principles distilled from the 4 lessons: (A) fail-silent defaults, (B) wrong-context validation. Both at n=2; promote to RULE on a third incident. |
| 2026-05-07 | risk_event_distribution | Cowork | ADVISORY | open | What the gate stack is actually doing — fee-budget waste, OCO race symbol pattern, network-instability recurrence, hour-of-day proof that the regime gate worked. |
| 2026-05-07 | treasury_cell_decay_read | Cowork | ADVISORY | open | Live-vs-OOS read on the 14 active Treasury gap_fill cells; which deserve elevated scrutiny next 7 days. |
| 2026-05-08 | slippage_redirect_and_dollar_metrics | Cowork | PATTERN | open | Why R-multiples are slippage-blind, why the 2026-05-08_2304 sweep recommendation was parked, and Pattern C (metric blindness to deployment cost) added to the meta-patterns library. |

## Proposed changes (in `proposed_changes/`)

| Date | Slug | Status | Topic |
|---|---|---|---|
| 2026-05-08 | passive_entry_orders | PROPOSED | Slippage-reduction lever #1; passive limit at favorable side of spread for mean-reversion strategies (gap_fill family). Implementation sketch + OCO interaction notes; needs user/CC sign-off before merge. |
| 2026-05-08 | setup_confluence_requirement | PROPOSED | Require ≥1 of (vol>1.5×MA, ATR expansion, cross-strategy agreement) before firing in autonomous mode. A/B-friendly flag design; composes with passive entries. |

## Priority queue 2026-05-08 — backend brain upgrades (all 4 shipped)

Per Claude Code's queue in `cowork_coordination.md` (2026-05-08
section). Each script is documented in the coordination doc's
Cowork-response entry below.

| # | Script | Commit | Purpose |
|---:|---|---|---|
| #1 | `scripts/cell_auto_promote.py` + 17 tests | `834852f` + `b3a1f75` | Auto promote/demote cells from live evidence (atomic write). |
| #2 | `scripts/param_sweep.py` | `ce495bb` | Generic walk-forward sweeper; replaces per-sweep scripts. |
| #3 | `scripts/regime_classifier.py` | `729c1fb` | Per-bar vol/trend/news regime tags → state/regime_tags.json. |
| #4 | `scripts/cost_ledger.py` | `1ed3b4e` | Daily NET = gross − fees − slippage − fixed; rolling monthly ledger. |
| #5 | broker_adapter | _(now done as stub)_ | See "Weekly queue 2026-05-09" below — `tools/broker_adapter.py` |

## Weekly queue 2026-05-09 — validation infrastructure (all 4 shipped)

Per CC's 2026-05-08 ~23:30 UTC reframe ("close the gap between looks
great and actually works in production"). All ship with explicit
Prediction + Measurement + Variance trigger per the new coordination
rule.

| # | Script / Doc | Purpose |
|---:|---|---|
| #6 | `tools/broker_adapter.py` | Abstract BrokerAdapter + TopstepAdapter (delegates to projectx_client) + IBKR/Paper stubs. STUB ONLY; live_trader migration is a separate sign-off step. |
| #7 | `vault/_meta/hypothesis_to_live_pipeline.md` | 7-stage promotion process with explicit gates + rollback per stage. Variance-vs-prediction is the headline metric, not P&L. |
| #8 | `scripts/slippage_calibration.py` | Reads filled live_trader orders, writes `state/measured_slippage.json` for backtests to consume. MeasuredSlippage class with cell→symbol→default fallback chain. |
| #9 | `scripts/stress_test.py` | Runs every STRATEGY_REGISTRY entry × symbol × 6 scenarios (slippage 0/0.25/0.5/1.0 ticks/side, ATR mults). Status: PASS/WARN/FAIL with sign-flip detection. |
| (P0 NEW) | `scripts/slippage_tracker_extended.py` | Per-symbol/hour/regime breakdowns of fill slippage. Predictions baked in per CC's reframe. |

## Promotion log

When an analysis piece gets promoted (to a lesson, config change,
thesis update, or validation gate), append a row here. This makes the
"analysis → learning" lifecycle traceable.

| Promoted on | Source piece | Promoted to | Note |
|---|---|---|---|
| _(none yet)_ | | | |
