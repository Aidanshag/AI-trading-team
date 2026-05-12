---
type: macro_brief
date: 2026-05-12
generated_at: 2026-05-12T10:00:12.263992+00:00
generated_by: scripts.generate_macro_brief
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, all analysts]
read_on_first_wake: true
---

# Macro brief — 2026-05-12

> Auto-generated daily situational awareness for the front-office. Cross-checks against the live `gap_fill` Treasury edge: anything that shifts gaps from flow-driven (fade works) toward information-driven (fade fails).

> **TL;DR (2026-05-12)** — 10Y=4.38% | real=1.93% | USD=118.0 | VIX=17.2 · 10 auction(s) next 7d · 0 HIGH-influence Fed speaker(s) upcoming.

## Headline market levels

| Series | Label | Level | Δ 5d | Δ 20d |
|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 4.380 % | -0.010 | +0.070 |
| DGS2 | 2Y Treasury yield | 3.900 % | +0.020 | +0.090 |
| DGS30 | 30Y Treasury yield | 4.950 % | -0.020 | +0.040 |
| DFII10 | 10Y real yield (TIPS) | 1.930 % | +0.020 | -0.020 |
| T10Y2Y | 10s2s curve slope | 0.470 % | -0.030 | -0.050 |
| T10YIE | 10Y breakeven inflation | 2.470 % | -0.030 | +0.090 |
| DTWEXBGS | Broad USD (trade-weighted) | 118.039 idx | -0.353 | -0.816 |
| VIXCLS | VIX | 17.190 | +0.200 | -2.040 |
| SOFR | Secured Overnight Funding | 3.600 % | -0.040 | -0.010 |

## Treasury auctions — next 10 days

| Date | Time ET | Type | Term | Amt ($B) | Primary | Basis |
|---|---|---|---|---:|---|---|
| 2026-05-12 | 13:00 | Note | 10-Year | 42.0 | ZN | — |
| 2026-05-13 | 13:00 | Bond | 30-Year | 25.0 | ZB | — |
| 2026-05-20 | 13:00 | Bond | 20-Year | 0.0 | ZB | ZN, ZB |

_Plus 9 short-dated Bill auction(s) totalling $130B — no direct ZN/ZT/ZB/ZF impact._

## Fed speakers — upcoming

**HIGH influence (0)**: Chair, Vice Chair, NY Fed.


**MEDIUM influence (1)**: governors + regional presidents.

## Regime read for `gap_fill` Treasury edge

- 10Y yield steady (-0.010% / 5d) → range regime, which is `gap_fill`'s preferred regime.
- **TODAY** `auction-day` for 10-Year Note ($42B) affecting ZN — Active concession/auction window — gap_fill on the affected tenor at elevated risk RIGHT NOW.
- **TODAY** `concession` for 30-Year Bond ($25B) affecting ZB — Active concession/auction window — gap_fill on the affected tenor at elevated risk RIGHT NOW.
- **TOMORROW** `auction-day` for 30-Year Bond ($25B) affecting ZB — Pre-position: gap_fill on these symbols enters elevated-risk window at the next session open.

---

## Sources / freshness

- macro_levels.json — generated 2026-05-12T10:00:09.278178+00:00
- treasury_auctions.json — generated 2026-05-12T10:00:10.959937+00:00
- fed_speakers.json — generated 2026-05-12T10:00:12.104101+00:00
