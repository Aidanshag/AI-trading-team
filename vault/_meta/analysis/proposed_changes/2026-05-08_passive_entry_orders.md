---
type: proposed_change
date: 2026-05-08
author: Cowork (Claude)
priority: P1
status: PROPOSED — needs user/CC review before merge
references:
  - vault/research/slippage_mitigation_playbook.md (Section 1, lever #1)
  - vault/_meta/cowork_coordination.md (2026-05-08 queue item #8)
  - scripts/live_trader.py:place_bracket
---

# Proposed: passive entry orders (slippage-reduction lever #1)

## Why this is a proposal, not a direct ship

This change modifies `scripts/live_trader.py:place_bracket` — the live
order-placement path. CC's coordination protocol gives that file
"either-can-modify-with-coordination" status (it's not on
HIGH_RISK_FILES), but a behavior change to live-fill mechanics deserves
explicit user/CC sign-off before merging because:

1. It changes the fill probability profile for every trade
2. It interacts with the brackets' protective-leg timing
3. It can break OCO race detection if the entry doesn't fill at all
4. Sunday's first live session (5/10 17:00 ET) is < 48h away

Cowork wrote the design + tradeoff analysis below. CC or user makes the
ship call.

## What it changes

**Today** (`live_trader.py:place_bracket`): entry orders are placed as
**marketable-limit at +5 ticks** (buy) or **−5 ticks** (sell) past the
current price. This crosses the spread to guarantee a fast fill —
historically Topstep rejects pure market orders, so marketable-limit was
the workaround. Cost: every fill pays ~5 ticks of adverse slippage.

**Proposed**: place entry as a **passive limit** at the favorable side
of the spread (or at the current bid for buys / ask for sells). The
order rests in the book until the market crosses to it. Cost: no
slippage on entry; fills can be missed if the market moves away.

For mean-reversion strategies (gap_fill family — the entire current
locked universe), missed fills are *protective*. We're fading
overnight noise; if the market accelerates instead of reverting, we
*want* to skip that trade. Passive entries naturally implement that
filter.

For trend-following strategies (`wide_session_drive`, when it lands
live): missed fills hurt — the trend has already moved when our
passive limit might fill, defeating the strategy's design. Passive
entries should NOT be applied to trend-followers.

## Implementation sketch

```python
# in scripts/live_trader.py:place_bracket()
def place_bracket(client, symbol, signal, qty=1, *, passive=False):
    side = "buy" if signal["side"] == "long" else "sell"
    tick = _tick_size_for(symbol)
    entry_price = float(signal["price"])

    if passive:
        # Sit at the favorable side of the spread. If we don't have a
        # quote, use the signal price (best estimate of fair value).
        # No slippage buffer.
        limit_price = entry_price
    else:
        # Existing behavior: cross the spread by 5 ticks.
        slip_ticks = 5
        limit_price = (entry_price + slip_ticks * tick if side == "buy"
                       else entry_price - slip_ticks * tick)

    # ... rest of place_bracket unchanged
```

Caller (`scan_once`) flips passive on/off per strategy:

```python
PASSIVE_ENTRY_STRATEGIES = {
    "gap_fill", "gap_fill_wide", "fair_value_gap",
    # NOT: wide_session_drive, donchian_breakout, vol_regime_trend
}
passive = strategy_name in PASSIVE_ENTRY_STRATEGIES
result = place_bracket(client, symbol, signal, passive=passive)
```

## Open questions before ship

1. **Topstep `time_in_force="day_post_only"` support?** Per playbook §1
   detail. If supported, the order is *guaranteed* not to cross the
   spread (rejected if it would). If not supported, we accept that a
   passive limit might cross by 1 tick.

2. **Cancel-and-retry timeout?** If the limit doesn't fill within X
   minutes, cancel it and either skip or re-evaluate. Suggested: 5
   minutes (matches the scan cadence).

3. **OCO race interaction?** `bracket_oco_misdirected_leg` events are
   detected when expected entry didn't fill but the protective leg
   did. With passive entries, fill failure is more common and not an
   error. The detection logic should:
   - Distinguish "passive entry didn't fill" (expected) from
     "protective leg orphaned" (still a real OCO race)
   - Per-strategy or per-mode flag the entry as `expected_fill_rate`
     so the detector doesn't false-positive

4. **Audit / shadow log?** When a passive entry doesn't fill, we
   should log it as a "missed fill" so we can later compare missed-fill
   rates to OOS expectancy. If ~30% of signals miss fills and the rest
   are net positive, that's the validated mode. If fills are 95% but
   slippage is gone, also good. The metric matters.

## Expected impact (per playbook §1)

> "−50% on entry slippage" for trades that fill. For gap_fill family
> on Treasuries, current default min_gap_atr=0.75 produces sub-tick
> stops (per `gap_fill_wide` rationale). 5-tick entry slippage swallows
> the per-trade R completely. Passive entries cut slippage to ~0 ticks
> for the trades that fill — which is exactly what makes the OOS edge
> survive in live conditions.

## Recommended ship sequence

1. CC or user reviews this proposal
2. Decide on Topstep post-only support (test against demo if needed)
3. Add `passive` flag to `place_bracket`, default False (no behavior
   change for callers that don't opt in)
4. Wire `PASSIVE_ENTRY_STRATEGIES` set into `scan_once`'s strategy
   loop — opt the gap_fill family in
5. Add OCO-detector exception for passive missed-fills
6. Add missed-fill audit log (`vault/research/missed_fills_<date>.md`
   or a column in the existing slippage tracker)
7. Ship for Sunday's first live session
8. After 5+ live fills, compare measured slippage on
   `gap_fill | ZN | Asian` to its OOS expectancy. If gap closes,
   passive entries are validated.

## Status

**PROPOSED.** Not implemented in code. Cowork has the design ready; CC
or the user makes the ship call.
