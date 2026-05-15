---
type: macro_levels
generated_at: 2026-05-15T10:00:10.594799+00:00
---

# Macro levels — auto-fetched from FRED

Live regime context for the agent preambles. Updated daily.

| Series | Label | As of | Level | Δ 5d | Δ 20d |
|---|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 2026-05-13 | 4.460 % | +0.100 | +0.170 |
| DGS2 | 2Y Treasury yield | 2026-05-13 | 3.980 % | +0.110 | +0.220 |
| DGS30 | 30Y Treasury yield | 2026-05-13 | 5.030 % | +0.090 | +0.140 |
| DFII10 | 10Y real yield (TIPS) | 2026-05-13 | 1.990 % | +0.050 | +0.090 |
| T10Y2Y | 10s2s curve slope | 2026-05-13 | 0.480 % | -0.010 | -0.050 |
| T10YIE | 10Y breakeven inflation | 2026-05-13 | 2.470 % | +0.050 | +0.080 |
| DTWEXBGS | Broad USD (trade-weighted) | 2026-05-08 | 118.039 idx | -0.353 | -0.816 |
| VIXCLS | VIX | 2026-05-13 | 17.870 | +0.480 | -0.300 |
| SOFR | Secured Overnight Funding | 2026-05-13 | 3.590 % | -0.020 | -0.130 |

## Implications for `gap_fill` Treasury edge

- **DGS10 trend (5d / 20d)**: rising trend = directional regime = overnight gaps more likely to extend, not fade. Recommend Risk Manager lean toward smaller size on long fades when 5d delta > +0.10%.
- **DFII10 (real yield)**: aggressive moves in real yields shift Treasury demand sharply. >0.10% 5d delta = elevated risk for gap_fill across the curve.
- **VIX**: elevated equity vol (>25) historically coincides with rates futures gap-extension regimes. Threshold for gap_fill caution: VIX > 20.
- **SOFR vs IORB**: if SOFR drifting above IORB indicates money-market stress; ZT/ZF gap_fill especially exposed.
