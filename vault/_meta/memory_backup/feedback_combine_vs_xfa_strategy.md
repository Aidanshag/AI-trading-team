---
name: feedback-combine-vs-xfa-strategy
description: "Stage-aware sizing rule established 2026-05-13. Combine = MGC + consistency profile; GC re-introduction deferred until XFA + real capital base. Don't raise MAX_SIGNAL_RISK_USD."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b979f9ba-f40d-4fdc-8d30-1f25c42d62e2
---

# Combine vs XFA — sizing and symbol selection differ by stage

**Rule:** the Combine and XFA phases have different success criteria; the
fund's sizing and symbol choices must match the phase it's in.

## Combine ($50K, pre-funding)

- **Goal:** pass the Combine. Topstep is watching for **consistency**, not
  heroics. The 50% single-day consistency rule punishes outsized winners —
  a $2,600 day actively HURTS if subsequent days are flat.
- **Target P&L profile:** $50-200/day, every day. Not big swings.
- **Symbol bias:** **MGC over GC.** Same price-pattern edge, 1/10 dollar
  risk per tick, fits comfortably inside the $150 max-risk cap, produces
  the steady small-winner profile the Combine rewards.
- **Status of GC cells:** kept in `live_allowlist` but `experimental: true`
  (shadow-mode). They record what would have happened for comparison
  data, but no real fills.
- **Cap discipline:** **DO NOT raise `MAX_SIGNAL_RISK_USD` above $150**
  for the Combine. The cap is the encoded lesson from 2026-05-12 (-$1,005
  GC overnight). Every dollar raised is a dollar of single-trade downside.
  Lower the cap if anything; never raise it.

## XFA (post-funding, real capital base)

- **Goal:** sustain payout-eligible profit on real money. Different from
  passing the Combine — payout cycles reward consistent monthly P&L over
  many sessions, not a single qualifying month.
- **Symbol re-introduction:** GC can be re-promoted to full-size IF
  - The trader has demonstrated multi-account-scaling discipline (Phase 2
    in `vault/_meta/strategic_roadmap.md`)
  - There's a real capital base — the fund is not surviving session-to-
    session on a single account
  - The internal DLL has been retuned to the new account-size context
- **Sizing rule on re-introduction:** start at micro (MGC), scale to GC
  only after a clean N-session window with MGC at the new tier.

## Why this isn't "trade more aggressively when funded"

It's the opposite. The Combine phase is **risk-bounded** because a blown
Combine = $165 wasted + restart. The XFA phase is **risk-tolerant**
because real capital provides absorptive capacity AND payout cycles need
volatility tolerance.

Reversing it (heroic Combine, conservative XFA) is the failure mode where
you spend $165 each time you blow a Combine and never get to XFA.

## What to do when a future session tempts otherwise

Future-Claude or future-user might propose:
- "Let's just raise the cap for GC, the win history is good" → reject;
  bounded-downside is the architecture
- "MGC is too small to matter for Combine pass" → reject; consistency
  matters more than per-trade size for the 50% rule
- "We should add GC back during Combine because MGC isn't catching enough"
  → if MGC genuinely under-delivers, add a regime-aware GC carve-out
  (only when ATR is in the bottom quartile = stops naturally narrow),
  not a blanket re-enable

Related: [[feedback-multi-account-scaling]],
[[feedback-brain-owns-decisions]],
[[project-2026-05-13-overnight-dll-breach]].
