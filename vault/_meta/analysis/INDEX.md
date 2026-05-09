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
| #5 | broker_adapter | _(deferred)_ | Multi-platform abstraction; defer until Combine passes. |

## Promotion log

When an analysis piece gets promoted (to a lesson, config change,
thesis update, or validation gate), append a row here. This makes the
"analysis → learning" lifecycle traceable.

| Promoted on | Source piece | Promoted to | Note |
|---|---|---|---|
| _(none yet)_ | | | |
