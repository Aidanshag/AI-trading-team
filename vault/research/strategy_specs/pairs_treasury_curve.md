---
type: strategy_specification
status: queued for implementation
target_phase: post-Combine-validation (after gap_fill_wide validates in production)
estimated_effort: 8-12 hours implementation + walk-forward
slippage_resistance: HIGH (asymmetric — slippage on one leg often offsets the other)
---

# Strategy: Pairs / Spread Mean-Reversion on Treasury Curve

## Concept

Trade the SPREAD between two treasury futures rather than a single instrument. Mean-reversion of the spread when it deviates from its rolling average. Slippage on the long leg often offsets slippage on the short leg → much more slippage-tolerant than single-instrument strategies.

## Universe

Treasury curve pairs (in order of expected mean-reversion strength):
- **NOB**: ZN (10y) − 2 × ZF (5y) → "Notes Over Bonds" classic spread
- **TUT**: ZT (2y) − 2 × ZF (5y)
- **FYT**: ZF − ZT
- **NOB-light**: ZN − ZB (10y vs 30y)
- **2s10s**: ZT − ZN

The 2-leg pairs reflect rate-curve dynamics. They mean-revert because of carry, fundamental policy expectations, and dealer hedging.

## Entry logic

```
For each bar:
    1. Compute spread = leg_a × ratio_a − leg_b × ratio_b
       (ratios chosen for DV01 neutrality; e.g. ZN-ZF: ratio is roughly 0.5)
    2. Compute z-score of spread vs 50-bar rolling mean and stdev
    3. If z-score > +2.0 or < -2.0:
       - Trade fade direction (sell rich leg, buy cheap leg)
       - Stop: spread widens to z = +/- 3.0 (further from mean)
       - Target: spread returns to z = 0 (mean)
       - RR = 1.5:1 typically
```

## Why it's slippage-resistant

| Single-instrument trade | Pair trade |
|---|---|
| Entry slippage = +1 tick adverse on 1 leg | +1 tick on long leg AND short leg |
| Stop slippage = +1 tick adverse on 1 leg | +1 tick on each leg, BUT one's adverse = other's favorable |
| Net: 2 ticks slippage cost per trade | Net: ~0-1 tick spread slippage |

The math: if ZN spreads 1 tick wider on entry AND ZF spreads 1 tick wider on entry, the SPREAD has the same value (both moves cancel). What we pay is the bid-ask spread on each leg, but those are well-known and bounded.

## Implementation outline

```python
def pairs_treasury_curve(
    bars_a: pd.DataFrame,         # e.g., ZN
    bars_b: pd.DataFrame,         # e.g., ZF
    ratio_a: float = 1.0,
    ratio_b: float = 2.0,
    z_window: int = 50,
    z_entry: float = 2.0,
    z_stop: float = 3.0,
    z_target: float = 0.0,
) -> Iterator[Signal]:
    """Returns synchronized signals — buy/sell BOTH legs together."""
```

New requirement: signals from this strategy emit a "pair" structure with TWO legs. The trader needs to place 2 entries simultaneously. This is a small addition to `place_bracket` (or a new `place_pair_bracket`).

## Validation gates before live

1. Backtest on 60d 5m bars, all curve pairs, slippage levels [0, 0.25, 0.5, 1.0]
2. Walk-forward 75/25 split — OOS expectancy must be positive at 0.5 slippage with n≥30
3. Live R-multiple tracker must show ≥80% match with OOS predictions over 4-week paper period
4. Only THEN promote to live_allowlist

## Why this is high-priority for the fund

- Slippage is the #1 risk we discovered. Pair trades structurally absorb slippage.
- Treasury curve mean-reverts because of fundamental flow (carry, policy, dealer hedging) — not just statistical fitting.
- 2x position size implications (each pair = 2 contracts): need to verify Topstep's per-position limit can handle pair trades.
- Decorrelates from gap_fill_wide — different signal trigger, different time horizon.

## Risks / what could fail

1. Topstep margin treats long+short legs as separate, doubling capital req
2. Spread can stay extreme longer than expected (ride past z=3 stop)
3. Liquidity in less-traded pairs (TUT, FYT) is thinner than ZN/ZB
4. Cross-leg latency: the 2 leg orders can fill at different times, leaving us briefly net-directional

## Open questions for cowork to resolve before implementing

1. Does Topstep allow simultaneous long+short positions in different contracts? (likely yes, but verify)
2. What's the optimal DV01-neutral ratio per pair? (need to compute from contract specs)
3. Should we use 5m or 15m bars? (15m might smooth noise; 5m gives more signals)
4. When pair stops hit — close BOTH legs immediately or just the loser?
