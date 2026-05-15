---
type: macro_brief
date: 2026-05-15
generated_at: 2026-05-15T10:00:12.839887+00:00
generated_by: scripts.generate_macro_brief
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, all analysts]
read_on_first_wake: true
---

# Macro brief — 2026-05-15

> Auto-generated daily situational awareness for the front-office. Cross-checks against the live `gap_fill` Treasury edge: anything that shifts gaps from flow-driven (fade works) toward information-driven (fade fails).

> **TL;DR (2026-05-15)** — 10Y=4.46% | real=1.99% | USD=118.0 | VIX=17.9 · 5 auction(s) next 7d · 0 HIGH-influence Fed speaker(s) upcoming.

## Headline market levels

| Series | Label | Level | Δ 5d | Δ 20d |
|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 4.460 % | +0.100 | +0.170 |
| DGS2 | 2Y Treasury yield | 3.980 % | +0.110 | +0.220 |
| DGS30 | 30Y Treasury yield | 5.030 % | +0.090 | +0.140 |
| DFII10 | 10Y real yield (TIPS) | 1.990 % | +0.050 | +0.090 |
| T10Y2Y | 10s2s curve slope | 0.480 % | -0.010 | -0.050 |
| T10YIE | 10Y breakeven inflation | 2.470 % | +0.050 | +0.080 |
| DTWEXBGS | Broad USD (trade-weighted) | 118.039 idx | -0.353 | -0.816 |
| VIXCLS | VIX | 17.870 | +0.480 | -0.300 |
| SOFR | Secured Overnight Funding | 3.590 % | -0.020 | -0.130 |

## Treasury auctions — next 10 days

| Date | Time ET | Type | Term | Amt ($B) | Primary | Basis |
|---|---|---|---|---:|---|---|
| 2026-05-20 | 13:00 | Bond | 20-Year | 16.0 | ZB | ZN, ZB |

_Plus 4 short-dated Bill auction(s) totalling $270B — no direct ZN/ZT/ZB/ZF impact._

## Fed speakers — upcoming

**HIGH influence (0)**: Chair, Vice Chair, NY Fed.


**MEDIUM influence (3)**: governors + regional presidents.

## Regime read for `gap_fill` Treasury edge

- **10Y borderline** (+0.100% / 5d, rising) → between range and directional regime. Treat the next 1-2 sessions as elevated watch — if Δ5d crosses ±0.10%, the gap_fill long-fade thesis is in directional-regime caution territory.

---

## Sources / freshness

- macro_levels.json — generated 2026-05-15T10:00:10.594799+00:00
- treasury_auctions.json — generated 2026-05-15T10:00:11.860245+00:00
- fed_speakers.json — generated 2026-05-15T10:00:12.754034+00:00
