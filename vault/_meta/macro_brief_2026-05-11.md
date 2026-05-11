---
type: macro_brief
date: 2026-05-11
generated_at: 2026-05-11T12:32:14.196326+00:00
generated_by: scripts.generate_macro_brief
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, all analysts]
read_on_first_wake: true
---

# Macro brief — 2026-05-11

> Auto-generated daily situational awareness for the front-office. Cross-checks against the live `gap_fill` Treasury edge: anything that shifts gaps from flow-driven (fade works) toward information-driven (fade fails).

> **TL;DR (2026-05-11)** — 10Y=4.41% | real=1.96% | USD=118.4 | VIX=17.1 · 12 auction(s) next 7d · 0 HIGH-influence Fed speaker(s) upcoming.

## Headline market levels

| Series | Label | Level | Δ 5d | Δ 20d |
|---|---|---:|---:|---:|
| DGS10 | 10Y Treasury yield | 4.410 % | +0.010 | +0.120 |
| DGS2 | 2Y Treasury yield | 3.920 % | +0.040 | +0.140 |
| DGS30 | 30Y Treasury yield | 4.970 % | -0.010 | +0.070 |
| DFII10 | 10Y real yield (TIPS) | 1.960 % | +0.020 | +0.010 |
| T10Y2Y | 10s2s curve slope | 0.480 % | -0.030 | -0.020 |
| T10YIE | 10Y breakeven inflation | 2.450 % | -0.030 | +0.090 |
| DTWEXBGS | Broad USD (trade-weighted) | 118.393 idx | -0.337 | -2.264 |
| VIXCLS | VIX | 17.080 | +0.190 | -2.410 |
| SOFR | Secured Overnight Funding | 3.600 % | -0.040 | -0.010 |

## Treasury auctions — next 10 days

| Date | Time ET | Type | Term | Amt ($B) | Primary | Basis |
|---|---|---|---|---:|---|---|
| 2026-05-11 | 13:00 | Note | 3-Year | 58.0 | — | ZT, ZF |
| 2026-05-12 | 13:00 | Note | 10-Year | 42.0 | ZN | — |
| 2026-05-13 | 13:00 | Bond | 30-Year | 25.0 | ZB | — |
| 2026-05-20 | 13:00 | Bond | 20-Year | 0.0 | ZB | ZN, ZB |

_Plus 11 short-dated Bill auction(s) totalling $296B — no direct ZN/ZT/ZB/ZF impact._

## Fed speakers — upcoming

**HIGH influence (0)**: Chair, Vice Chair, NY Fed.


**MEDIUM influence (1)**: governors + regional presidents.

## Regime read for `gap_fill` Treasury edge

- 10Y yield steady (+0.010% / 5d) → range regime, which is `gap_fill`'s preferred regime.
- **TODAY** `auction-day` for 3-Year Note ($58B) affecting ZF, ZT — Active concession/auction window — gap_fill on the affected tenor at elevated risk RIGHT NOW.
- **TODAY** `concession` for 10-Year Note ($42B) affecting ZN — Active concession/auction window — gap_fill on the affected tenor at elevated risk RIGHT NOW.
- **TOMORROW** `auction-day` for 10-Year Note ($42B) affecting ZN — Pre-position: gap_fill on these symbols enters elevated-risk window at the next session open.
- **TOMORROW** `concession` for 30-Year Bond ($25B) affecting ZB — Pre-position: gap_fill on these symbols enters elevated-risk window at the next session open.

---

## Sources / freshness

- macro_levels.json — generated 2026-05-11T12:32:11.629255+00:00
- treasury_auctions.json — generated 2026-05-11T12:32:13.007869+00:00
- fed_speakers.json — generated 2026-05-11T12:32:14.069947+00:00
