---
type: macro_levels
generated_at: 2026-05-12T10:00:09.278178+00:00
---

# Macro levels — auto-fetched from FRED

Live regime context for the agent preambles. Updated daily.

| Series | Label | As of | Level | Δ 5d | Δ 20d |
|---|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 2026-05-08 | 4.380 % | -0.010 | +0.070 |
| DGS2 | 2Y Treasury yield | 2026-05-08 | 3.900 % | +0.020 | +0.090 |
| DGS30 | 30Y Treasury yield | 2026-05-08 | 4.950 % | -0.020 | +0.040 |
| DFII10 | 10Y real yield (TIPS) | 2026-05-08 | 1.930 % | +0.020 | -0.020 |
| T10Y2Y | 10s2s curve slope | 2026-05-11 | 0.470 % | -0.030 | -0.050 |
| T10YIE | 10Y breakeven inflation | 2026-05-11 | 2.470 % | -0.030 | +0.090 |
| DTWEXBGS | Broad USD (trade-weighted) | 2026-05-08 | 118.039 idx | -0.353 | -0.816 |
| VIXCLS | VIX | 2026-05-08 | 17.190 | +0.200 | -2.040 |
| SOFR | Secured Overnight Funding | 2026-05-08 | 3.600 % | -0.040 | -0.010 |

## Implications for `gap_fill` Treasury edge

- **DGS10 trend (5d / 20d)**: rising trend = directional regime = overnight gaps more likely to extend, not fade. Recommend Risk Manager lean toward smaller size on long fades when 5d delta > +0.10%.
- **DFII10 (real yield)**: aggressive moves in real yields shift Treasury demand sharply. >0.10% 5d delta = elevated risk for gap_fill across the curve.
- **VIX**: elevated equity vol (>25) historically coincides with rates futures gap-extension regimes. Threshold for gap_fill caution: VIX > 20.
- **SOFR vs IORB**: if SOFR drifting above IORB indicates money-market stress; ZT/ZF gap_fill especially exposed.
