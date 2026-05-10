---
type: thesis
symbol: ZB
sector: rates
conviction: high
direction: intraday (long + short cells both validated)
timeframe: intraday
strategy: gap_fill_wide
status: STANDING_LIVE
primary_driver: overnight gap mean-reversion on long-end Treasury
related: [[ZN]], [[ZT]], [[ZF]]
updated: 2026-05-09T15:00:00Z
author: Cowork (Claude)
---

# [[ZB]] — gap_fill_wide standing edge (long-end of the curve)

> Standing live edge on the 30Y Treasury Bond future. Same `gap_fill_wide` mechanic as [[ZN]] (≥1.5×ATR gap, 1.5×ATR stop, 3-tick floor), applied to the long end. **Six cells active live** — the most cells of any single Treasury, with all three sessions × both sides represented. Parent-strategy OOS E=+0.98R, t=+10.50, n=382.

## Strategy variant — gap_fill → gap_fill_wide (2026-05-08)

Same variant change as ZN: live code path is `gap_fill_wide`, OOS evidence cited below is from parent `gap_fill`. ZB has the highest tick value of the curve ($31.25), so the wide-stop variant matters most here — `gap_fill`'s 0.5×ATR stop translated to ~$25 worst-case which the broker noise-stopped easily; `gap_fill_wide`'s 1.5×ATR stop with 3-tick floor produces ~$94 minimum stops that survive normal book chop.

## Thesis

- **Mechanic (live: `gap_fill_wide`).** Identical to [[ZN]] and [[ZT]]: ≥1.5×ATR gap fires; stop = 1.5×ATR with 3-tick floor; target = prior close; rr_target=1.5. Code: `tools/backtest/strategies.py:gap_fill_wide`.
- **Why ZB on the long end.** The 30Y is more sensitive to term-premium repricing and quarterly refunding announcements than to near-term Fed policy. Overnight gaps tend to be flow-driven (foreign sovereign rebalancing, pension duration matching, basis-trade adjustments) rather than information-driven, which is exactly the regime where gap_fill works.
- **Walk-forward evidence (Tier 3, 2026-05-05).** OOS hit 59.2%, E=+0.98R, t=+10.50, n=382 — lower hit rate than [[ZT]] but the highest sample size in the universe. Source: `vault/research/backtests/2026-05-05_2207_tier3_gapfill_extensions.md`.
- **Live deployment (allowlist generated 2026-05-08T16:35:49Z).** Six ZB cells active in `state/strategy_validation.json:live_allowlist` — all three sessions × both sides:
  - `gap_fill_wide | ZB | Asian | long` — parent OOS E=+0.82R, t=+5.34, n=129
  - `gap_fill_wide | ZB | Asian | short` — parent OOS E=+1.19R, t=+8.15, n=145
  - `gap_fill_wide | ZB | London | long` — parent OOS E=+0.57R, t=+2.11, n=26
  - `gap_fill_wide | ZB | London | short` — parent OOS E=+0.94R, t=+1.80, n=31
  - `gap_fill_wide | ZB | PostClose | long` — parent OOS E=+1.04R, t=+3.41, n=28
  - `gap_fill_wide | ZB | PostClose | short` (added in 2026-05-08 promotion)
  - All session OOS evidence is from parent `gap_fill`; `gap_fill_wide` is a higher-bar (≥1.5×ATR) subset and accumulates its own live data starting 2026-05-10.
- **Per-trade economics.** Tick = $31.25 — twice ZN's tick. 5-tick stop = $156. 7-tick reward = $219. Round-trip fee ~$3. Reward/fee ~73× — clears the floor by a wide margin. **The bigger ticks mean ZB has the highest per-trade variance of the curve** — manage sizing accordingly.

## What would kill it

- **Term-premium regime shift.** When the long end starts pricing structural inflation risk (2022-style), 30Y gaps extend rather than fade. Watch for sustained widening in the 10s30s spread; if 30Y is selling off independently of 10Y, the fade is in trouble.
- **Quarterly refunding announcement weeks.** Treasury supply news creates sustained directional moves at the long end specifically. Verify the high-impact-blackout gate covers refunding announcements (it should — verify in `config/topstep.yaml` or equivalent).
- **Auction concession days.** Pre-30Y auction (typically Wednesday afternoons in cycle months), ZB tends to weaken into the auction; gap_fill in the days leading into can fail. Worth flagging via the economic calendar self-heal.
- **Same operational kills as [[ZN]]** — broker stop failures, thin-tape regime, contract roll noise.

## Correlation notes

- **Long end vs belly.** ZB and ZN are correlated but ZB has 2–2.5× the DV01. Long both is concentrated duration risk.
- **30Y-equity correlation.** Inverts in inflation-shock regimes (rate up, equities down). The fade signal is direction-agnostic, so this is informational only — but if the regime is in inflation-shock mode, the fade fails more often.
- **vs gold.** ZB and gold both rally in dovish regimes; ZB sells off in inflation-shock while gold rallies. Useful regime signal.

## Sizing

- 1 contract per fire. ZB has the largest tick value of the four; even at 1 contract a typical loss is $156, the largest in the validated universe. **The internal DLL is currently tightened to $250** (post-incident, per `vault/_meta/economics.md`) — a single ZB stop-out is 62% of the day's loss budget. That's tight. Consider scaling ZB sizing only after internal DLL is restored to $500 AND ZB cells have ≥30 live observations with positive live-vs-OOS gap.
- Stacking with other curve cells of the same direction = one trade for sizing.

## Standing status

Active. **Watch for the London cells especially** — they were added 2026-05-06 with smaller n (26, 31) than the Asian cells (129, 145). The lower-n cells need a clean live-vs-OOS read to confirm the edge holds before scaling.

## Related

- Strategy code: `tools/backtest/strategies.py:gap_fill_wide` (live), `gap_fill` (parent)
- Live allowlist: `state/strategy_validation.json:live_allowlist`
- Tier 3 walk-forward: `vault/research/backtests/2026-05-05_2207_tier3_gapfill_extensions.md`
- Recent promotions (London/PostClose adds): `vault/research/validation/promotion_log.md`
- Curve siblings: [[ZN]] · [[ZT]] · [[ZF]]
