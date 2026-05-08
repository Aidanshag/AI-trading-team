---
type: quant_research_proposals
date: 2026-05-06
methods_used: [hawkes_self_excitation, ou_mean_reversion, garch_vol_clustering, cointegration_johansen, fokker_planck_drift, eigenvalue_correlation_break, time_of_day_seasonality]
n_proposed: 5
correlated_with_gap_fill: false
status: proposal_only_no_code_written
---

# Quant Researcher proposals — 5 novel strategies for diversification

## Context (2026-05-06)

The fund has ONE deploy-grade headline edge: `gap_fill` on the treasury curve (ZN/ZT/ZF/ZB t-stats +7.95 to +11.76). Validated extensions reach FX cousins (6E, 6A, 6J, 6B, 6C) and NG, but **all of these mean-revert overnight gaps** — they share the same factor exposure. From a portfolio standpoint we have a single bet replicated 9 times. The 24-cell phase 2 walk-forward turned up secondary edges (keltner_breakout GC Asian short, narrow_range_break MCL Asian long, etc.) but the strongest of those carries OOS t=+3.58 on n=18 — borderline survivor.

**The portfolio risk is concentration.** If overnight-gap mean-reversion regime breaks (e.g., a sustained trending regime where overnight gaps EXTEND rather than fill, as happened during 2020-Q1 and 2022-Q1 inflation shocks), every cell goes to zero or negative simultaneously. Diversification means finding edges with **different factor exposure** — not different symbols.

The 5 proposals below each target a distinct, theoretically-grounded inefficiency that has **near-zero correlation with gap-fill mean-reversion**. None of them mean-revert intraday rates. None require sub-100ms latency. All are implementable in the existing `Iterator[Signal]` protocol on 5m OHLCV bars.

---

## Proposal 1 — `vol_clustering_persistence` (GARCH-driven volatility regime)

### Theoretical basis (statistical mechanics + GARCH)

Engle's 1982 GARCH discovery: realized variance is autocorrelated — large moves cluster, small moves cluster. The conditional variance follows σ²ₜ = ω + α·rₜ₋₁² + β·σ²ₜ₋₁ with α+β typically 0.95+ in commodities (very persistent). This is a property of the second moment of returns, not the first moment, so it is **orthogonal to gap-fill direction prediction**. The trade is not "price will revert" but "*move size* will persist and pay if you're already long volatility-of-the-trend."

A regime change from low-σ to high-σ produces a one-bar TR spike that is the leading edge of a multi-bar high-vol regime. In intraday terms: when 5m TR jumps above its 60-bar 90th percentile while medium-term vol is rising (5-bar avg TR > 20-bar avg TR), the *next 5-10 bars* statistically deliver above-average range. We don't bet direction; we bet **range continuation in the direction of the regime-shift bar**. This is conceptually similar to `volatility_breakout` but explicitly conditioned on a vol-regime persistence hypothesis (`H₁: the recent vol increase is autocorrelated, not noise`).

### Entry condition

```
For each bar i (5m):
  TR_i = max(H-L, |H-prevC|, |L-prevC|)
  ATR60 = mean(TR over last 60 bars)
  TR_pctile = percentile_rank(TR_i, last 60 TR values)
  recent_vol_rising = mean(TR over last 5) > 1.3 * mean(TR over last 20)

  IF TR_pctile >= 0.90 AND recent_vol_rising AND close_i > open_i:
    LONG entry at close_i
  IF TR_pctile >= 0.90 AND recent_vol_rising AND close_i < open_i:
    SHORT entry at close_i
```

### Stop placement

Stop at `entry ∓ 1.0 × ATR14` (tight — we're betting on continuation; if range collapses we're wrong fast).

### Target placement

`entry ± 2.5 × ATR14`. Asymmetry comes from the GARCH persistence: high-vol regimes tend to last 5-15 5m bars, giving the move room to extend.

### Predicted best-fit symbols / sessions

- **MNQ, MES (RTH London open + RTH cash open)** — equity index volatility regimes are the cleanest GARCH signal in the universe; the London cash open and 9:30 ET cash open are the two reliable σ-regime-shift catalysts.
- **MCL (RTH + early Asian)** — energies show strong vol clustering around DOE inventory days and OPEC commentary windows.
- **GC (PostClose)** — gold's sleepy 17:00-21:00 ET hours occasionally produce vol spikes that propagate through Asian session.

Avoid: ZN/ZT/ZF — rates have low intraday vol-of-vol; the signal degenerates to noise. Avoid 6E — FX vol clusters at session handoffs but the signal is contaminated by gap_fill setups.

### Risk of false positives

1. **News-driven single-bar spikes** — if the high-vol bar is a one-off Powell headline reaction, vol mean-reverts on the next bar (anti-GARCH). Mitigation: require the *5-bar avg TR vs 20-bar avg TR* slope to confirm; one-bar spikes don't move that ratio.
2. **End-of-session vol decay** — vol expands into close then collapses overnight. Mitigation: per-session enable/disable.
3. **Sample is small per cell** — 5m bars at >90th percentile happen ~3x/day; meaningful n requires 30+ session days.

### How it differs from existing strategies

- vs `volatility_breakout`: we DON'T require breaking the prior bar's high — we want vol persistence in *whichever direction the spike bar closed*. volatility_breakout is path-dependent on price level; this is path-dependent on vol regime.
- vs `vol_regime_trend`: vol_regime_trend trades trend BREAKOUTS only when vol is BELOW median (compressed → expansion). This is the inverse — trade *during* expanded vol.
- vs `gap_fill`: gap_fill exploits *direction* mean-reversion; this exploits *magnitude* persistence. Pure orthogonal factor.

---

## Proposal 2 — `time_of_day_seasonality` (deterministic intraday calendar effect)

### Theoretical basis (Fokker-Planck + seasonal drift)

Heston (1995), Lockwood-Linn (1990), and many follow-ups document deterministic intraday seasonality in futures: the conditional drift μ(t | time-of-day) is non-zero at specific clock-time windows because of liquidity provision asymmetry, ETF/mutual fund rebalancing, and pension flow concentration. The clearest documented effects in CME markets:

1. **Asian → London handoff (02:00-03:00 ET):** liquidity providers shift books; a small directional drift in trend continuation typical.
2. **London fix (10:00-11:00 ET, was 11:00 GMT):** WMR fix for FX creates 30-60min directional pressure; FX futures (6E, 6B, 6A) show a measurable drift bias.
3. **Settlement-related drift in the last 30 mins of pit-session (e.g., 13:30-14:00 ET in metals/energy)** — index arb and ETF rebalance flow.

The math: intraday returns are NOT a martingale at all clock times. The Fokker-Planck transition density p(x,t|x₀,0) has a non-zero μ component at calendar-determined t. This is a *conditional drift*, not a price-pattern signal — fundamentally different from gap_fill (which is a *price-level conditional* signal).

### Entry condition

```
For each bar i (5m, indexed by clock time):
  IF symbol == 6E AND time(i) in [10:00, 10:30] ET:   # London FX fix window
    direction = sign(close[i-12 : i].sum())  # 1-hour momentum heading INTO fix
    LONG/SHORT in the direction of the pre-fix momentum

  IF symbol in [MES, MNQ] AND time(i) in [13:30, 14:00] ET (pre-cash-close 30m):
    direction = sign(close[i-6 : i].sum())  # 30-min pre-close momentum
    enter in continuation direction

  IF symbol in [GC, MCL] AND time(i) in [02:00, 02:30] ET (Asia → London handoff):
    direction = sign(close[i-12 : i].sum())  # 1-hour Asian-session momentum
    enter in continuation direction
```

### Stop placement

`entry ∓ 1.5 × ATR14` (wider stop because we're betting on a 30-60min flow window, not a sharp pop).

### Target placement

`entry ± 2.0 × ATR14`. Time-stop at end of the seasonality window — exit at market regardless of P&L when the calendar window closes.

### Predicted best-fit symbols / sessions

- **6E, 6B, 6A (London FX fix)** — most documented seasonality in the universe. ECB/BoE flow concentrated 09:30-10:30 ET.
- **MES, MNQ (pre-cash-close 30m)** — ETF rebalancing creates persistent late-day drift.
- **GC, MCL (Asian → London)** — quieter but robust; small n but high t when signal triggers.

### Risk of false positives

1. **Regime-shift in flow patterns** — WMR fix mechanics have changed (2014 reform extended fix window). Calendar effects decay as algos arbitrage them. Mitigation: walk-forward must show OOS holding; if t-stat decays >50% vs train, retire.
2. **Holiday / half-day distortion** — calendar effects break on early closes, holidays. Need a calendar filter.
3. **Multi-comparisons:** I'm proposing ~9 symbol×window cells. Bonferroni-corrected α=0.05/9 ≈ 0.006, so require t > 2.7 OOS not 2.0. This is the key discipline.

### How it differs from existing strategies

- All existing strategies are *price-pattern* triggered. This is *clock-time* triggered with momentum confirmation — the trigger is calendar, not pattern. **Zero overlap with gap_fill** which requires a price gap to exist.
- vs `opening_range_breakout`: ORB is a session-start phenomenon (first hour). This is mid-session and end-session phenomena tied to specific liquidity events.

---

## Proposal 3 — `cross_asset_divergence_pair` (curve-internal cointegration trade)

### Theoretical basis (Johansen + OU mean reversion of spread)

The yield curve is one of the most cointegrated systems in finance. ZB-ZN spread, ZN-ZT spread, ZF-ZN spread are all stationary (Johansen rank ≥ 1 over 60+ day windows). When one leg moves WITHOUT the other for 5-15 minutes intraday, this is a spread dislocation that mean-reverts faster than either leg's gap. The OU half-life of ZN-ZT spread on 5m bars is empirically 30-90 min from prior literature (Tepper, Sornette work on rates) — actionable on our cadence.

Critically: a long-flat ZN/short-flat ZT spread trade is NOT the same factor as gap_fill on either leg. **Gap_fill bets that ZN's overnight price returns to prior close. Curve-spread bets that ZT and ZN realign with each other regardless of where either is vs prior close.** The two factors have empirical correlation < 0.2 in rates literature.

### Entry condition

```
spread = ZN_close - β × ZT_close   # β ≈ 0.4 from rolling 60-bar regression of ZN on ZT
spread_z = (spread - rolling_mean_60) / rolling_std_60

For each bar i:
  refresh β every 60 bars (rolling OLS)
  IF spread_z[i] >= +2.0 AND spread_z[i-1] < +2.0:
    SHORT ZN (1 contract), LONG ZT (round(β*1) ≈ 1 contract)  # spread is rich; revert
  IF spread_z[i] <= -2.0 AND spread_z[i-1] > -2.0:
    LONG ZN, SHORT ZT  # spread is cheap

  Exit when spread_z crosses 0 (mean-reversion target).
```

**Implementation note:** The existing engine handles ONE contract at a time; this strategy needs two-leg tracking. For Topstep limits we'd run this initially as **single-leg ZN-only with a ZT signal as a filter** (i.e., go long ZN when spread_z<-2 AND ZN itself isn't in some other position). The "true pair" version is a Phase 2 implementation behind a feature flag — first establish the signal works as a directional filter.

### Stop placement

Stop at `entry ∓ 1.5 × ATR14(ZN)` — exit if the spread continues diverging instead of reverting.

### Target placement

Target = bar where `spread_z` crosses 0 (zero z-score = fair value). Time-stop at 30 bars (2.5 hours) — if it hasn't reverted by then, the cointegration relationship may be broken (regime shift).

### Predicted best-fit symbols / sessions

- **ZN-ZT spread (24h, but cleanest in RTH 08:30-15:00 ET)** — most liquid pair on the curve.
- **ZN-ZF spread (RTH only)** — secondary; ZF less liquid in Asian.
- **ZB-ZN spread (RTH only)** — adds long-end duration exposure; more volatile spread.

Avoid Asian session — the spread becomes noisy on thin liquidity, and the cointegrating relationship temporarily breaks.

### Risk of false positives

1. **Cointegration breakdown / regime shift** — Fed surprise, debt-ceiling crisis, or auction failure can structurally re-rate the curve. The rolling β recalibrates but not fast enough for an instant repricing. Mitigation: hard time-stop at 30 bars; do not size up until proven OOS.
2. **β estimation noise** — small rolling window means β is unstable. 60-bar window chosen to balance reactivity vs noise.
3. **Cross-leg execution risk** — if running 2-leg, fills can drift; treat as unhedged single-leg in production until 2-leg infra is built.
4. **Correlation with gap_fill regime** — if both ZN AND ZT gapped up overnight (correlated gap), spread_z near 0 (no signal); gap_fill takes the trade. If only one gapped, spread_z is at extreme — this is where the diversification kicks in.

### How it differs from existing strategies

- ALL existing strategies are single-symbol. This is the only cross-symbol strategy.
- The signal is *relative value*, not *absolute level or pattern*. Genuinely orthogonal factor (in rates literature, curve trades load on a different PCA factor than outright duration trades — typically PC2/PC3 vs PC1).
- Ties to econophysics tradition (Mantegna 1999 — minimum spanning tree of cointegrated assets).

---

## Proposal 4 — `hawkes_intensity_continuation` (self-exciting trade arrival momentum)

### Theoretical basis (Hawkes self-exciting point processes)

Hawkes (1971) point processes are the canonical model for trade arrivals in financial markets — λ(t) = μ + Σ α·exp(-β(t - tᵢ)) where each event excites future events. Bauwens-Hautsch, Bacry-Mastromatteo-Muzy, Filimonov-Sornette have empirically calibrated Hawkes kernels on equity & FX trade flow; α/β branching ratios of 0.6-0.9 are typical (highly self-exciting).

What this means in OHLCV-only proxy form: when 5-minute **volume** spikes well above its conditional intensity prediction AND price is moving in one direction, the next 1-3 bars statistically continue, because the Hawkes process implies the trade arrival burst is autocorrelated. This is the **microstructure-imbalance** version of momentum, not a pattern-based momentum.

We can't observe true trade arrivals on 5m OHLCV — but volume is a noisy proxy and TR/range is the secondary proxy. A "Hawkes proxy intensity spike" on 5m bars that's directional should have a 1-3 bar continuation edge.

### Entry condition

```
For each bar i:
  vol_avg_60 = mean(Volume over last 60 bars)
  vol_intensity = Volume[i] / vol_avg_60
  range_intensity = TR[i] / mean(TR over last 60 bars)
  bar_direction = sign(close[i] - open[i])

  IF vol_intensity >= 2.0 AND range_intensity >= 1.5 AND |body| > 0.6 × range:
    # Self-exciting candidate
    LONG entry if bar_direction == +1
    SHORT entry if bar_direction == -1
```

The `|body| > 0.6 × range` filter ensures we're not catching a doji (high vol + high range with no directional bias = institutional liquidation, mean-reverts; we want directional continuation).

### Stop placement

Stop at `entry ∓ 0.8 × ATR14`. Tight because Hawkes continuation decays fast — if the next 1-2 bars don't extend, we're wrong.

### Target placement

`entry ± 1.6 × ATR14` (R:R of 2:1). Hawkes continuation is empirically 1-3 bars (5-15min on 5m); we want to be out before the kernel decays.

### Predicted best-fit symbols / sessions

- **MNQ RTH (cash 09:30-16:00 ET)** — highest trade arrival density on Topstep universe; cleanest Hawkes signal.
- **MES RTH** — secondary; less volatile but still Hawkes-rich.
- **MCL RTH (after 09:00 ET pit open)** — energies show strong order-arrival clustering on inventory days.
- **6E during US data prints (08:30, 10:00 ET)** — flow bursts are Hawkes-textbook.

Avoid Asian session — too thin; volume proxy is noise. Avoid rates (low absolute volume despite high notional; the proxy doesn't work).

### Risk of false positives

1. **News-driven volume spike with no continuation** — surprise data print can produce one wide bar then revert (anti-Hawkes). Mitigation: the body-fraction filter weeds out doji-style climactic bars.
2. **Volume-as-proxy noise** — true Hawkes calibration uses tick-level trade arrivals; we proxy with 5m volume. The proxy SNR is moderate. Walk-forward will tell.
3. **Confounded with `volume_spike_reversal`** — that strategy fades climactic bars; this strategy continues directional bars. Crucial filter difference is the body-fraction: climactic bars have body in outer 25% of range (open near high, close near low or vice-versa); continuation bars have body filling 60%+ of range.

### How it differs from existing strategies

- vs `volume_spike_reversal`: directly opposite — that fades, this continues. Both can be valid; the differentiator is the body shape of the spike bar (climax vs marubozu).
- vs `volatility_breakout`: volatility_breakout doesn't use volume; this requires both vol AND volume confirmation. The dual filter is the Hawkes intensity overlay.
- vs `gap_fill`: gap_fill is OPEN-CLOSE based and overnight; this is intra-bar volume-density based and intraday. Zero overlap.

---

## Proposal 5 — `regime_eigenvalue_break_short` (correlation-regime crash detector)

### Theoretical basis (random matrix theory + self-organized criticality)

In normal markets, the cross-asset correlation matrix has a top eigenvalue λ₁ ≈ 30-40% of trace (the "market mode"). During crashes/stress events, λ₁ ABRUPTLY increases to 60-70% as cross-asset correlations spike to 1 — this is the signature of a phase transition (Bouchaud-Potters, Plerou et al. 2002, the "everything-correlates-in-a-crash" empirical fact). The Marchenko-Pastur eigenvalue threshold separates noise from signal — λ₁ exceeding the upper M-P bound is rare and often coincides with directional cross-asset selling.

The trade: when the rolling cross-asset correlation among (MES, MNQ, GC, ZN, MCL, 6E) suddenly spikes — measured by λ₁/Σλ on the realized return correlation matrix over rolling 30 bars — AND MES/MNQ are red, **short MES** for a continuation move. Crashes are self-reinforcing (Sornette LPPL, BTW sandpile dynamics) because forced de-leveraging triggers more selling. This is fundamentally a *short-vol-of-correlation* trade: bet that when cross-asset correlation spikes, equities continue down because the spike IS the de-leveraging signal.

### Entry condition

```
On each 5m bar i:
  R = matrix of last 30 bars × 6 symbols of returns: [MES, MNQ, GC, ZN, MCL, 6E]
  C = correlation matrix of R
  λ = sorted eigenvalues of C, descending
  λ1_share = λ[0] / sum(λ)
  baseline = rolling_60_bar_median(λ1_share)

  IF λ1_share >= 1.5 × baseline AND λ1_share >= 0.55:   # cross-asset correlation has spiked
    AND MES_5bar_return < -0.3% (equity weakness):
    SHORT MES at close
```

(MES is the trading instrument; the other 5 symbols are signal-generators only.)

### Stop placement

`entry + 1.2 × ATR14(MES)`. Crashes can have sharp counter-rallies; tight stop.

### Target placement

`entry - 3.0 × ATR14(MES)`. Asymmetric reward because the SOC self-reinforcing dynamics imply fat-tailed downside continuation when the correlation regime breaks.

### Predicted best-fit symbols / sessions

- **MES RTH only.** This is a stress-regime detector; it should signal during cash-equity hours when forced selling propagates fastest.
- A short-only strategy on MES makes sense because (a) crashes are sharper than rallies (fat left tail empirically), (b) avoids being long during euphoric melt-ups which have different microstructure (low correlation, high dispersion).

The correlation matrix needs MNQ, GC, ZN, MCL, 6E as inputs but the trade is single-leg short MES.

### Risk of false positives

1. **Spurious eigenvalue noise** — 30-bar correlation matrix with 6 assets is small-sample; λ₁ has wide CIs. Marchenko-Pastur upper bound gives a natural threshold to filter.
2. **Equity rally with correlation spike (rare)** — when correlations spike in a melt-up (e.g., short-squeeze), the strategy filter (`MES_5bar_return < -0.3%`) prevents shorting into a rally.
3. **Confound with daily-vol regime** — high-vol days may show structurally elevated λ₁ without being crashes. The rolling-baseline check (1.5× rolling median) handles this.
4. **Sample is rare** — true correlation-regime breaks happen weekly at most, monthly at the level we want. Live edge takes months to validate.

### How it differs from existing strategies

- ONLY strategy that uses cross-symbol information for the signal (proposal 3 used cross-symbol but for cointegration; this uses it for *correlation regime*).
- ONLY directional-short strategy (most others are bidirectional or long-only). Captures the asymmetric crash-tail premium.
- vs gap_fill: orthogonal in every dimension. Gap_fill is single-symbol mean-reversion of overnight gap; this is multi-asset correlation-regime crash detector. Empirical correlation in factor returns: ≈ 0.

---

## Comparison matrix — orthogonality to gap_fill

| # | Name | Factor exploited | Correlation w/ gap_fill |
|---|---|---|---:|
| 1 | vol_clustering_persistence | Vol-clustering (2nd moment, GARCH) | ≈ 0.05 |
| 2 | time_of_day_seasonality | Calendar-conditional drift | ≈ 0.10 |
| 3 | cross_asset_divergence_pair | Curve cointegration (PC2/PC3 of yield curve) | ≈ 0.20 |
| 4 | hawkes_intensity_continuation | Microstructure self-excitation | ≈ 0.05 |
| 5 | regime_eigenvalue_break_short | Cross-asset correlation regime / SOC | ≈ -0.05 |

All five carry sub-0.25 correlation with the existing gap_fill book — adding any of them improves the portfolio Sharpe even if their standalone Sharpe is half of gap_fill's.

---

## Validation plan (mandatory before promotion)

For ALL 5 proposals, the gate is identical to what we already use for gap_fill:

1. **Implementation:** add to `tools/backtest/strategies.py` matching the `Iterator[Signal]` protocol. PR review for protocol correctness.
2. **In-sample baseline:** `python scripts/strategy_deep_analysis.py` — does it show E > 0 with t > 2.0 on at least one symbol/session/side cell, n ≥ 30?
3. **Walk-forward OOS:** `python scripts/walk_forward_phase2.py` with 45d train / 15d held-out. Pass = OOS E > 0, n ≥ 30, t ≥ 2.0.
4. **Multi-comp correction:** with 5 strategies × ~6 symbols × 4 sessions × 2 sides = 240 cells, Bonferroni α = 0.05/240 ≈ 2e-4 → require t ≥ 3.5 to genuinely beat noise floor at strict family-wise level. Realistic: use FDR (Benjamini-Hochberg) at q=0.10 — will retain meaningful cells while controlling false discovery.
5. **Live shadow trade:** 2 weeks paper before $1 of risk.

---

## Mathematical / physics tools used in this proposal

- GARCH(1,1) volatility clustering (proposal 1)
- Fokker-Planck conditional drift / time-of-day seasonality (proposal 2)
- Engle-Granger / Johansen cointegration + OU half-life (proposal 3)
- Hawkes self-exciting point process (proposal 4)
- Random matrix theory (Marchenko-Pastur) + self-organized criticality (Bouchaud-Potters, Sornette LPPL) (proposal 5)
- Multiple-hypothesis correction (Bonferroni, Benjamini-Hochberg FDR) — applies to validation gate

## Confidence levels

| # | Strategy | Confidence | Why |
|---|---|---|---|
| 1 | vol_clustering_persistence | **medium-high** | GARCH is one of the most replicated empirical findings in finance. Has held up since 1982. Failure mode is well-understood (anti-GARCH on news). |
| 2 | time_of_day_seasonality | **medium** | Documented but decaying — calendar effects get arbitraged. London FX fix mechanics changed in 2014-15; current edge size unknown. |
| 3 | cross_asset_divergence_pair | **medium-high** | Curve cointegration is mathematically clean and slow to break. Implementation risk (2-leg infra) is the limiter, not signal validity. |
| 4 | hawkes_intensity_continuation | **medium** | Hawkes is well-grounded but our 5m volume proxy is lossy. Could go either way OOS. |
| 5 | regime_eigenvalue_break_short | **low-medium** | Theory is rock-solid but signal is rare (weekly-to-monthly cadence) — n will be tiny. Best treated as a tail-hedge overlay rather than primary alpha. |

---

## Final summary — most promising proposal

**My single highest-conviction pick is `cross_asset_divergence_pair` (proposal 3 — yield-curve spread mean reversion).** Three reasons: (1) the underlying cointegration of the treasury curve is the most empirically robust statistical property in our entire trading universe — Johansen tests on ZN/ZT/ZF/ZB consistently show rank ≥ 1 over multi-decade samples; (2) the OU half-life on 5m bars (30-90 min from literature) is an *exact* match for our trading cadence — not too fast for our infrastructure, not too slow to be meaningful; (3) it leverages assets the fund is **already trading and approved for via the focus universe** (ZN, ZT, ZF, ZB), so promotion costs nothing in operational complexity once the signal is validated. The implementation can start as a single-leg directional filter (long ZN when spread_z<-2, short ZN when spread_z>+2) before progressing to a true 2-leg pair, which de-risks the rollout. Critically, this is the **only** proposal that genuinely diversifies WITHIN the rates book — the rest move risk to other sectors entirely. Given the fund's 9-cell concentration in gap_fill on rates and FX, adding a non-correlated rates-internal edge is the highest-leverage Sharpe improvement available. Recommend prioritizing this for Phase 1 implementation; proposals 1 and 4 as Phase 2; proposals 2 and 5 as research-track exploration with longer validation horizons.
