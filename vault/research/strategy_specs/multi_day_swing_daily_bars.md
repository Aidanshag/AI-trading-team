---
type: strategy_specification
status: queued for implementation
target_phase: post-Combine-validation
estimated_effort: 10-15 hours implementation + multi-year walk-forward
slippage_resistance: VERY HIGH (slippage tiny relative to daily ranges)
---

# Strategy: Multi-Day Swing on Daily Bars

## Concept

Hold positions for 2-7 days based on daily-bar signals. Daily ranges on treasury futures are 30-100+ ticks; slippage of 1 tick is essentially zero percent of expected gain. **The most slippage-tolerant strategy class possible** — at the cost of overnight risk and slower cadence.

## Why this matters specifically for our fund

Today we discovered gap_fill on intraday 5m bars is fragile to slippage because moves are tiny (sub-tick stops). On daily bars:
- Average daily range on ZN: ~40 ticks ($625 / contract)
- 1 tick of slippage on entry+exit = 0.05% of expected move
- A 2:1 RR trade with 60-tick target absorbs slippage trivially

This is NOT a band-aid. Daily-timeframe trend strategies are the BEST paradigm for our friction-constrained context.

## Concrete strategies (3 candidates)

### A. Donchian breakout (daily)
```
On 20-day high break: long
On 20-day low break: short
Stop: 2 × daily ATR (typically ~$1,250 on ZN)
Target: 4 × daily ATR (4 days of trend)
Hold: until target or stop
Frequency: 2-4 entries per month per symbol
```

### B. Pullback in daily trend
```
Define trend: price > 50-day EMA (long) or < 50-day EMA (short)
Wait for pullback to 20-day EMA
Enter on reversal candle (engulfing or hammer)
Stop: 1 × daily ATR
Target: 2 × daily ATR
Frequency: 4-8 entries per month per symbol
```

### C. Daily mean-reversion at extremes
```
Daily RSI < 25 OR > 75
Confirmation: reversal candle + volume above 30-day average
Enter at break of reversal candle (intraday)
Stop: 1.5 × daily ATR
Target: 2.5 × daily ATR
Frequency: 1-2 entries per month per symbol
```

## Why slippage doesn't matter at this scale

Stop = 1.5 × daily ATR ≈ 60 ticks on ZN
Slippage = 1 tick adverse
Slippage as % of stop = 1.7%
Slippage as % of expected gain (target = 2.5×ATR) = 1%

For comparison:
- Intraday gap_fill: stop = 0.4 ticks, slippage as % of stop = 250%
- Multi-day swing: stop = 60 ticks, slippage as % of stop = 1.7%

**150x more slippage-tolerant than current gap_fill_wide.**

## Implementation outline

```python
def daily_swing_donchian(
    bars: pd.DataFrame,           # daily bars, NOT 5m
    high_lookback: int = 20,
    low_lookback: int = 20,
    stop_atr_mult: float = 2.0,
    target_atr_mult: float = 4.0,
    atr_period: int = 14,
) -> Iterator[Signal]:
    """Holds positions multi-day until target or stop."""
```

New requirements:
1. Backtest infrastructure must support daily bars (current setup uses 5m)
2. Live trader needs to handle multi-day holds (current setup is intraday)
3. Topstep allows overnight holds in funded accounts (verify — Combine may differ)

## Critical Combine compatibility check

Topstep Combine rules around overnight holds:
- Funded accounts: yes, can hold overnight
- Combine evaluation: need to verify — some prop firms restrict this
- DLL/TDD continue to apply: a swing position that loses 50% of stop overnight could trip DLL even though it's a "small" loss in daily-bar terms

This needs research before implementing in Combine.

## Validation gates

1. Backtest on 5+ years of daily bars (yfinance has free daily futures back to ~2003)
2. Walk-forward across multiple regimes: 2018 vol spike, 2020 COVID, 2022 hawkish Fed, 2024 cuts cycle
3. Slippage stress at 1, 2, 3 ticks adverse — must remain profitable
4. Paper trade for 30 days minimum
5. Compare live to backtest with ±10% variance tolerance (much tighter than intraday)

## Position sizing implications

Daily swings have larger $ stops. Per-trade $150 cap means:
- ZN ATR ≈ 40 ticks × $15.625 = $625
- Stop = 2×ATR = $1,250
- Per-trade cap $150 / $1,250 = 0.12 contracts → can't size!

Either:
- Increase per-trade cap to $300-500 for swing positions
- Use micros (no equivalent for ZN — closest is /10Y CBOT cash, requires different broker)
- Accept smaller-than-1-contract impossible → would need different strategy parameters

This is a math fight against Topstep's $50K Combine size. The strategy may need a $100K+ funded account to size properly.

**Conclusion**: Multi-day swing is more suitable for SCALED multi-account operation (Phase 2-3) than for Phase 1 single-Combine.

## Why we still spec it now

1. Document the spec while context is fresh
2. Cowork can implement and backtest this WEEK with no operational risk (paper-only)
3. Validates whether the strategy edge is real even if we can't deploy at Phase 1 sizes
4. Provides a Phase 2 candidate for one of the multi-account decorrelation slots

## Risks

1. **Sizing math doesn't fit Combine** (described above)
2. **Overnight gap risk** — Sunday night reopen can gap through stops
3. **Lower trade frequency** — fewer signals = less feedback loop for validation
4. **Market regime sensitivity** — trend strategies fail in chop; need regime classifier on top
