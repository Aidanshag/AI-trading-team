---
name: Multi-account scaling is the long-term plan, not single-account alpha
description: User strategic vision 2026-05-09 — pass single Combine first, then SCALE BY REPLICATING across multiple Topstep accounts via copy-trading
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User strategic vision (2026-05-09):

> "I could do 5-10% a year because hopefully once I pass the combine and am
> confident enough in the strategy, I will open multiple Topstep accounts
> and copy trade across them."

> "The multi account framing will come at some point, but doesn't matter
> until we have a successful single account first."

This is the actual fund design, and it changes what "good enough" means.

## The mental model

| What changes | What stays the same |
|---|---|
| Target return per account → 5-10%/yr (realistic) | Need ONE reliable strategy first |
| Path to scale → MORE accounts at same size | Pass single Combine before anything else |
| Optimization target → reliability + replicability | Slippage management is still critical |
| Long-term P&L → linear in account count | Single-account engineering quality is the bottleneck |

## What this means for current work

**Phase 1 (NOW through ~30 days post-Combine pass)**: single-account focus.
- Pass the Combine on one account
- Build measurement, validation, reliability infrastructure
- Prove the strategy actually works in production at one account

**Phase 2 (~3-6 months out)**: replication infrastructure.
- Multi-account orchestrator pattern
- Per-account isolation (each has own DLL/TDD tracking)
- Cross-account coordination (prevent over-exposure)
- Bootstrap funding: pass Combine 1 → use FA1 income to fund Combine 2 → etc.

**Phase 3 (~6-12 months out)**: at-scale operation.
- 5-10 accounts running same strategy with possible decorrelation tweaks
- Fund-level dashboard across accounts
- Risk parity at fund level, not per-trade

## Critical questions for Phase 2 (research before building)

1. **Does Topstep allow copy-trading across accounts?** Some prop firms explicitly ban this.
2. **Simultaneous Combines policy?**
3. **Cross-account aggregation rules?**
4. **Tax structure** — each account separate or aggregated?

These need answers BEFORE Phase 2 architecture. Saving 1-2 hours of policy research will avoid wasted engineering.

## Risk concentration warning (for Phase 2)

5 accounts running the same strategy = **perfectly correlated**. One bad day takes down all 5.

Mitigation options for Phase 2:
- Vary parameters per account (account A: gap_fill_wide on treasuries; account B: future pairs strategy; account C: multi-day swing)
- Stagger account activation (3 active, 2 in cooldown)

## How to apply this in current work

When making engineering decisions, ask: **"would this design support 10 accounts, or only 1?"**
- Same answer for both → great, go ahead
- Different → document the multi-account refactor as a Phase 2 followup, but don't build it now
- Engineering complexity that ONLY makes sense for multi-account → defer to Phase 2

The current `live_trader.py` is single-account by design and that's fine. The brain (validation, allowlist, lessons) is account-agnostic and works for both. Phase 2 adds an orchestrator layer above the trader.

## Why this changes "good enough"

Per-account 5-10%/yr is now ENOUGH because the scale comes from N. This shifts what we optimize for:
- **Reliability >> peak performance**. A 7%/yr strategy that NEVER blows up is better than 30%/yr strategy that occasionally gives back 50%.
- **Replicability** — strategy must be deterministic, copy-able to a fresh account
- **Operational discipline** — must survive multi-account complexity later

This is *exactly* the right way to scale on Topstep's structure.
