---
type: meta
status: active
applies_to: [all]
updated: 2026-04-29
---

# Learning System — how the team gets smarter from losses

The team's edge over the average retail trader is **not better setups** — it's **systematic learning from every loss**. Most retail traders never do post-mortems. Institutional desks always do. This document is the framework.

## Core principle

**Every losing trade is a teacher. Every repeat of the same mistake is malpractice.**

Description without prescription is incomplete. Prescription without statistics is overfitting. The learning loop must do both.

## Architecture

```
TRADE CLOSES (loss)
    │
    ▼
auto-trigger post-mortem
    │
    ▼
LESSON DRAFTED (Quant Researcher / dedicated reviewer)
  - what happened
  - root cause(s)
  - failure category tag
  - corrective action proposal
  - confidence: ADVISORY (n=1)
    │
    ▼
Stored in vault/lessons/{date}_{symbol}_{strategy}_{outcome}.md
    │
    ├─► At every analyst wake: SURFACE relevant lessons
    │     (matched by symbol, strategy, regime, time-of-day, etc)
    │
    └─► At weekly review:
         - Aggregate by failure category
         - If n≥3 of same category → PROMOTE to firm rule
         - Lessons older than 30d without recurrence → EXPIRE
         - Rules that consistently save money → make HARD GATES
```

## Failure category taxonomy

Tag every lesson with one or more of these:

| Tag | Description | Example |
|---|---|---|
| `time_decay` | Signal stale by time it filled | ZN ORB filled 10h after RTH signal |
| `liquidity_regime_mismatch` | Volume conditions different at fill vs signal | RTH-baseline confirmation applied to overnight thin tape |
| `no_catalyst` | Pure-technical thesis without flow driver | Counter-trend in choppy regime |
| `stop_inside_noise` | Stop too tight relative to ATR | Got noise-swept |
| `single_actor_risk` | Thin liquidity = one trader can move price | 215-contract sell crashed our ZN stop |
| `consistency_breach_risk` | One outsized day risks Combine consistency rule | A $1,500 day on path to $3K target |
| `correlation_stack` | Multiple trades = one bet (under-hedged) | Long crude + long energy + long copper |
| `regime_flip_missed` | Macro changed but trade didn't account for it | FOMC dovish, kept short rates |
| `entry_mechanic_wrong` | Used stop-entry where immediate-fill was better (or vice versa) | Stop-entry on thin tape → fakeout |
| `early_exit_missed` | Should have taken profit/cut loss before bracket fired | +0.7R reversed; rode all the way to stop |
| `oversized_risk` | Risk per trade too large for conviction tier | $250 risk on low-conviction setup |
| `data_gap` | Decided without key data; trade based on incomplete info | No live news vendor; missed hawkish Fed speech |

## Confidence levels

| Level | Meaning | Effect |
|---|---|---|
| **ADVISORY** (n=1) | Single occurrence; descriptive, not prescriptive | Surfaced at wake but not blocking |
| **PATTERN** (n=2) | Second similar failure; warning weight | Surfaced + flagged at wake |
| **RULE** (n≥3) | Pattern confirmed; promoted to firm guidance | Surfaced + cited in Risk Manager checks |
| **HARD GATE** (n≥5 + clear cost savings) | Codified as a check in `risk_limits.yaml` | Risk hook blocks the failure mode |

## Lesson lifecycle (TTL)

- **Default TTL: 30 days** for ADVISORY lessons.
- **Refresh:** if the same category recurs, TTL resets.
- **Promotion:** at 30 days, n=1 lessons that haven't recurred get archived to `vault/lessons/_archive/` (still searchable, not actively surfaced).
- **Permanent:** PATTERN, RULE, and HARD GATE lessons stay active until explicitly retired.

This prevents the "10,000 contradictory rules" problem.

## Surfacing at analyst wake

Every analyst's preamble should include the most relevant active lessons at wake time, matched by:
- Symbol (sector/instrument-specific lessons)
- Strategy name (strategy-specific failure modes)
- Time-of-day / session (overnight-thin-liquidity lessons surface for overnight wakes)
- Recency (within last 7 days at higher priority)

The orchestrator's `_team_preamble()` should append a "Recent lessons (active)" block when the wake matches a known pattern.

## Counterfactual tracking

When an analyst cites a lesson in their NO_TRADE rationale (e.g., "skipping this ORB per `2026-04-29_zn_orb_overnight_failed`"), log it as `kind=lesson_applied` in the decisions table. Then periodically:

1. For each `lesson_applied` event, compare current price vs the proposed entry over the next N hours.
2. Compute expected outcome had the trade been taken.
3. If lessons consistently save money → hardened to RULE → eventually HARD GATE.
4. If lessons consistently miss winning trades → DEMOTE / REVISE.

This is the only honest way to know whether the learning loop creates edge or destroys it.

## Weekly lesson review (CIO + Compliance)

Every Sunday:
1. List all lessons added this week.
2. List all lesson-applied events; compute counterfactual P&L.
3. Identify any 2nd or 3rd occurrences of same category → promote.
4. Identify any 30-day-stale lessons → archive.
5. Identify any RULE-level lessons that consistently saved money → propose codification as HARD GATE.

## Why this works

Markets change. Traders learn. The team has the same memory. **A losing trade that produces a lesson — and the lesson actually changes future behavior — is more valuable than a winning trade.**

A winning trade pays you once. A correctly-applied lesson pays you every time the same pattern recurs.
