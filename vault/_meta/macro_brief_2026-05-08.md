---
type: macro_brief
date: 2026-05-08
generated_at: 2026-05-08T10:00:14.909789+00:00
generated_by: scripts.generate_macro_brief
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, all analysts]
read_on_first_wake: true
---

# Macro brief — 2026-05-08

> Auto-generated daily situational awareness for the front-office. Cross-checks against the live `gap_fill` Treasury edge: anything that shifts gaps from flow-driven (fade works) toward information-driven (fade fails).

> **TL;DR (2026-05-08)** — 10Y=4.36% | real=1.94% | USD=118.4 | VIX=17.4 · 7 auction(s) next 7d · 0 HIGH-influence Fed speaker(s) upcoming.

## Headline market levels

| Series | Label | Level | Δ 5d | Δ 20d |
|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 4.360 % | -0.060 | +0.070 |
| DGS2 | 2Y Treasury yield | 3.870 % | -0.050 | +0.080 |
| DGS30 | 30Y Treasury yield | 4.940 % | -0.040 | +0.050 |
| DFII10 | 10Y real yield (TIPS) | 1.940 % | -0.020 | -0.020 |
| T10Y2Y | 10s2s curve slope | 0.490 % | -0.030 | -0.020 |
| T10YIE | 10Y breakeven inflation | 2.450 % | -0.010 | +0.110 |
| DTWEXBGS | Broad USD (trade-weighted) | 118.393 idx | -0.337 | -2.264 |
| VIXCLS | VIX | 17.390 | -1.420 | -3.650 |
| SOFR | Secured Overnight Funding | 3.610 % | -0.020 | +0.020 |

## Treasury auctions — next 10 days

| Date | Time ET | Type | Term | Amt ($B) | Primary | Basis |
|---|---|---|---|---:|---|---|
| 2026-05-11 | 13:00 | Note | 3-Year | 58.0 | — | ZT, ZF |
| 2026-05-12 | 13:00 | Note | 10-Year | 42.0 | ZN | — |
| 2026-05-13 | 13:00 | Bond | 30-Year | 25.0 | ZB | — |

_Plus 4 short-dated Bill auction(s) totalling $296B — no direct ZN/ZT/ZB/ZF impact._

## Fed speakers — upcoming

**HIGH influence (0)**: Chair, Vice Chair, NY Fed.


**MEDIUM influence (3)**: governors + regional presidents.

## Regime read for `gap_fill` Treasury edge

- 10Y yield steady (-0.060% / 5d) → range regime, which is `gap_fill`'s preferred regime.

---

## Sources / freshness

- macro_levels.json — generated 2026-05-08T10:00:10.671016+00:00
- treasury_auctions.json — generated 2026-05-08T10:00:13.605609+00:00
- fed_speakers.json — generated 2026-05-08T10:00:14.770858+00:00
