---
type: thesis
symbol: ZN
sector: rates
conviction: DEMOTED
direction: n/a (strategy removed from live)
timeframe: n/a
strategy: gap_fill_wide
status: DEMOTED_2026-05-11
primary_driver: (historical) overnight gap mean-reversion
related: [[ZB]], [[ZT]], [[ZF]]
updated: 2026-05-11T22:00:00Z
demoted_by: vault/research/analysis/2026-05-11_gap_fill_wide_validation_attempt.md
author: Cowork (Claude)
---

> ## ⛔ DEMOTED 2026-05-11
>
> `gap_fill` and `gap_fill_wide` have been **removed from the live filter**
> as of 2026-05-11 evening. CC's autonomous validation found the original
> Tier-3 t-stats of +7.95 to +11.76 cited throughout this thesis were
> artifacts of three compounding bugs in the validation pipeline:
> missing `tick_size` injection, a `t.stop_price` typo, and a
> silent division-by-`1e-9` in the rr-check when stops collapsed to
> sub-tick on low-vol 5m treasury bars.
>
> Under the **corrected** pipeline, neither `gap_fill` nor
> `gap_fill_wide` produces a deployable parameter set on 60 days of
> treasury data across 144 combinations tested.
>
> The Sunday-night 2026-05-10/11 live run also revealed an orphan-leg
> regression in `place_bracket()` (Pattern A — protective legs placed
> before entry-fill confirmation) that netted -$137.89 on ZB.
>
> **Sources:**
> - `vault/research/analysis/2026-05-11_gap_fill_wide_validation_attempt.md`
> - `vault/research/analysis/2026-05-11_broker_target_fill_anomaly.md`
> - `vault/lessons/2026-05-11_gap_fill_calibration_and_orphan_leg_incident.md`
>
> The live allowlist is now a 23-cell diversified mix (FVG family,
> narrow_range_break, vol_spike_fade, inside_bar_break, order_block_d1,
> pivot_reversal, cross_asset_divergence_zn, liquidity_sweep_tuned,
> keltner_breakout, rsi2_extreme_reversion). See CLAUDE.md "Strategic
> focus — diversified mix" for the current state.
>
> The content below is **preserved for historical reference**. Do not
> use as a current trade thesis. If the backtest engine `Trade.stop_price`
> issue gets fixed and a re-validated gap_fill family emerges, this
> thesis should be rewritten from scratch, not resurrected.

# [[ZN]] — gap_fill_wide standing edge ⛔ DEMOTED

> Standing live edge on the 10Y Treasury future: fade open gaps ≥ 1.5×ATR back to prior close, with stops at 1.5×ATR (≥3 ticks hard floor) for live tradability. Both long (gap-down fade) and short (gap-up fade) cells validated on Asian and PostClose sessions. ZN is the original walk-forward validated symbol; the rest of the curve ([[ZB]], [[ZT]], [[ZF]]) are extensions.

## Strategy variant — gap_fill → gap_fill_wide (2026-05-08)

The deployed code path is `gap_fill_wide`, a slippage-tolerant variant of the original `gap_fill`. Three parameter changes:

| Parameter | gap_fill | gap_fill_wide | Why |
|---|---|---|---|
| `min_gap_atr` | 0.75 | **1.5** | Only larger gaps fire; reduces low-conviction signals |
| Stop distance | 0.5 × ATR | **1.5 × ATR** | Wider buffer; survives intra-bar noise |
| `min_stop_ticks` | (none) | **3** | Hard floor — sub-tick stops were getting noise-stopped live |

Why the variant exists: ATR on 5m treasury bars is typically 1–3 ticks. The original `gap_fill` `0.5×ATR` stop produced sub-tick stops that the backtest accepted (idealized fills) but that live execution noise-stopped before the trade had time to work. `gap_fill_wide` is the live-tradable expression of the same edge.

The OOS evidence cited in this thesis is from the parent `gap_fill` walk-forward validation. The wide variant inherits the family edge but trades less frequently (signals require ≥1.5×ATR gaps). Live observations on `gap_fill_wide` specifically begin Sunday 2026-05-10.

## Thesis

This is not a directional view. It is a documented statistical edge that the system trades both ways when the trigger fires.

- **Mechanic (live: `gap_fill_wide`).** When ZN opens with `|open − prior_close| ≥ 1.5 × ATR(14)`, fade the gap back toward prior close. Stop = entry ± 1.5 × ATR (with `min_stop_ticks=3` hard floor); target is prior close. `rr_target = 1.5` enforces the reward-to-risk floor at signal time. Code: `tools/backtest/strategies.py:gap_fill_wide` (lines 1251+). Parent strategy: `tools/backtest/strategies.py:gap_fill`.
- **Why it works on Treasuries.** Overnight gaps in rates futures absent fresh policy news tend to be flow-driven (Asian sovereign hedging, basis-trade unwinds, futures-vs-cash repricing) rather than information-driven. Once US liquidity returns, the gap is treated as noise and bid/offered back into prior structure. The fade reflects this microstructure asymmetry: information-driven gaps (FOMC, NFP, CPI) extend; flow-driven gaps revert.
- **Walk-forward evidence (60d 5m bars, 45d train / 15d held-out OOS).** Train n=585 E=+0.87R t=+15.21. **OOS n=256 E=+1.10R t=+11.95 hit-rate=70%.** OOS hit > train hit (69.9% vs 65.7%) is a strong tell against curve-fit — the held-out window outperformed the training window. Source: `vault/research/backtests/2026-05-04_2139_walk_forward_validation.md`.
- **Live deployment (allowlist generated 2026-05-08T16:35:49Z).** Four ZN cells active in `state/strategy_validation.json:live_allowlist`:
  - `gap_fill_wide | ZN | Asian | long`
  - `gap_fill_wide | ZN | Asian | short`
  - `gap_fill_wide | ZN | PostClose | long`
  - `gap_fill_wide | ZN | PostClose | short`
  - Sessions in ET: Asian = 20:00–04:00, PostClose = 16:00–20:00. ZN is one of 6 symbols in the 26-cell `gap_fill_wide` deployment (treasuries + NG + 6E).
- **Per-trade economics (validated cells).** Tick = $15.625. Typical 5–8 tick stop = $80–$125 — well inside the $250 per-trade cap. Round-trip fee is in the $3 range for full-size rates contracts. Reward-to-fee at default `rr_target=1.5` clears the 3× fee floor.

## What would kill it

- **Sustained regime shift to information-driven gaps.** A multi-week stretch where overnight gaps consistently extend rather than fade — typically a Fed-pivot week, a war/crisis tape, or a Treasury-supply shock. The first sign is OOS expectancy decay in `vault/research/live_vs_oos/`. Demote at first observation; do not wait for the daily validator's 3-consecutive-fail trigger if the regime read is clear.
- **Front-month roll noise.** In the last 2 weeks of contract life, CTD (cheapest-to-deliver) basis effects can produce non-mean-reverting gap behavior. Watch for spurious signals on roll days.
- **Liquidity regime change in Asian session.** The thin-tape regime gate (21:00–04:00 ET) is currently disabled per recent edits — verify before each session. If Asian tape thins (BoJ holiday, illiquid weekly opens), gaps become single-actor moves and the fade fails.
- **Stop-rejection on the broker side.** The 5/5 NG `inside_bar_break` incident showed bracket stops can fail to register server-side. The `LOSS_TIER_HARD_CAP_USD = $200` software belt in `auto_trader.py` is the backstop, but if it ever fires for a ZN gap_fill trade, that's a signal to halt the strategy until root-caused.

## Correlation notes

- **ZN, ZB, ZT, ZF are one trade in aggregate.** A long signal on all four simultaneously is a single duration bet; size accordingly. The risk hook's `_check_sector_and_basket_limits` enforces this via `risk_limits.yaml:correlated_baskets.duration_basket` — verify the cap is set to a sensible aggregate.
- **Cross-strategy stacking.** No other strategies are currently live, so there's no near-term concern about stacking gap_fill on top of e.g. a manual rates view. If the universe expands, watch ZN gap_fill long stacking on top of any 2s10s curve trade — they share direction.
- **Headline risk window.** Pre-FOMC, pre-CPI, pre-NFP — the high-impact blackout gate (`_check_high_impact_blackout`) blocks ±5min around the print, but the directional regime shift can persist for hours. Consider a wider blackout window for gap_fill specifically on these days.

## Sizing

- 1 contract per fire, default. The $250 per-trade cap is well-clear of the typical $80–$125 worst-case loss; sizing up to 2 contracts is mathematically possible but breaks the consistency-rule headroom math (one trade ≤ 25% of internal DLL ceiling, internal DLL is currently tightened to $250 → per-trade cap is ~$60 worst-case at 2 contracts, which fails). Stay at 1 contract until internal DLL is restored to $500 (per `vault/_meta/economics.md` post-incident comment).
- Daily cap per the existing gates: `max_trades_per_day=8` autonomous, but realistic firing on ZN alone is 0–2 setups/day. Stacking with [[ZB]], [[ZT]], [[ZF]] of the same direction is one trade for sizing purposes (see Correlation notes).

## Standing status

This thesis is the active live view. Re-validation cadence: walk-forward re-runs nightly via `scripts/daily_strategy_validation.py`. Demotion happens automatically on 3 consecutive OOS-decay observations (see `vault/research/validation/promotion_log.md` for the demotion rule). Live performance tracked in `vault/research/live_vs_oos/` — review the per-cell `mean_live_R vs OOS_E` gap weekly.

If a ZN cell gets flagged as ⚠ UNDERPERFORM in the live-vs-OOS tracker, this thesis should be revisited and the cell potentially shadowed pending review.

## Related

- Strategy code: `tools/backtest/strategies.py:gap_fill_wide` (live), `gap_fill` (parent)
- Live allowlist: `state/strategy_validation.json:live_allowlist`
- Walk-forward source: `vault/research/backtests/2026-05-04_2139_walk_forward_validation.md`
- Curve siblings: [[ZB]] · [[ZT]] · [[ZF]]
- Product reference: [[futures/product_deep_dives/ZN]]
