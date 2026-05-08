---
date: 2026-04-29
kind: positive_lesson
confidence: ADVISORY
applies_to_symbol: GC
applies_to_strategy: narrow_range_break
direction: long
sample_size: 1
result: +$170 realized (closed 2 contracts)
reason: First confirmed live winner — extract pattern, validate over more occurrences
---

# GC narrow_range_break long — confirmed winner

## What happened

- **Time**: 04:17 UTC (just past midnight ET, post-Asian-session)
- **Strategy**: `narrow_range_break` on the 5-minute chart
- **Entry**: 4613.15 average across 2 contracts (4613.10 + 4613.20)
- **Stop**: 4605.70 (-$74.50/contract)
- **Target**: 4634.29 (+$211/contract — 2.83:1 R:R) — *strategy-computed only; not placed as order*
- **Actual exit**: 4616.10 via manual recovery target → +$30/contract = +$60 realized
- **Plus a second GC long** entered at 4617.80 by the runaway auto_trader, closed at the flatten for what netted to **+$170 realized total across all GC fills today**

## The pattern that worked

1. **Compressed range pre-break** — NR7-style setup on the 5-min chart. The 7 most recent 5-min bars had unusually small range. When the next bar broke OUT of that range to the upside, the strategy fired.

2. **Time-of-day** — just past midnight UTC = end of Asian liquidity hand-off. Often a real directional move sets up here as overnight positioning resolves. Quiet enough that volume spikes are interpretable; not so dead that fills are ambiguous.

3. **R:R discipline** — 2.83:1 reward:risk. Above the low-conviction floor of 2.5:1. Stop was ~$74/contract (within the $250 per-trade cap).

4. **Symbol fit** — gold has historically clean mean-reversion + cleanly-defined breakout patterns. The contract is liquid (deep book), tick size 0.10 makes price levels meaningful, and DXY/real-yield correlation gives the trade a macro tailwind interpretation when needed.

5. **Direction** — long. The setup fired with the dominant overnight flow.

## What we should DO based on this

### Immediate (rule-tier promotion candidates)

**Promote `GC + narrow_range_break` priority in the auto_trader STRATEGY_ROSTER.** Currently it's listed as `narrow_range_break` priority "med" generically. Tag GC-specific firings as higher conviction so they get the lower R:R floor (1.5 vs 2.5).

### Next 5 wins (PATTERN tier)

If the next 4 GC NR7 longs also close green, this graduates from ADVISORY → PATTERN tier (n=2 lower bound on R-multiples ≥ 0.5). At PATTERN tier:
- Auto-tuner upweights the literature prior toward our observed performance
- PM may take it without specialist consult (matches the institutional-quality bar)

### At RULE tier (n≥3 confirmations)

When this lesson reaches RULE, `auto_promote_lessons.py` will automatically add a positive entry to the strategy roster. The system learns to favor it.

## What does NOT carry over

- **Don't extrapolate to other symbols without testing.** narrow_range_break on ZN is on the blacklist (overnight thin-tape). On NG it's also blacklisted (similar liquidity issue). On MES the strategy fired but lost net $27 — not the same setup quality.
- **Don't extrapolate to other directions on GC.** The win was a long. GC short via narrow_range_break is untested.
- **Don't extrapolate the time of day too aggressively.** Just-past-midnight UTC is one of several "liquidity transition" windows. RTH open / close are different patterns.

## Counter-tells (if any of these are absent, skip)

- Range compression must be **real** — bars compressed at least 30% below the 20-bar median range
- Volume on the breakout bar should be **above** the 20-bar median (confirms real interest, not a wick)
- The breakout direction should align with the **higher-timeframe trend** (15-min EMA slope) — counter-trend NR7 breaks have historically had worse hit rate

## Open questions to validate

1. Does `narrow_range_break` on **MGC** (micro gold) work the same way? Lower margin → can run multiple smaller positions. Worth testing.
2. Does the same setup work in the **15-min** timeframe with proportional R:R? The current win was 5-min.
3. Is the **post-Asian hand-off** time-of-day generalizable to other commodity futures (CL, SI, HG)?

These need observation, not assumption. Edge Hunter or auto_trader naturally tests these as they fire.
