---
type: macro_levels
generated_at: 2026-05-11T12:32:11.629255+00:00
---

# Macro levels — auto-fetched from FRED

Live regime context for the agent preambles. Updated daily.

| Series | Label | As of | Level | Δ 5d | Δ 20d |
|---|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 2026-05-07 | 4.410 % | +0.010 | +0.120 |
| DGS2 | 2Y Treasury yield | 2026-05-07 | 3.920 % | +0.040 | +0.140 |
| DGS30 | 30Y Treasury yield | 2026-05-07 | 4.970 % | -0.010 | +0.070 |
| DFII10 | 10Y real yield (TIPS) | 2026-05-07 | 1.960 % | +0.020 | +0.010 |
| T10Y2Y | 10s2s curve slope | 2026-05-08 | 0.480 % | -0.030 | -0.020 |
| T10YIE | 10Y breakeven inflation | 2026-05-08 | 2.450 % | -0.030 | +0.090 |
| DTWEXBGS | Broad USD (trade-weighted) | 2026-05-01 | 118.393 idx | -0.337 | -2.264 |
| VIXCLS | VIX | 2026-05-07 | 17.080 | +0.190 | -2.410 |
| SOFR | Secured Overnight Funding | 2026-05-08 | 3.600 % | -0.040 | -0.010 |

## Implications for `gap_fill` Treasury edge

- **DGS10 trend (5d / 20d)**: rising trend = directional regime = overnight gaps more likely to extend, not fade. Recommend Risk Manager lean toward smaller size on long fades when 5d delta > +0.10%.
- **DFII10 (real yield)**: aggressive moves in real yields shift Treasury demand sharply. >0.10% 5d delta = elevated risk for gap_fill across the curve.
- **VIX**: elevated equity vol (>25) historically coincides with rates futures gap-extension regimes. Threshold for gap_fill caution: VIX > 20.
- **SOFR vs IORB**: if SOFR drifting above IORB indicates money-market stress; ZT/ZF gap_fill especially exposed.
