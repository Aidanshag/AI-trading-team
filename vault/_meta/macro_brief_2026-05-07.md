---
type: macro_brief
date: 2026-05-07
generated_at: 2026-05-07T00:38:45.869666+00:00
generated_by: scripts.generate_macro_brief
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, all analysts]
read_on_first_wake: true
---

# Macro brief — 2026-05-07

> Auto-generated daily situational awareness for the front-office. Cross-checks against the live `gap_fill` Treasury edge: anything that shifts gaps from flow-driven (fade works) toward information-driven (fade fails).

> **TL;DR (2026-05-07)** — 10Y=4.43% | real=1.96% | USD=118.4 | VIX=17.4 · 9 auction(s) next 7d · 0 HIGH-influence Fed speaker(s) upcoming.

## Headline market levels

| Series | Label | Level | Δ 5d | Δ 20d |
|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 4.430 % | +0.070 | +0.100 |
| DGS2 | 2Y Treasury yield | 3.930 % | +0.090 | +0.120 |
| DGS30 | 30Y Treasury yield | 4.980 % | +0.040 | +0.080 |
| DFII10 | 10Y real yield (TIPS) | 1.960 % | +0.040 | +0.000 |
| T10Y2Y | 10s2s curve slope | 0.490 % | -0.010 | -0.010 |
| T10YIE | 10Y breakeven inflation | 2.420 % | -0.040 | +0.090 |
| DTWEXBGS | Broad USD (trade-weighted) | 118.393 idx | -0.337 | -2.264 |
| VIXCLS | VIX | 17.380 | -0.450 | -8.400 |
| SOFR | Secured Overnight Funding | 3.620 % | -0.020 | +0.000 |

## Treasury auctions — next 10 days

| Date | Type | Term | Amt ($B) | Affects |
|---|---|---|---:|---|
| 2026-05-07 | Bill | 8-Week | 85.0 | — |
| 2026-05-07 | Bill | 4-Week | 90.0 | — |
| 2026-05-11 | Note | 3-Year | 58.0 | — |
| 2026-05-11 | Bill | 13-Week | 0.0 | — |
| 2026-05-11 | Bill | 26-Week | 0.0 | — |
| 2026-05-12 | Bill | 6-Week | 0.0 | — |
| 2026-05-12 | Note | 10-Year | 42.0 | ZN |
| 2026-05-12 | Bill | 52-Week | 0.0 | — |
| 2026-05-13 | Bond | 30-Year | 25.0 | ZB |

## Fed speakers — upcoming

**HIGH influence (0)**: Chair, Vice Chair, NY Fed.


**MEDIUM influence (3)**: governors + regional presidents.

## Regime read for `gap_fill` Treasury edge

- 10Y yield steady (+0.070% / 5d) → range regime, which is `gap_fill`'s preferred regime.

---

## Sources / freshness

- macro_levels.json — generated 2026-05-07T00:32:57.259275+00:00
- treasury_auctions.json — generated 2026-05-07T00:36:35.965501+00:00
- fed_speakers.json — generated 2026-05-07T00:38:45.371243+00:00
