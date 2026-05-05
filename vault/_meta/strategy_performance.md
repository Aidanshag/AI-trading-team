---
type: meta
status: active
applies_to: [Edge Hunter, Quant Researcher, Portfolio Manager, all analysts]
updated: 2026-05-04T10:54+00:00
total_observed_trades: 0
---

# Strategy Performance — auto-tuning ranking

This document is **machine-generated** from actual closed trades + literature priors via Bayesian shrinkage. Updates automatically as trades close. Read on every wake — bias toward top-ranked strategies.

**How to read:**
- Strategies sorted by expectancy (highest first).
- `n` = observed trades for this strategy.
- `confidence`: ADVISORY (n<20), PATTERN (20-49), RULE (50-99), HARD (≥100).
- ADVISORY = informational, use literature priors; PATTERN = some weight; RULE = trust empirical.

## Confidence summary

- **HARD**: 0 strategies
- **RULE**: 0 strategies
- **PATTERN**: 0 strategies
- **ADVISORY**: 18 strategies

**Total observed trades across all strategies: 0**

## Ranking

| Rank | Strategy | Expectancy | Hit% | n | Conf |
|---:|---|---:|---:|---:|---|
| 1 | `vol_regime_trend` ⭐⭐ | +0.50R | 50% | 0 | ADVISORY |
| 2 | `pullback_in_trend` ⭐ | +0.38R | 55% | 0 | ADVISORY |
| 3 | `volume_spike_reversal` ⭐ | +0.38R | 55% | 0 | ADVISORY |
| 4 | `support_resistance_bounce` ⭐ | +0.38R | 55% | 0 | ADVISORY |
| 5 | `bollinger_squeeze_break` ⭐ | +0.35R | 45% | 0 | ADVISORY |
| 6 | `keltner_breakout` | +0.26R | 45% | 0 | ADVISORY |
| 7 | `pivot_reversal` | +0.25R | 50% | 0 | ADVISORY |
| 8 | `volatility_breakout` | +0.22R | 35% | 0 | ADVISORY |
| 9 | `gap_fill` | +0.17R | 65% | 0 | ADVISORY |
| 10 | `inside_bar_break` | +0.15R | 50% | 0 | ADVISORY |
| 11 | `donchian_breakout` | +0.12R | 38% | 0 | ADVISORY |
| 12 | `narrow_range_break` | +0.12R | 45% | 0 | ADVISORY |
| 13 | `vol_spike_fade` | +0.10R | 55% | 0 | ADVISORY |
| 14 | `range_mean_reversion` | +0.08R | 60% | 0 | ADVISORY |
| 15 | `vwap_reversion` | +0.08R | 60% | 0 | ADVISORY |
| 16 | `bollinger_mean_reversion` ⚠️ | +0.02R | 60% | 0 | ADVISORY |
| 17 | `opening_range_breakout` ⚠️ | +0.00R | 40% | 0 | ADVISORY |
| 18 | `rsi2_extreme_reversion` ⚠️ | -0.02R | 65% | 0 | ADVISORY |

## Bias guidance for analysts

**Prefer (top 5 by expectancy):**
- `vol_regime_trend` — E=+0.50R, hit 50% (n=0, ADVISORY)
- `pullback_in_trend` — E=+0.38R, hit 55% (n=0, ADVISORY)
- `volume_spike_reversal` — E=+0.38R, hit 55% (n=0, ADVISORY)
- `support_resistance_bounce` — E=+0.38R, hit 55% (n=0, ADVISORY)
- `bollinger_squeeze_break` — E=+0.35R, hit 45% (n=0, ADVISORY)

**Avoid / restrict (bottom 3 by expectancy):**
- `bollinger_mean_reversion` — E=+0.02R, hit 60% (n=0, ADVISORY)
- `opening_range_breakout` — E=+0.00R, hit 40% (n=0, ADVISORY)
- `rsi2_extreme_reversion` — E=-0.02R, hit 65% (n=0, ADVISORY)

## Methodology

- **Bayesian shrinkage**: blended = (prior × 30 + observed × n) / (30 + n)
- **Prior weight**: 30 trade-equivalents from literature.
- **R-normalization**: $200/R assumed for converting $ P&L to R-multiples.
- **Confidence ladder:**
  - n < 20: ADVISORY (use literature defaults; observed too noisy)
  - 20 ≤ n < 50: PATTERN (moderate weight)
  - 50 ≤ n < 100: RULE (trust empirical)
  - n ≥ 100: HARD (codify as gate)
