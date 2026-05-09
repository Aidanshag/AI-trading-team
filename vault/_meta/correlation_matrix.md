---
type: meta
applies_to: [portfolio_manager, risk_manager, cio]
updated: 2026-04-25
source: Historical regime analysis + cross-asset transmission framework
---

# Correlation matrix: Expected correlations by regime

**Purpose:** Guide position sizing, correlation-aware hedging, and avoid stacking correlated trades that look different on the surface.

**Key insight:** Correlations are regime-dependent. A correlation that holds in reflation may invert in deflation. The PM must net positions not just by gross size, but by effective correlation within the current regime.

---

## Regime framework (reference)

- **Goldilocks** — growth up, inflation down → equities rally, bonds rally, commodities flat-to-down, USD down.
- **Reflation** — growth up, inflation up → equities choppy, commodities rally hard, bonds down, USD down, credit spreads widen.
- **Stagflation** — growth down, inflation up → equities crater, commodities rally, long-end bonds sell-off, gold up, USD up.
- **Deflation** — growth down, inflation down → equities down, bonds rally, commodities down hard, USD up, real yields down.
- **Transitional** — unclear direction; treat as low-conviction environment; reduce size across the board.

---

## Equity index futures (ES, NQ, RTY, YM)

### ES (S&P 500) as the primary benchmark

| Pair | Goldilocks | Reflation | Stagflation | Deflation | Notes |
|------|------------|-----------|-------------|-----------|-------|
| ES ↔ NQ | +0.92 | +0.85 | +0.88 | +0.90 | Stays high; NQ slightly more volatile in reflation |
| ES ↔ RTY | +0.88 | +0.72 | +0.80 | +0.86 | RTY decouples negatively in reflation (higher rates hit smaller-cap debt) |
| ES ↔ YM | +0.91 | +0.82 | +0.85 | +0.88 | YM similar to ES; slightly lower correlation in reflation |

**Within-complex sizing rule:** ES, NQ, RTY, YM are all the same regime trade (growth). A long ES + long RTY + long NQ reads as triple sizing on "US equities risk-on," not three independent ideas. Net them together.

---

## Index futures ↔ Rates

### ES ↔ Treasury futures (ZT, ZF, ZN, ZB)

| Regime | ES-ZT | ES-ZF | ES-ZN | ES-ZB | Interpretation |
|--------|-------|-------|-------|-------|---|
| Goldilocks | −0.35 | −0.38 | −0.40 | −0.42 | Both rally together; negative correlation reflects duration sensitivity (flight-to-quality is weak) |
| Reflation | −0.65 | −0.68 | −0.70 | −0.72 | STRONG negative correlation; equities crash as rates hammer bonds |
| Stagflation | −0.50 | −0.48 | −0.45 | −0.38 | Moderate negative; long-end decouples (inflation hedge) |
| Deflation | −0.25 | −0.28 | −0.30 | −0.35 | Moderate negative; both rally on flight-to-safety but bonds lead |

**Practical use:** A long ES position hedged with long ZB in reflation is WEAK hedging (−0.72 correlation means you still get hit). Better to size down ES or accept that in reflation, both legs lose together.

**Curve plays:** In transition or low-confidence environments, curve trades (e.g., long ZF short ZB) decorrelate from equity moves. Good hedge when equity directional view is unclear.

---

## Index futures ↔ Commodities

### ES ↔ Energy (CL, NG, RB, HO)

| Regime | ES-CL | ES-NG | ES-RB | ES-HO | Notes |
|--------|-------|-------|-------|-------|-------|
| Goldilocks | +0.15 | −0.05 | +0.10 | +0.12 | Weak positive or flat; commodities don't move much |
| Reflation | +0.65 | +0.45 | +0.60 | +0.62 | STRONG positive; both express "growth + inflation" theme |
| Stagflation | −0.35 | −0.10 | −0.20 | −0.25 | Negative (stocks down, energy up); NG flat-to-slightly-negative |
| Deflation | −0.20 | +0.05 | −0.10 | −0.08 | Weak; both down but equities down harder |

**Risk stacking warning:** A long ES + long CL in a reflation regime is NOT diversification—it's double-sizing on "risk-on, growth up." Net position size should reflect the combined payout.

### ES ↔ Metals (GC, SI, HG, PL, PA)

| Regime | ES-GC | ES-SI | ES-HG | ES-PL | ES-PA | Notes |
|--------|-------|-------|-------|-------|-------|-------|
| Goldilocks | −0.15 | −0.10 | +0.30 | +0.20 | +0.25 | Precious metals slightly negative; copper/PL positive (growth) |
| Reflation | +0.25 | +0.20 | +0.70 | +0.45 | +0.50 | Copper, PL, PA rally with growth; precious metals lag |
| Stagflation | −0.30 | −0.05 | −0.50 | −0.35 | −0.40 | GC up, stocks down; copper down hard (growth proxy); PL/PA mixed |
| Deflation | −0.25 | −0.20 | −0.20 | −0.10 | −0.15 | Gold as hedge; copper deflation proxy |

**Heuristic:** Copper and palladium = growth indicators. Gold and silver = inflation/safety. In reflation, gold lagging is normal. In deflation, copper crashing is normal.

### ES ↔ Grains (ZC, ZS, ZW, ZL, ZM)

| Regime | ES-ZC | ES-ZS | ES-ZW | ES-ZL | ES-ZM | Notes |
|--------|-------|-------|-------|-------|-------|-------|
| Goldilocks | +0.05 | +0.10 | +0.08 | +0.20 | +0.15 | Very weak; grains orthogonal in benign environment |
| Reflation | +0.40 | +0.45 | +0.35 | +0.50 | +0.48 | Positive; global growth → feed demand → meal/oil rally |
| Stagflation | +0.15 | +0.20 | +0.25 | +0.10 | +0.12 | Grains lag precious metals; weather >> macro |
| Deflation | −0.10 | −0.05 | −0.08 | −0.15 | −0.12 | Both down; grains lead lower (demand destruction) |

**Note:** Grains are driven more by weather and seasonal factors than macro. Use correlations as background context, not primary hedge logic.

### ES ↔ Softs & Livestock (KC, CT, SB, CC, LE, HE)

| Regime | ES-KC | ES-CT | ES-SB | ES-CC | ES-LE | ES-HE | Notes |
|--------|-------|-------|-------|-------|-------|-------|-------|
| Goldilocks | +0.10 | +0.05 | +0.08 | +0.12 | +0.15 | +0.10 | Weak; softs often weather/supply-driven |
| Reflation | +0.35 | +0.25 | +0.30 | +0.40 | +0.50 | +0.45 | Positive; feed costs rise, softs rally |
| Stagflation | +0.10 | +0.15 | +0.20 | +0.25 | +0.05 | +0.08 | Softs rally (inflation play); livestock production costs soar (margin squeeze) |
| Deflation | −0.05 | −0.10 | −0.12 | −0.08 | +0.10 | +0.05 | Livestock = food staple, slightly positive |

---

## FX ↔ Equities and Rates

### ES ↔ FX (6E, 6B, 6J, 6A, 6C, 6S)

| Regime | ES-6E | ES-6B | ES-6J | ES-6A | ES-6C | ES-6S | Notes |
|--------|-------|-------|-------|-------|-------|-------|-------|
| Goldilocks | +0.30 | +0.25 | −0.10 | +0.35 | +0.30 | +0.20 | Risk-on: commodity currencies (AUD, CAD) rally with growth; JPY down |
| Reflation | +0.45 | +0.35 | −0.40 | +0.55 | +0.50 | +0.30 | Risk-on accelerates; JPY sold off hard (carry unwind concern but growth wins) |
| Stagflation | −0.10 | −0.05 | +0.40 | −0.20 | −0.15 | −0.10 | Risk-off; JPY rallies as safe-haven; commodity currencies collapse |
| Deflation | −0.20 | −0.15 | +0.35 | −0.30 | −0.25 | −0.05 | JPY strong (safety); commodity currencies weak; DXY up, EM FX down |

**Key insight:** JPY is a risk-off hedge; commodity currencies (AUD, CAD, NZD proxied via AUD) are risk-on leveraged plays.

### ZN (10Y) ↔ FX (rate differential framework)

| Regime | ZN-6E | ZN-6B | ZN-6J | ZN-6A | ZN-6C | ZN-6S | Notes |
|--------|-------|-------|-------|-------|-------|-------|-------|
| Goldilocks | +0.50 | +0.45 | −0.20 | +0.55 | +0.60 | +0.40 | Higher US rates → stronger USD + commodity currency appreciation |
| Reflation | +0.55 | +0.50 | −0.30 | +0.60 | +0.65 | +0.45 | Rising US rates (inflation) → USD strength + divergence vs others |
| Stagflation | −0.10 | −0.05 | +0.25 | −0.15 | −0.10 | −0.05 | Curve inversion fears; long-end pressure; JPY safe haven |
| Deflation | −0.35 | −0.30 | +0.40 | −0.40 | −0.35 | −0.25 | Falling US rates but fall slower than global; soft-dollar play |

**Practical rule:** When US 10Y is rising (reflation, strong growth), EUR, GBP, AUD, CAD tend to weaken vs USD. When US 10Y is falling (deflation, recession fears), JPY and CHF tend to strengthen.

---

## Within-asset-class correlations (same regime, different symbols)

### Energy complex internal correlations (Goldilocks regime — reference)

| Pair | Correlation | Notes |
|------|---|---|
| CL ↔ RB | +0.88 | Refining input–output; move together |
| CL ↔ HO | +0.92 | Crude → heating oil path; highest correlation |
| CL ↔ NG | +0.25 | Different production (shale NG, OPEC crude); weak correlation |
| RB ↔ HO | +0.85 | Both distillates; tight correlation |

**Implication:** A long CL + long RB is essentially one trade (WTI commodity). NG is the diversifier.

### Metals internal correlations (Goldilocks regime)

| Pair | Correlation | Notes |
|------|---|---|
| GC ↔ SI | +0.75 | Precious metals complex; correlated |
| GC ↔ HG | +0.35 | Gold = inflation hedge; copper = growth; weak correlation |
| HG ↔ PL | +0.70 | Industrial metals; co-move with growth |
| PL ↔ PA | +0.68 | Platinum-group metals; move together |

**In stagflation:** GC ↔ HG drops to +0.08 (GC rallies, HG crashes). Gold becomes the diversifier.

### Grains internal correlations (Goldilocks regime)

| Pair | Correlation | Notes |
|------|---|---|
| ZC ↔ ZS | +0.70 | Feed costs link corn and soybeans |
| ZS ↔ ZL | +0.85 | Soybean crush; oil and meal co-move |
| ZC ↔ ZW | +0.55 | Different regions, different curves; moderate correlation |

**Note:** Weather events break these correlations. A drought in Argentina can spike SB while leaving ZC flat.

---

## Regime-neutral hedging (structural plays that work across regimes)

| Strategy | Pairs | Goldilocks | Reflation | Stagflation | Deflation | Avg Effectiveness |
|----------|-------|------------|-----------|-------------|-----------|---|
| Long GC, short ES | ES-GC corr | −0.15 | +0.25 | −0.30 | −0.25 | Weak; gold rallies in stagflation/deflation only |
| Long JPY, short ES | ES-JPY corr | −0.10 | −0.40 | +0.40 | +0.35 | Works in risk-off; fails in reflation |
| Long ZB, short ES | ES-ZB corr | −0.42 | −0.72 | −0.38 | −0.35 | Weak; fails worst in reflation |
| Long 6J, short ES | ES-JPY via 6J | (−0.10) | (−0.40) | (+0.40) | (+0.35) | Same as JPY FX |
| Long VX futures (via proxy) | Equity vol hedge | Variable | Low (cost-of-carry) | Excellent | Good | Good in crises; poor in trends |

**Hard truth:** There is no perfect hedge that works in all regimes. The best hedge is position sizing and accepting that in reflation, long equities + long bonds both get hit.

---

## Practical PM rules from this matrix

1. **Net positions by correlation, not gross size.** A long ES + short 10Y ZB in reflation (−0.72 correlation) is NOT a hedge—your real exposure is still ~long equities with 28% cushion. Size accordingly.

2. **Diversifying asset classes within a regime:**
   - Goldilocks: Add grains, softs, commodity FX (AUD, CAD). Minimize JPY, bonds.
   - Reflation: Max weight on CL, ZS, ZL, ZM, commodities generally. Minimize bonds and JPY.
   - Stagflation: Gold, long-end bonds, EM FX (harder to access as futures), minimal copper/equities.
   - Deflation: Bonds (ZB long-end), JPY, CHF, minimal commodities and equities.

3. **Warn on structural stacking:**
   - A thesis like "long ES + long NG + long RB" in reflation is not three independent ideas; it's tripled reflation exposure. Reduce conviction or size on two of the three.
   - A thesis like "long ES + long 6A (AUD) + long ZL (soybean oil)" in reflation is better diversified: equities + commodity FX + ag commodity, but still net positive. Check correlation.

4. **Intra-complex (same sector):**
   - Within energy: long CL + long RB is almost redundant (−0.88 correlation). If bullish energy, pick one or reduce both. Long CL + long NG is better (0.25 correlation).
   - Within metals: long GC + long SI is good diversification (0.75, not 1.0). Long GC + long HG is better diversification—but they behave oppositely in reflation, so have a reason.

5. **Curve trades (long ZF, short ZB; or long ZT, short ZF):**
   - Curve strategies decorrelate from equity market direction. Useful when macro regime is unclear or transitional.
   - In goldilocks, curve is usually stable (low volatility). In reflation, curve steepens (short-end up, long-end down) → trade short-end longs against long-end shorts.

---

## When the regime changes: the correlation shock

When the regime transitions (e.g., goldilocks → reflation), correlations shift violently:

- **CL ↔ ES:** jumps from +0.15 → +0.65 (suddenly CL rallies with equities, not in opposition).
- **GC ↔ ES:** jumps from −0.15 → +0.25 (gold stops being a gold stock hedge; starts rallying with reflation euphoria).
- **ES ↔ ZB:** becomes MORE negative, not less (−0.42 → −0.72; bonds get crushed as rates rise).

**Risk management implication:** The hedge that worked in regime A may hurt you in regime B. This is why the CIO's regime read is critical: every Friday, re-check your live theses against the regime update. If the regime changed and your hedge inverted, close or rebalance.

---

## Data sources & update frequency

- **Historical correlations** (1Y rolling window): from FRED (macro), Topstep tick data (futures OHLCV), CFTC positioning (sentiment shift confirmation).
- **Update cycle:** Monthly or when regime changes; intra-regime correlations are relatively stable.
- **Exception:** Energy (CL, NG, RB, HO) correlations update weekly because of geopolitical/supply shocks; metals (GC, HG, PL) weekly due to Fed rate signals.

---

## Related references

- `vault/playbooks/macro_framework.md` — how regimes shift; what to look for.
- `vault/playbooks/position_sizing.md` — size positions accounting for correlation (not gross notional).
- `vault/playbooks/psychology_and_discipline.md` — why it's emotionally hard to cut a good thesis when regime changes.
- `vault/regime/current.md` — the CIO's live regime read; check here before PM proposal goes to Risk.
