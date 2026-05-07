---
type: macro_levels
generated_at: 2026-05-07T00:32:57.259275+00:00
---

# Macro levels — auto-fetched from FRED

Live regime context for the agent preambles. Updated daily.

| Series | Label | As of | Level | Δ 5d | Δ 20d |
|---|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 2026-05-05 | 4.430 % | +0.070 | +0.100 |
| DGS2 | 2Y Treasury yield | 2026-05-05 | 3.930 % | +0.090 | +0.120 |
| DGS30 | 30Y Treasury yield | 2026-05-05 | 4.980 % | +0.040 | +0.080 |
| DFII10 | 10Y real yield (TIPS) | 2026-05-05 | 1.960 % | +0.040 | +0.000 |
| T10Y2Y | 10s2s curve slope | 2026-05-06 | 0.490 % | -0.010 | -0.010 |
| T10YIE | 10Y breakeven inflation | 2026-05-06 | 2.420 % | -0.040 | +0.090 |
| DTWEXBGS | Broad USD (trade-weighted) | 2026-05-01 | 118.393 idx | -0.337 | -2.264 |
| VIXCLS | VIX | 2026-05-05 | 17.380 | -0.450 | -8.400 |
| SOFR | Secured Overnight Funding | 2026-05-05 | 3.620 % | -0.020 | +0.000 |

## Implications for `gap_fill` Treasury edge

- **DGS10 trend (5d / 20d)**: rising trend = directional regime = overnight gaps more likely to extend, not fade. Recommend Risk Manager lean toward smaller size on long fades when 5d delta > +0.10%.
- **DFII10 (real yield)**: aggressive moves in real yields shift Treasury demand sharply. >0.10% 5d delta = elevated risk for gap_fill across the curve.
- **VIX**: elevated equity vol (>25) historically coincides with rates futures gap-extension regimes. Threshold for gap_fill caution: VIX > 20.
- **SOFR vs IORB**: if SOFR drifting above IORB indicates money-market stress; ZT/ZF gap_fill especially exposed.
