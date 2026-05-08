---
type: macro_levels
generated_at: 2026-05-08T10:00:10.671016+00:00
---

# Macro levels — auto-fetched from FRED

Live regime context for the agent preambles. Updated daily.

| Series | Label | As of | Level | Δ 5d | Δ 20d |
|---|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 2026-05-06 | 4.360 % | -0.060 | +0.070 |
| DGS2 | 2Y Treasury yield | 2026-05-06 | 3.870 % | -0.050 | +0.080 |
| DGS30 | 30Y Treasury yield | 2026-05-06 | 4.940 % | -0.040 | +0.050 |
| DFII10 | 10Y real yield (TIPS) | 2026-05-06 | 1.940 % | -0.020 | -0.020 |
| T10Y2Y | 10s2s curve slope | 2026-05-07 | 0.490 % | -0.030 | -0.020 |
| T10YIE | 10Y breakeven inflation | 2026-05-07 | 2.450 % | -0.010 | +0.110 |
| DTWEXBGS | Broad USD (trade-weighted) | 2026-05-01 | 118.393 idx | -0.337 | -2.264 |
| VIXCLS | VIX | 2026-05-06 | 17.390 | -1.420 | -3.650 |
| SOFR | Secured Overnight Funding | 2026-05-06 | 3.610 % | -0.020 | +0.020 |

## Implications for `gap_fill` Treasury edge

- **DGS10 trend (5d / 20d)**: rising trend = directional regime = overnight gaps more likely to extend, not fade. Recommend Risk Manager lean toward smaller size on long fades when 5d delta > +0.10%.
- **DFII10 (real yield)**: aggressive moves in real yields shift Treasury demand sharply. >0.10% 5d delta = elevated risk for gap_fill across the curve.
- **VIX**: elevated equity vol (>25) historically coincides with rates futures gap-extension regimes. Threshold for gap_fill caution: VIX > 20.
- **SOFR vs IORB**: if SOFR drifting above IORB indicates money-market stress; ZT/ZF gap_fill especially exposed.
