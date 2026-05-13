---
type: macro_levels
generated_at: 2026-05-13T10:00:20.434309+00:00
---

# Macro levels — auto-fetched from FRED

Live regime context for the agent preambles. Updated daily.

| Series | Label | As of | Level | Δ 5d | Δ 20d |
|---|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 2026-05-11 | 4.420 % | -0.030 | +0.120 |
| DGS2 | 2Y Treasury yield | 2026-05-11 | 3.950 % | +0.000 | +0.170 |
| DGS30 | 30Y Treasury yield | 2026-05-11 | 4.980 % | -0.040 | +0.080 |
| DFII10 | 10Y real yield (TIPS) | 2026-05-11 | 1.950 % | +0.000 | +0.030 |
| T10Y2Y | 10s2s curve slope | 2026-05-12 | 0.460 % | -0.040 | -0.040 |
| T10YIE | 10Y breakeven inflation | 2026-05-12 | 2.470 % | +0.000 | +0.100 |
| DTWEXBGS | Broad USD (trade-weighted) | 2026-05-08 | 118.039 idx | -0.353 | -0.816 |
| VIXCLS | VIX | 2026-05-11 | 18.380 | +0.090 | -0.740 |
| SOFR | Secured Overnight Funding | 2026-05-11 | 3.600 % | -0.030 | -0.030 |

## Implications for `gap_fill` Treasury edge

- **DGS10 trend (5d / 20d)**: rising trend = directional regime = overnight gaps more likely to extend, not fade. Recommend Risk Manager lean toward smaller size on long fades when 5d delta > +0.10%.
- **DFII10 (real yield)**: aggressive moves in real yields shift Treasury demand sharply. >0.10% 5d delta = elevated risk for gap_fill across the curve.
- **VIX**: elevated equity vol (>25) historically coincides with rates futures gap-extension regimes. Threshold for gap_fill caution: VIX > 20.
- **SOFR vs IORB**: if SOFR drifting above IORB indicates money-market stress; ZT/ZF gap_fill especially exposed.
