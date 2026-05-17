---
type: audit
status: VERIFIED CLEAN
date: 2026-05-17
purpose: Brain-side bulkiness audit (companion to trader audit)
---

# Brain bulkiness audit — 2026-05-17

Per standing rule "continuously trim trader, anything extra goes to brain." Today's trader trim (784 → 659 lines) raised the question: is the brain itself over the same ceiling, indicating a structural problem?

## Current state — HEALTHY

| File | Lines | Verdict |
|---|---|---|
| `scripts/brain_signaler.py` | 218 | well under any ceiling |
| `tools/brain_logic.py` | 293 | well under any ceiling |
| **Total brain** | **511** | healthy — no trim needed |

## Function breakdown — brain_signaler.py

| Function | Lines | Verdict |
|---|---|---|
| `_log` | 5 | keep |
| `_fetch_bars` | 4 (thin wrapper) | keep |
| `scan_once` | 113 | core orchestration; appropriate size for the work it does |
| `main` | ~27 | bootstrap; keep |

## Function breakdown — brain_logic.py

| Function | Lines | Verdict |
|---|---|---|
| `_now_utc` | 4 | keep |
| `load_live_cells` | 12 | keep |
| `session_now_utc` | 14 | keep |
| `_load_calendar_events` | 74 | candidate for extraction to `tools/calendar_cache.py` if it grows |
| `news_proximity_for` | 30 | keep |
| `current_regime` | 68 | keep (regime classifier — core brain concern) |
| `cell_passes_regime_filter` | 15 | keep |
| `find_latest_signal` | ~43 | keep |

## What this means

The trader-trim work today (`signal_validators` extraction) is the RIGHT direction: pull pure validation logic out of the execution layer into shared modules that both the trader (last-mile defense) and the brain (pre-emission checks) can import. Total trader + brain = 1170 lines now (was 1077 trader + 511 brain when we started the trim today). The extraction added ~100 lines of test/scaffolding, which is the right kind of growth.

The next time the trader trends back up to >700 lines, the playbook is the same: identify pure functions, extract them to `tools/*.py`, re-export with `from ... import` to preserve external API.

## Action items

None. Brain is healthy as-is. The audit is filed for the standing record.
