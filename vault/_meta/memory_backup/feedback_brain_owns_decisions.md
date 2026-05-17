---
name: feedback-brain-owns-decisions
description: "Standing rule established 2026-05-13. Anything that's not pure order placement belongs in the brain, not the trader. Twice now (auto_trader→live_trader 5/11, live_trader→queue-consumer 5/13) we've had to rip decision logic out of the trader after it caused problems."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b979f9ba-f40d-4fdc-8d30-1f25c42d62e2
---

# Brain owns decisions; trader only places orders.

**Rule:** new code that is NOT pure order placement goes in the brain
(`scripts/brain_signaler.py` + `tools/brain_logic.py`), never the trader
(`scripts/live_trader.py`).

**Why:** the trader has been simplified twice in two weeks:
- 2026-05-08: extracted utilities to `tools/*` ("continuous trim")
- 2026-05-11: auto_trader (2,900 LOC) → live_trader (~1,300 LOC) — but
  in that cut the internal DLL, defensive ladder, and per-trade risk
  cap got dropped on the floor. That regression caused the −$1,005 GC
  overnight loss on 2026-05-12/13.
- 2026-05-13: live_trader (1,450 LOC) → queue consumer (~300 LOC end
  state). Brain now owns strategy execution, session filtering, regime
  filtering, cooldowns, cell allowlist, news proximity. Trader reads
  signals from `state/pending_signals.json` and applies last-mile
  safety gates.

Pattern: every time decision logic accumulates in the trader, a bug
hides somewhere in it. Smaller trader = smaller bug surface = fewer
incidents.

**How to apply:**

When adding new capability, ask: "is this DECIDING something, or
PLACING something?"

- DECIDING → brain (`scripts/brain_signaler.py` + helpers in
  `tools/brain_logic.py`):
  - New strategies
  - New session/regime/news filters
  - New cell allowlist semantics
  - Cooldown / dedup logic
  - Position sizing models
  - Signal-quality scoring
- PLACING / GATING → trader (`scripts/live_trader.py`):
  - `place_bracket` and broker IO
  - Last-mile safety floors that MUST run at order placement
    (max_signal_risk, internal_dll, projection_dll, min_signal_R) —
    defense in depth against brain bugs
  - Position polling (loss cap, profit lock)
  - Snapshot heartbeat

If a new "feature" doesn't fit cleanly in either bucket, that's a
smell — it probably belongs in the brain.

**Ceiling reminder:** trader target stays <600 lines after the legacy
cleanup on 2026-05-16 (Friday). Anything that pushes it back over the
ceiling means we're putting brain work in the trader again.

Related: [[feedback-two-layer-architecture]],
[[feedback-continuous-trader-trim]],
[[project-2026-05-13-overnight-dll-breach]].
