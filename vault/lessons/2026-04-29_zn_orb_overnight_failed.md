---
type: lesson
date: 2026-04-29
trade_id: 2897285454
symbol: ZN
strategy: opening_range_breakout
outcome: LOSS
loss_usd: -62.50
gross_loss_usd: -63.82  # includes commission/fees
status: closed
applies_to: [Edge Hunter, Quant Researcher, Index/Macro Analyst, Rates Analyst, Portfolio Manager, Risk Manager, Execution Trader]
---

# Lesson: ZN ORB breakout failed in overnight thin liquidity

## What happened

| Item | Value |
|---|---|
| Strategy | `opening_range_breakout` |
| Setup signal time | 13:45 UTC (RTH) — 30-min ORB high formed at 110.921875 |
| Entry order placed | 00:00 UTC (autonomous re-eval, +10h after signal) |
| Fill time | 00:04 UTC at 110.921875 |
| Stop hit | ~01:14 UTC at ~110.86 |
| Outcome | −$62.50 max loss + $1.32 fees = **−$63.82 net** |
| Time in trade | 70 minutes |

## Sequence of events

1. **13:45 UTC**: 30-min ORB high formed at 110.921875 during RTH on 41,692-contract bar (3× baseline volume — Hawkes intensity confirmed institutional flow).
2. **20:30 UTC**: Quant Researcher published thesis (decision 132): long ORB breakout above 110.921875, stop 110.859375, target 111.046875.
3. **22:00 UTC**: Daily maintenance break. Order rejected. Autonomous borderline-pass at 22:05 UTC because price had dropped to 110.859375 (at-stop level).
4. **00:00 UTC**: Autonomous re-eval (Risk Manager) re-approved when ZN rebounded to 110.921875. Buy-stop placed.
5. **00:04 UTC**: Buy-stop **filled at 110.921875** (took only 4 minutes — but on thin volume).
6. **00:00–01:14 UTC**: Position drifted in tight range (110.875–110.92), no follow-through buying.
7. **01:14 UTC**: Single 215-contract sell order crashed price through 110.859375 stop. Exit at ~110.86.

## Root causes — multiple analytical failures compounded

### 1. Time-of-day decay (PRIMARY cause)

The ORB signal formed at 13:45 UTC during peak RTH liquidity. The trade actually filled at 00:04 UTC — **10 hours and 19 minutes later**. ORB breakouts work because morning liquidity confirms the level. By overnight, that confirmation is stale. Volume profile changes. Different participants. Different behavior.

**Lesson:** ORB strategies should only fire in the SAME session as signal formation. Tag every signal with `session_open_time`; reject if `now - session_open_time > 4 hours` or session has rolled.

### 2. Volume signal misread — RTH ≠ overnight

QR cited "3× baseline volume" as confirmation. That was RTH baseline. By 00:04 fill time, evening Globex was trading 5–15 contracts/bar — **three orders of magnitude thinner than RTH**. The Hawkes intensity argument doesn't translate across liquidity regimes.

**Lesson:** Volume confirmation must be normalized to **same-time-of-day historical**, not absolute count. A 597-contract reopen bar at 22:00 UTC is normal evening volume, not "confirmation."

### 3. Stop-entry vulnerability in thin liquidity

A buy-stop in 5-15 contract bars is essentially a lottery ticket on noise. ANY tick to the level fires. The "breakout" was a 1-bar artifact, not real flow.

**Lesson:** In thin sessions (< 100 contracts/bar), AVOID stop-entry orders. Either (a) wait for RTH liquidity, (b) require multiple-bar confirmation above level, or (c) PASS.

### 4. No macro catalyst

The thesis was 100% technical. No news driver, no rate event, no flow story. Treasuries had no reason to rally that night.

**Lesson:** Pure-technical theses need either trending tape OR catalyst-driven flow. In choppy/range-bound regimes without catalyst, technical levels are likely to be tested as noise (where this happened) rather than respected as inflection (which would have made it work).

### 5. The autonomous re-eval was right on the rule, wrong on the spirit

Risk Manager correctly noted "invalidation rule not strictly triggered" (closes at 110.875 weren't strictly below). But the SPIRIT of the breakout thesis was "price holds above ORB level on real volume." In 22:00–23:00 UTC, ZN held at 110.875–110.890 with thin volume — the breakout was already dead in spirit.

**Lesson:** The autonomous re-eval should ask "are entry conditions ALL still present (price + volume + momentum + structure)?" not just "has invalidation strictly fired?" Spirit-of-thesis matters.

### 6. The single-actor wipe at 01:14

The 215-contract sell that took us out was a single institutional-sized clear-out in an otherwise empty session. **In thin sessions, ONE actor can move price arbitrarily.** This is a structural risk you can't analyze around — only avoid by not being in the trade during thin sessions.

## What the team will do differently

**For ORB / breakout strategies:**
- Tag every signal with `session_origin: RTH | overnight | weekend`
- Reject re-entry if signal age > 4 hours OR session has rolled
- Require minimum-volume thresholds (per-instrument) for confirmation

**For autonomous re-evaluation:**
- Don't just check invalidation rule strictness — verify ALL original entry conditions are present
- Volume profile check: if current volume regime differs >50% from signal-time, treat as a different setup (which probably needs fresh Risk Manager eval, not re-approval of the old)
- Time-decay check: signals older than 4× the strategy's natural timeframe are stale

**For stop-entry mechanics:**
- In thin liquidity (<100 contracts/avg-bar over last 20 bars), prefer immediate-fill or PASS over stop-entry
- Document liquidity regime in proposal rationale

**For Risk Manager:**
- Add "session-decay" check as gate #14: signal-age vs strategy-natural-horizon
- Add "liquidity regime" check: average bar volume over last 20 bars vs minimum threshold per strategy
- Counter-regime/no-catalyst trades require explicit flow story, not just technical reasoning

**For all analysts:**
- Read this lesson on every wake. Same-session, same-regime, same-flow-conditions matter as much as the structural level.

## Performance impact on Combine

Net P&L impact: **−$63.82** on a $50,000 account = **−0.13% drawdown**.
Day P&L: −$63.82 (well within $500 internal DLL).
TDD anchor: still $50,000 (we never went above).
Trading days logged: this counts as 1 day with a trade.

Combine status: still on track. **One losing trade is not the failure mode.** The failure mode is repeating the same mistake.

This lesson is now standing context for every analyst, PM, RM, and Execution Trader wake.
