---
type: thesis
symbol: ZN
sector: rates
conviction: high
direction: intraday (long + short cells both validated)
timeframe: intraday
strategy: gap_fill
status: STANDING_LIVE
primary_driver: overnight gap mean-reversion
related: [[ZB]], [[ZT]], [[ZF]]
updated: 2026-05-06T23:30:00Z
author: Cowork (Claude)
---

# [[ZN]] — gap_fill standing edge

> Standing live edge on the 10Y Treasury future: fade open gaps > 0.75×ATR back to prior close. Both long (gap-down fade) and short (gap-up fade) cells validated on Asian and PostClose sessions. ZN is the original walk-forward validated symbol; the rest of the curve ([[ZB]], [[ZT]], [[ZF]]) are extensions.

## Thesis

This is not a directional view. It is a documented statistical edge that the system trades both ways when the trigger fires.

- **Mechanic.** When ZN opens with `|open − prior_close| > 0.75 × ATR(14)`, fade the gap back toward prior close. Stop is set 0.5 × ATR beyond the gap-extreme; target is prior close. `rr_target = 1.5` enforces the reward-to-risk floor at signal time. Code: `tools/backtest/strategies.py:gap_fill`.
- **Why it works on Treasuries.** Overnight gaps in rates futures absent fresh policy news tend to be flow-driven (Asian sovereign hedging, basis-trade unwinds, futures-vs-cash repricing) rather than information-driven. Once US liquidity returns, the gap is treated as noise and bid/offered back into prior structure. The fade reflects this microstructure asymmetry: information-driven gaps (FOMC, NFP, CPI) extend; flow-driven gaps revert.
- **Walk-forward evidence (60d 5m bars, 45d train / 15d held-out OOS).** Train n=585 E=+0.87R t=+15.21. **OOS n=256 E=+1.10R t=+11.95 hit-rate=70%.** OOS hit > train hit (69.9% vs 65.7%) is a strong tell against curve-fit — the held-out window outperformed the training window. Source: `vault/research/backtests/2026-05-04_2139_walk_forward_validation.md`.
- **Live deployment (locked 2026-05-06 22:24 UTC).** Four ZN cells active in `state/strategy_validation.json:live_allowlist`:
  - `gap_fill | ZN | Asian | long`
  - `gap_fill | ZN | Asian | short`
  - `gap_fill | ZN | PostClose | long`
  - `gap_fill | ZN | PostClose | short`
  - Sessions in ET: Asian = 20:00–04:00, PostClose = 16:00–20:00.
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

- Strategy code: `tools/backtest/strategies.py:gap_fill`
- Live allowlist: `state/strategy_validation.json:live_allowlist`
- Walk-forward source: `vault/research/backtests/2026-05-04_2139_walk_forward_validation.md`
- Curve siblings: [[ZB]] · [[ZT]] · [[ZF]]
- Product reference: [[futures/product_deep_dives/ZN]]
