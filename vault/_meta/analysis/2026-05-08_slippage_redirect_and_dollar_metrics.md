---
type: analysis
date: 2026-05-08
author: Cowork (Claude)
applies_to: [CIO, Risk Manager, Quant Researcher]
sources:
  - vault/research/param_sweeps/gap_fill_2026-05-08_2304.md
  - vault/research/slippage_mitigation_playbook.md
  - vault/_meta/cowork_coordination.md (CC's 2026-05-08 redirect)
  - vault/research/historical_slippage_topstep.md (added 2026-05-09 update)
confidence: PATTERN
status: open
amended: 2026-05-09
---

> ## ⚠ AMENDMENT 2026-05-09 — empirical slippage is materially better
>
> This piece used 0.25 ticks/side as the "typical / conservative live
> slippage" assumption. After reading
> `vault/research/historical_slippage_topstep.md` (n=31 v1 fills mined
> from `state/fund.db:orders`), the empirical floor is closer to
> **0.10–0.15 ticks/side** on liquid futures. Entries on
> marketable-limit fill *favorable* (mean -10.4 ticks vs intent — better
> than asked); stop fills are +1-2 ticks adverse; targets fill at limit
> price. So:
>
> - The structural Pattern C finding (R-multiples are slippage-blind;
>   the dollar-metric extension to `param_sweep.py` was the right
>   redirect) is **unchanged**.
> - The deployment-relevant column is closer to
>   `mean_net_usd_at_slip_0.10` (between the script's 0.0 and 0.25
>   levels), not the 0.25 column I emphasised.
> - Combine pass probability per the historical-slippage doc is
>   93–98%, not the more conservative number derived from 0.25
>   per-side modelling.
> - The "park" decision on the +2.80R / +2.10R / +1.91R
>   parked-sweep variants was correct (slippage-blind), but the
>   dollar-metric re-sweep (queued 2026-05-09) may show those
>   wide-stop variants comfortably surviving 0.10–0.15 ticks/side
>   slippage. The verdict isn't "they don't work in production" — it's
>   "the original sweep didn't measure the deployment-relevant thing,
>   and a properly-instrumented re-sweep is pending."
>
> Treasuries (ZN/ZB/ZT/ZF) have zero historical fills in the v1 sample —
> Sunday 2026-05-10 onward will be the first measurement. If live
> treasury slippage materially exceeds 0.25 ticks/side on Sunday's fills,
> revisit Pattern C as a live finding rather than backtest theory.

# R-multiples are slippage-blind — the param-change recommendation is parked

## Why this exists

This afternoon's `gap_fill` parameter sweep (commit landed in
`vault/research/param_sweeps/gap_fill_2026-05-08_2304.{csv,md}`)
produced striking R-multiple results:

| Symbol | Best params (by R) | OOS_E (R) | OOS_t |
|---|---|---:|---:|
| ZT | `min_gap_atr=1.5, rr_target=1.0` | +2.80R | +7.79 |
| ZB | `min_gap_atr=1.5, rr_target=1.0` | +2.10R | +7.60 |
| ZF | `min_gap_atr=1.5, rr_target=1.0` | +1.91R | +4.73 |
| ZN | `min_gap_atr=0.5, rr_target=2.0` | +1.25R | +8.36 |

Cowork initially recommended shipping these param changes — they
roughly double per-trade R on ZT/ZB/ZF.

**Claude Code redirected.** The redirect was correct, and this piece
documents why so future analyses don't repeat the mistake.

## The flaw in R-multiple-only ranking

R-multiples are computed as `(exit_price − entry_price) / |entry_price
− stop_price|`. They normalize for stop distance — a +2R trade with a
1-tick stop (entry to stop = 1 tick) and a +2R trade with a 100-tick
stop both score +2R.

**But slippage is denominated in TICKS, not in R.** A 0.25-tick adverse
slippage at entry + 0.25-tick adverse exit = 0.5 ticks of round-trip
slippage cost. For a 1-tick-stop trade, 0.5 ticks is 50% of the stop
distance — so the +2R trade becomes effectively +1.5R, and the −1R loss
becomes −1.5R. For a 100-tick-stop trade, 0.5 ticks is 0.5% of the stop
distance — slippage is noise.

R-multiple ranking treats both trades identically. **Dollar-metric
ranking exposes the difference.** This is why the "best" cells by R
might be the worst cells once realistic slippage hits — they have the
tightest stops, and tight stops are where slippage compounds fastest.

## Concrete worry on the 2026-05-08 sweep results

The `min_gap_atr=1.5` param means "only fire when the gap is at least
1.5 × ATR" — fewer signals, larger gap moves, but the stop is set at
±0.5×ATR from entry (per `gap_fill` mechanic). **Stop distance for the
filtered cells could be sub-tick to a few ticks**, depending on ATR
that bar. The +2.80R OOS on ZT could be flattering: if the typical stop
is 1 tick, 0.25 ticks of slippage per side eats 50% of the per-trade R
on every trade. Net dollar P&L would be much less impressive than the
R-multiple suggests.

Until we measure the average stop distance in ticks per cell, we don't
know whether the +2.80R is real per-dollar edge or a tight-stop
artifact.

## What the dollar-metric extension fixes

Cowork extended `scripts/param_sweep.py` to compute, per cell:

- `mean_gross_usd` — average per-trade $ result with no slippage
- `mean_risk_ticks` — average stop distance in ticks (the diagnostic)
- `mean_net_usd_at_slip_<X>` — average per-trade $ net after X
  ticks/side of round-trip slippage, for X ∈ {0, 0.25, 0.5, 1.0}
- `breakeven_slip_ticks` — the slippage level at which mean net $ = 0

The MD summary now ranks "best variant per symbol" by **net $ at
slip=0.25**, not by R. The full grid table shows $-net at all four
slippage levels plus breakeven_slip.

A cell with high R but low `$@slip=0.25` is exposed. A cell with
moderate R but high `breakeven_slip_ticks` is robust.

## The specific decision parked

**Don't change `STRATEGY_ROSTER`'s gap_fill kwargs** based on the
2026-05-08 R-only sweep. The right sequence:

1. Re-run the same sweep with the dollar-metric extension after CC's
   auto-commit picks up the param_sweep.py change. Output will land in
   `vault/research/param_sweeps/gap_fill_<ts>.md` with the new columns.
2. Read the `$@slip=0.25` and `breakeven_slip_ticks` columns. Pick
   the cell that maximizes $@slip=0.25, not E.
3. Validate the chosen cell's `mean_risk_ticks` is wide enough that
   1 tick of slippage is < 30% of stop distance.
4. **Then** consider promoting params.

`gap_fill_wide` (CC's 2026-05-08 baseline) is the slippage-resistant
default. Don't disturb it before Sunday's measurement.

## How this becomes learning

This piece encodes a NEW Pattern C for the
`vault/_meta/analysis/2026-05-07_lesson_meta_patterns.md` library:

> **Pattern C — Metric blindness to deployment cost.**
>
> A strategy metric calibrated for ranking purposes can hide the
> deployment cost. R-multiples normalize for stop distance, but
> slippage is in ticks, so R-rank can mislead when stops vary widely
> between candidates.
>
> Before merging any parameter change based on a backtest metric, ask:
> 1. *What real-world cost does this metric not capture?* (slippage,
>    fees, missed fills, spread, regime drift)
> 2. *Could two cells have identical metric values but very different
>    deployment costs?* (yes for R-mult vs $-net when stops vary)
> 3. *What's the most common deployment regime, and what does the
>    metric look like at that regime?* (slippage at 0.25 ticks/side
>    is the typical Topstep gap_fill_wide regime)

This is structurally similar to Pattern B (wrong-context validation)
but more subtle — Pattern B is about applying the metric in the wrong
regime; Pattern C is about the metric itself failing to model
deployment costs even in the same regime.

If a third occurrence of this kind of metric blindness appears,
escalate to PATTERN tier in the meta-patterns file.

## See also

- [[2026-05-07_lesson_meta_patterns]] — Pattern A (fail-silent),
  Pattern B (wrong-context), now Pattern C (metric blindness).
- [[../../research/slippage_mitigation_playbook]] — full slippage
  reduction lever inventory.
- [[../../research/param_sweeps/gap_fill_2026-05-08_2304]] — the
  R-only sweep this piece responds to.
- [[2026-05-07_treasury_cell_decay_read]] — sister analysis on
  pre-Sunday deployment status.
