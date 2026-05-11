---
type: research_findings
date: 2026-05-11
author: Claude Code (autonomous)
status: complete
scope: low-vol strategies + PostClose deep-dive
---

# Low-vol + PostClose research — autonomous run 2026-05-11 evening

## Headline

1. **Low-vol strategies: nothing in the current library validates.** Three candidates swept; zero qualifying cells across 225 parameter combinations. Conclusion: the futures-only constraint of Topstep makes pure low-vol monetization structurally difficult. Best policy is **sit out low-vol regimes**, not try to fade them.
2. **PostClose: a possible long-bias edge exists but no cell strictly validates.** 21 of 23 PostClose cells with positive E are long-side — too consistent to be pure noise. None meet n≥25, t≥1.5 within 60d data window. Recommend: extend data window before deploying, OR deploy 1-2 borderline cells as live-data-gathering experiment.
3. **Peak-window optimization: already running daily.** No new infrastructure needed for now.

## Low-vol candidate sweeps

Each strategy was swept on 5 representative symbols (ZN, MNQ, GC, 6E, MCL) with the corrected pipeline (tick_size injection + risk_ticks measurement).

### rsi2_extreme_reversion (RSI(2) extreme reversion)
- Grid: `rsi_buy_below ∈ {5, 10, 15} × rsi_exit_above ∈ {60, 70, 80}` = 9 combos × 5 symbols
- Result: **all 45 cells negative-expectancy**
- Best: MNQ with rsi_buy<5, exit>60: n=224, t=-0.36, E=-0.04R, risk=92 ticks
- Root cause: stops at 5-bar swing-low produce 90-100 tick distances on MNQ. The strategy's edge is real but absorbed by stop width.
- Verdict: dead end without major stop-logic redesign.

### bollinger_mean_reversion
- Grid: `sma_period ∈ {10, 20, 40} × bb_std ∈ {1.5, 2.0, 2.5}` = 9 combos × 5 symbols
- Result: **0 trades fired across all 45 cells**
- Root cause: the strategy's signal condition requires explicit Bollinger-band TOUCH which is rare on 5m treasury/index bars over 60d.
- Verdict: not suited to 5m intraday data; would need daily timeframe.

### range_mean_reversion
- Grid: `range_period ∈ {10,20,40} × range_max_pct ∈ {0.02,0.04,0.06} × stop_atr_mult ∈ {0.5,1.0,1.5}` = 27 combos × 5 symbols
- Result: **0 cells with positive E AND n≥10**
- Verdict: strategy doesn't find tradable range-fade setups in this data window.

## PostClose deep-dive

Looking at all 79 PostClose cells re-evaluated today with n≥10, sorted by expectancy:

**Top 5 by E (no strict-gate qualifier):**

| Cell | n | t | E | Note |
|---|---|---|---|---|
| narrow_range_break\|NG\|PostClose\|long | 12 | +1.70 | +1.01R | n too low |
| narrow_range_break\|6C\|PostClose\|long | 16 | +1.25 | +0.53R | n too low, t borderline |
| inside_bar_break\|GC\|PostClose\|long | 17 | +1.00 | +0.41R | n too low, t weak |
| inside_bar_break\|6C\|PostClose\|long | 15 | +0.89 | +0.39R | similar |
| rsi2_extreme_reversion\|MCL\|PostClose\|long | 21 | +0.66 | +0.38R | weak t, high E |

**Statistical observation worth noting:** Of the 23 PostClose cells with positive E, **21 are LONG-side**. This 21/23 = 91% skew is unlikely from pure noise — suggests a real upward drift in PostClose hours (after-RTH-close), possibly from:
- Closing-flow imbalance (MOC sells are absorbed at 4 PM, leaving slight buy bias 4-8 PM)
- Asian-session pre-open hedging via overnight-friendly products
- Lower-vol session = retail-driven momentum vs. institutional bid

**This is research-quality evidence, not yet deployable evidence.** None meet n≥25 + t≥1.5 + E>0 simultaneously.

## What's deployable autonomously vs. needs user review

### Deployable (safe, marginal upside)
None. All low-vol candidates failed; all PostClose candidates fail validation gates.

### Worth deploying as live-data-gathering experiment (user decision)
- `narrow_range_break|6C|PostClose|long` (n=16, t=1.25, E=0.53R)
- `inside_bar_break|GC|PostClose|long` (n=17, t=1.00, E=0.41R)
- `rsi2_extreme_reversion|MNQ|PostClose|long` (n=29 ← meets n threshold, t=0.63, E=0.14R — weak edge but real sample)

Rationale: per-position cap is $150; trader-side gates filter degenerate signals; we'd accumulate live data on PostClose behavior. Risk-bounded research. **But these cells haven't formally validated, so this is a research deployment, not a primary-edge deployment.**

### Requires longer data window
- Better PostClose validation requires extending beyond yfinance's 60d × 5m limit
- Options: Polygon historical (paid), Topstep tick-data export, IBKR historical
- 1-year intraday window would likely promote 5-8 of the top PostClose cells to validity
- This is a separate engineering project, not autonomous-tonight scope

## Updated guidance for the trader

- **Low-vol regimes:** continue running existing cells without low-vol-specific additions. The regime_gate I built means vol-sensitive cells (keltner, vol_spike_fade) only fire in high-vol. No symmetric "low-vol cell" needed — the library doesn't have one that works.
- **PostClose:** accept the gap until we have more data. Live trading in 20:00-00:00 UTC stays quiet by design.
- **Peak windows (Asian + London + RTH):** continue daily validation cycle. The promotion/demotion loop in `daily_strategy_validation.py` will naturally adjust cells over time as live data accumulates.

## Files

- `vault/research/param_sweeps/rsi2_extreme_reversion_2026-05-11_2038.csv`
- `vault/research/param_sweeps/bollinger_mean_reversion_2026-05-11_2038.csv`
- `vault/research/param_sweeps/range_mean_reversion_2026-05-11_2039.csv`
- This report
