---
type: macro_brief
date: 2026-05-13
generated_at: 2026-05-13T10:00:26.665647+00:00
generated_by: scripts.generate_macro_brief
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, all analysts]
read_on_first_wake: true
---

# Macro brief — 2026-05-13

> Auto-generated daily situational awareness for the front-office. Cross-checks against the live `gap_fill` Treasury edge: anything that shifts gaps from flow-driven (fade works) toward information-driven (fade fails).

> **TL;DR (2026-05-13)** — 10Y=4.42% | real=1.95% | USD=118.0 | VIX=18.4 · 8 auction(s) next 7d · 0 HIGH-influence Fed speaker(s) upcoming.

## Headline market levels

| Series | Label | Level | Δ 5d | Δ 20d |
|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 4.420 % | -0.030 | +0.120 |
| DGS2 | 2Y Treasury yield | 3.950 % | +0.000 | +0.170 |
| DGS30 | 30Y Treasury yield | 4.980 % | -0.040 | +0.080 |
| DFII10 | 10Y real yield (TIPS) | 1.950 % | +0.000 | +0.030 |
| T10Y2Y | 10s2s curve slope | 0.460 % | -0.040 | -0.040 |
| T10YIE | 10Y breakeven inflation | 2.470 % | +0.000 | +0.100 |
| DTWEXBGS | Broad USD (trade-weighted) | 118.039 idx | -0.353 | -0.816 |
| VIXCLS | VIX | 18.380 | +0.090 | -0.740 |
| SOFR | Secured Overnight Funding | 3.600 % | -0.030 | -0.030 |

## Treasury auctions — next 10 days

| Date | Time ET | Type | Term | Amt ($B) | Primary | Basis |
|---|---|---|---|---:|---|---|
| 2026-05-13 | 13:00 | Bond | 30-Year | 25.0 | ZB | — |
| 2026-05-20 | 13:00 | Bond | 20-Year | 0.0 | ZB | ZN, ZB |

_Plus 7 short-dated Bill auction(s) totalling $264B — no direct ZN/ZT/ZB/ZF impact._

## Fed speakers — upcoming

**HIGH influence (0)**: Chair, Vice Chair, NY Fed.


**MEDIUM influence (1)**: governors + regional presidents.

## Regime read for `gap_fill` Treasury edge

- 10Y yield steady (-0.030% / 5d) → range regime, which is `gap_fill`'s preferred regime.
- **TODAY** `auction-day` for 30-Year Bond ($25B) affecting ZB — Active concession/auction window — gap_fill on the affected tenor at elevated risk RIGHT NOW.

---

## Sources / freshness

- macro_levels.json — generated 2026-05-13T10:00:20.434309+00:00
- treasury_auctions.json — generated 2026-05-13T10:00:25.088472+00:00
- fed_speakers.json — generated 2026-05-13T10:00:26.576587+00:00
