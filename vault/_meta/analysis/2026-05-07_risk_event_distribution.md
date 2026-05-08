---
type: analysis
date: 2026-05-07
author: Cowork (Claude)
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter]
sources:
  - state/fund.db (risk_events, orders, account_snapshots)
  - vault/lessons/2026-04-29_zn_orb_overnight_failed.md
  - vault/lessons/2026-05-05_profit_lock_disabled_overnight.md
  - vault/_meta/cowork_session_log.md
confidence: ADVISORY
status: open
---

# Risk-event distribution — what the gate stack is actually doing

## Headline

The post-incident safety rebuilds (2026-04-29 and 2026-05-05) **are
visibly working** — the risk-event distribution shifted from chaos
(naked-short blocks, per-symbol-max-contracts, can-trade-false warnings,
84+ events on a single day) to a clean tail of network blips and one
known software issue. **But there are two specific inefficiencies and
one open root-cause question** worth surfacing before they become
actual losses.

## Last 10 days, by day, top rules

| Date | Top rule | Severity | Count | Read |
|---|---|---|---:|---|
| 2026-04-28 | autonomy_spend_cap | block | 1 | Token-budget guard fired once. Normal. |
| **2026-04-29** | **naked_short_future** | block | **84** | The disaster day. Pre-snapshot-pipeline-fix. |
| 2026-04-29 | per_symbol_max_contracts | block | 21 | Same day. Per-symbol caps catching the storm. |
| 2026-04-29 | broker_can_trade_false | warn | 22 | Topstep server-side flagged; gate honored it. |
| 2026-04-30 | globex_reopen_buffer_block | info | 6 | Routine. |
| 2026-05-01 | thin_tape_regime_block | info | 26 | Regime gate doing its job overnight. |
| 2026-05-04 | session_cutoff | block | 9 | Pre-MNQ/GC fires; gate caught session edge. |
| 2026-05-04 | bracket_oco_misdirected_leg | breach | 2 | OCO race; software issue (see §B below). |
| **2026-05-05** | **daily_fee_budget_exhausted** | block | **224** | Spike from one bad day (see §A below). |
| 2026-05-06 | per_symbol_burn_warn | warn | 328 | Log-noise flood; fixed yesterday session. |
| 2026-05-06 | bracket_oco_misdirected_leg | breach | 5 | OCO race recurrence (see §B). |
| **2026-05-07** | **snapshot_capture_failed** | warn | **6** | Network dropouts only. (see §C). |

The pattern: rebuilds working, residual issues are now narrow.

## §A — The 5/5 daily_fee_budget_exhausted spike

**224 firings in one session.** All on 2026-05-05. The gate did exactly
what it should — refused new orders once the daily fee budget was
spent — but firing 224 times means the auto_trader's scan loop
re-evaluated every symbol on every 5-minute tick AFTER the cap was
already hit. Each re-evaluation ran through the full risk gate stack
to land back at "blocked, fee budget exhausted." That's pure scan-loop
waste. It also runs up the API budget on agent wakes that are
unactionable.

**Recommendation (PATTERN, n=1):** add a short-circuit at the top of
`scan_once` — if today's fee budget is exhausted (cheap query), exit
early before the universe loop. The hard gate stays in place as the
floor; this is just removing wasted cycles. **Expected savings:** ~1-3¢
of API spend per session on bad days, plus cleaner risk_events table.

## §B — bracket_oco_misdirected_leg breaches

9 events total over 5/4–5/6, severity=`breach`. All show the same
shape: `expected_pos: long/short, actual_pos: null`. Decoded: the
trader placed a protective stop order, but no corresponding entry ever
filled to open the position the stop was protecting. The OCO race
detector caught the orphan and cancelled it.

**Distribution by symbol:**
- MNQ: 2 events (5/4 evening)
- MCL: 4 events (5/5 + 5/6)
- GC: 2 events
- NG: 1 event (5/6 morning, the last pre-lockdown trade)

**Zero on Treasuries.** This is a pre-lockdown-universe pattern. May or
may not recur on `gap_fill | ZN/ZT/ZB/ZF` once those start firing —
the OCO race is at the broker-API layer (entry fill confirmation race
with stop-leg placement), not strategy-specific. It will likely recur
in some form when Treasury fires happen. Worth confirming.

**Recommendation (ADVISORY):** when the first Treasury gap_fill cell
fires, monitor for this event for the first 5 fires. If it recurs at
the same rate (~5/100 trades), the OCO race timing is symbol-agnostic
and the existing detector + cancel logic is the right floor. If it
recurs at higher rate on Treasuries (faster fills or different
broker-side timing), Treasury cells deserve their own bracket-placement
flow.

## §C — Today's network instability (snapshot_capture_failed × 6)

All 6 today are network-layer errors:
- 4 × `[Errno 11001] getaddrinfo failed` (DNS resolution failure)
- 1 × `The read operation timed out` (slow response)
- 1 × `getaddrinfo failed` with `degraded_heartbeat: true` (Claude
  Code's 13:40 EDT fix engaging — wrote synthetic can_trade=False
  snapshot instead of dying)

**This is the second day in a row showing this pattern.** Yesterday
(5/6) had 3 events; today already 6 by 19:11 UTC. The wifi/DNS
reliability issue Claude Code diagnosed is recurring. The
degraded-heartbeat fix is the right defensive layer; the network
itself isn't being investigated.

**Recommendation (PATTERN, n=2 days):** if the trader is going to run
24/5 with auto-restart, the host machine should have:
- Wired ethernet preferred over wifi for the trading workstation, or
- A network-watchdog that pre-warns when DNS/connection latency
  degrades, before a snapshot fails
This is operations-layer, not code. Worth a sentence in the lessons
or operational ops doc — "DNS failures degraded heartbeats are a
real-world recurring event."

## §D — Hour-of-day distribution proves the regime gate worked

Trade-placement distribution (UTC) across the entire ~120-trade
history:

```
00:00  ##
02:00  #
03:00  ####
04:00  ################################################################################  (80 trades = 67%)
05:00  #############
06:00  ###
07:00  ##
09:00  #
13:00  #
18:00  ##
22:00  ##
23:00  ##
```

The 04:00 UTC bar is the 2026-04-29 incident window. Post-incident,
the `thin_tape_regime_block` gate (21:00-04:00 ET = 01:00-08:00 UTC)
catches anything trying to fire in this window. Validation: all 26
of the 5/1 thin_tape_regime_block events fall in 02:00-07:00 UTC.

**This is a textbook post-incident learning trace.** The gate works.

## What the system should do with this analysis

1. **Implement the §A short-circuit** (low risk, in `auto_trader.py`,
   not HIGH_RISK_FILES). Cleaner logs, smaller API spend, no behavior
   change beyond reducing waste.
2. **Watch the §B OCO pattern on Treasury cells** when they first fire.
   Tag observations toward whether this is broker-API-symbol-specific
   or universal.
3. **Document the §C network-reliability pattern** as a real-world
   ops issue. Cowork's analysis library has it now; consider promoting
   to lesson if it recurs a 3rd day.
4. **Cite §D in the next post-mortem** of any incident. The pre/post
   distribution shift is a clean evidence example for "the rebuild
   actually worked" — useful when explaining the system's safety
   posture.

## Confidence and lifecycle

ADVISORY. Each of §A through §C has n=1 to n=2 observations. Promotes
to PATTERN if (A) the fee-budget short-circuit gets implemented and
the metric proves out, (B) OCO race recurs on Treasury fires, (C)
network errors hit a third day.

## See also

- [[2026-05-07_treasury_cell_decay_read]] — sister piece on the
  live-vs-OOS gap.
- [[../../lessons/2026-04-29_zn_orb_overnight_failed]] — origin of the
  thin-tape regime gate.
- [[../../lessons/2026-05-05_profit_lock_disabled_overnight]] — origin
  of the unrealized-PL fix and degraded-heartbeat pattern.
- [[../cowork_coordination]] — handoff protocol Claude Code wrote.
