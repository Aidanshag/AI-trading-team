---
type: walk_forward_firing_strategies
date: 2026-05-05T21:58:35.478144+00:00
cutoff: 2026-04-18 00:56:15-04:00
---

# Walk-forward validation — strategies firing live without OOS proof

Strategies tested: `narrow_range_break`, `inside_bar_break`
Symbols: GC, MCL, NG, MNQ, MES, ZN, 6E

Verdict criteria: OOS t-stat ≥ 2.0 (strict) OR (t ≥ 1.5 AND n_oos ≥ 50).
Both require OOS expectancy > 0 and n_oos ≥ 30.

## Per (strategy, symbol) results

| Strategy | Symbol | Train | OOS | Verdict | Reason |
|---|---|---|---|---|---|
| narrow_range_break | GC | n= 751 hit= 34.8% E=+0.05R t=+0.92 | n= 220 hit= 32.7% E=-0.04R t=-0.37 | ✗ fails | OOS E=-0.04R <= 0 |
| narrow_range_break | MCL | n= 682 hit= 32.8% E=-0.03R t=-0.48 | n= 204 hit= 31.4% E=-0.09R t=-0.89 | ✗ fails | OOS E=-0.09R <= 0 |
| narrow_range_break | NG | n= 785 hit= 34.1% E=-0.02R t=-0.35 | n= 245 hit= 33.5% E=+0.00R t=+0.04 | ✗ fails | t=+0.04 < threshold |
| narrow_range_break | MNQ | n= 774 hit= 31.0% E=-0.09R t=-1.77 | n= 254 hit= 29.9% E=-0.08R t=-0.83 | ✗ fails | OOS E=-0.08R <= 0 |
| narrow_range_break | MES | n= 772 hit= 32.8% E=-0.05R t=-0.96 | n= 225 hit= 28.9% E=-0.14R t=-1.47 | ✗ fails | OOS E=-0.14R <= 0 |
| narrow_range_break | ZN | n= 782 hit= 29.3% E=-0.28R t=-6.80 | n= 262 hit= 21.4% E=-0.48R t=-7.47 | ✗ fails | OOS E=-0.48R <= 0 |
| narrow_range_break | 6E | n= 874 hit= 35.7% E=+0.01R t=+0.21 | n= 253 hit= 30.4% E=-0.15R t=-1.74 | ✗ fails | OOS E=-0.15R <= 0 |
| inside_bar_break | GC | n= 718 hit= 39.8% E=+0.06R t=+1.22 | n= 222 hit= 37.8% E=-0.00R t=-0.02 | ✗ fails | OOS E=-0.00R <= 0 |
| inside_bar_break | MCL | n= 717 hit= 41.4% E=+0.08R t=+1.64 | n= 217 hit= 35.5% E=-0.08R t=-0.95 | ✗ fails | OOS E=-0.08R <= 0 |
| inside_bar_break | NG | n= 802 hit= 37.0% E=-0.07R t=-1.66 | n= 272 hit= 40.1% E=-0.02R t=-0.23 | ✗ fails | OOS E=-0.02R <= 0 |
| inside_bar_break | MNQ | n= 704 hit= 35.9% E=-0.05R t=-1.03 | n= 233 hit= 32.2% E=-0.13R t=-1.51 | ✗ fails | OOS E=-0.13R <= 0 |
| inside_bar_break | MES | n= 735 hit= 36.9% E=-0.04R t=-0.78 | n= 191 hit= 37.2% E=-0.03R t=-0.27 | ✗ fails | OOS E=-0.03R <= 0 |
| inside_bar_break | ZN | n= 689 hit= 36.0% E=-0.19R t=-4.48 | n= 213 hit= 29.6% E=-0.36R t=-5.21 | ✗ fails | OOS E=-0.36R <= 0 |
| inside_bar_break | 6E | n= 812 hit= 39.8% E=+0.02R t=+0.36 | n= 279 hit= 36.6% E=-0.07R t=-0.97 | ✗ fails | OOS E=-0.07R <= 0 |

## Validated combinations (will be added to STRATEGY_SYMBOL_ALLOWLIST)

**NONE.** Both strategies fail OOS on every symbol tested. Recommendation: remove from auto_trader's active strategy set until parameter tuning produces an OOS-validated variant.
