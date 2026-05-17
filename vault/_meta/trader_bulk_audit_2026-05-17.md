---
type: audit
status: ACTIVE
date: 2026-05-17
purpose: Trader-bulkiness audit per standing user directive (continuous trim, ceiling 700 / target <600)
---

# Trader bulkiness audit — 2026-05-17

**Current state:** `scripts/live_trader.py` = **784 lines** (12% over the 700 ceiling, 31% over the <600 target).

Triggered by user direction after tick_protect ship: "make sure it is not too bulky, remember anything extra can be in the brain."

## Function-by-function

| Function | Lines | Verdict |
|---|---|---|
| `_log` | 8 | keep (trader-local logging) |
| `is_halted` | 18 | could move to `tools/halt_check.py`; tiny enough to leave |
| `dll_breached` | 47 | **extract** — pure validator over a snapshot dict |
| `compute_signal_risk_usd` | 19 | **extract** — pure math |
| `signal_passes_max_risk_gate` | 28 | **extract** — pure validator |
| `projected_dll_breach` | 36 | **extract** — pure validator |
| `signal_passes_min_r_gate` | 56 | **extract** — pure validator |
| `place_bracket` | 18 | keep (broker IO + entry-fill confirmation) |
| `enforce_loss_cap` | 19 | candidate (orchestration over profit_protect) |
| `cleanup_orphan_brackets` | 9 | candidate |
| `recent_thesis_for` | 18 | **extract** — pure DB query helper |
| `consume_pending_signals` | 169 | core orchestration — keep but consider sub-helpers |
| `_position_polling_loop` | 95 | core (grew today with tick_protect wiring) — keep |
| `main` | 96 | bootstrap — keep |

## Extraction plan (proposed for next session)

**Target file:** `tools/signal_validators.py` — house pure signal/snapshot validation logic that the trader (and brain) both consume.

**Extract:**
- `compute_signal_risk_usd`
- `signal_passes_max_risk_gate`
- `signal_passes_min_r_gate`
- `dll_breached`
- `projected_dll_breach`
- `recent_thesis_for` (rename to clearer name, or put in `tools/thesis_log.py`)

**Estimated reduction:** 186 lines → live_trader becomes ~598 lines (right at the <600 target).

**Why this is safe:** these functions are PURE (no broker IO, no mutable state). The trader imports them; the brain can import them too. No behavior change.

## Deferred items

- `is_halted` — small, trader-local read. Leave.
- `enforce_loss_cap` / `cleanup_orphan_brackets` — orchestration over profit_protect; would need tighter test coverage before extracting.
- `consume_pending_signals` (169 lines) — the orchestration heart of the trader. Splitting into sub-helpers is a separate, bigger task.

## Status

- AUDIT: done, captured here
- IMPLEMENTATION: DEFERRED — not safe to refactor minutes before Globex reopen (5:00 PM ET 2026-05-17)
- NEXT: ship after first live trading day with tick_protect, when we can verify any regression isolated from the trim
