---
name: Continuously trim trader to keep it as the knife
description: User standing directive 2026-05-08 — every session must look for non-core code in scripts/live_trader.py and move it to tools/ or brain
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User standing directive (2026-05-08): the simplified trader (`scripts/live_trader.py`) must stay as **the knife** — minimal, fast, only direct execution logic. Every session and every Cowork cycle should actively look for code that doesn't belong in execution and migrate it elsewhere.

**Why:** the v1 trader bloated to 2,929 lines and accumulated bugs faster than they could be fixed. The simplification cut it to ~700 lines but features keep getting added. Without continuous trimming pressure, the same bloat returns.

**How to apply:**

1. **Every session, audit the trader for trim candidates.** Run `wc -l scripts/live_trader.py` at session start. If > 700, audit aggressively.

2. **What's "core" (must stay in trader):**
   - The scan loop (`scan_once`)
   - Direct broker actions (`place_bracket`, `enforce_loss_cap`, `cleanup_orphan_brackets`)
   - Hard kill gates (`is_halted`, `dll_breached` — these MUST be in-process so they fire even if external services fail)
   - Signal detection per scan (`find_latest_signal`)
   - The CLI entry (`main`)

3. **What can move out:**
   - Pure utility helpers (date/time, YAML loading, tick math) → `tools/trader_utils.py` (already extracted 2026-05-08)
   - Snapshot capture logic (broker state observer) → `tools/snapshot_writer.py` (queued)
   - DB query helpers (cooldown lookups, daily-count) → `tools/trade_state.py`
   - Bar fetching → `tools/bar_fetcher.py`
   - Brain interface readers (`load_live_cells`) → `tools/brain_interface.py`

4. **Before extracting, verify:**
   - All 25 unit tests still pass
   - `live_trader --once --dry-run` produces identical output before/after
   - The extracted module is single-purpose and imports cleanly

5. **Aspirational ceiling:** trader < 500 lines. Current floor: 700 lines (with cleanup + Sunday-reopen gates). Target: < 600 lines after snapshot extraction.

6. **Cowork coordination:** the trim work is shared between CLI Claude and Cowork sessions. Both should look for trim opportunities. The improvement_backlog.md tracks queued extractions.
