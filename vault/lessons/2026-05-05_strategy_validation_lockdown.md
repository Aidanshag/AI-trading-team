---
date: 2026-05-05
kind: process_lesson
confidence: RULE
applies_to_system: strategy_gating
sample_size: 1
result: 7 strategies → default-deny; 24 → 33 validated cells; 7 new gap_fill symbols
reason: Live trader fired 4 unvalidated trades today; user directive — only validated strategies trade
---

# Strategy validation lockdown (Tier 1/2/3 walk-forward + default-deny)

## What happened

After today's overnight bleed (lesson `2026-05-05_profit_lock_disabled_overnight.md`),
the trader was firing strategies live without confirmed walk-forward edge.
4 of the 5 fills today were `narrow_range_break` and `inside_bar_break` —
strategies that pass the Phase 2 *cell-level* validation but were firing
on cells outside the validated subsets, because the live gate was symbol-
level only and **default-allow** (strategies not in the list were free
to fire on any focus symbol).

User directive: "only allow trades that are validated for now."

## What we did

**Tier 1** — fresh walk-forward on `narrow_range_break` and `inside_bar_break`
at the *aggregate* (per-symbol, all-sessions, both-sides) level. Result:
**zero strategy/symbol combos pass at aggregate.** ZN narrow_range_break
was the worst at OOS E=−0.48R t=−7.47 — near-statistically-significant
*negative* edge. Confirms the per-cell view: edge exists in narrow
session/side windows, NOT in the aggregate.

**Tier 2** — per-cell sweep on `fair_value_gap`, `order_block`,
`liquidity_sweep` at default params. **10 validated cells found**
(5 already in allowlist, 5 new): liquidity_sweep × MNQ London long,
6E Asian short; fair_value_gap × NG RTH short, MNQ Asian long,
6E Asian short, GC RTH short. `order_block` had **zero** validated cells
at default params — needs parameter tuning before promotion.

**Tier 3** — extend gap_fill to neighboring symbols and timeframes.
**7 new validated symbols at 5m**:
- Treasury curve: ZB, ZF, ZT (OOS E up to +1.41R, t up to +11.76, n=333)
- FX cousins: 6B, 6J, 6A, 6C (OOS E up to +2.34R)

15m and 30m timeframes failed only because n_oos < 20 in the 60-day
window — needs longer history to confirm. Worth re-running with 180d
once we have it.

**Lockdown changes** (in `scripts/auto_trader.py`):

1. `STRATEGY_SYMBOL_ALLOWLIST` now covers all Phase 2 + Tier 2 + Tier 3
   validated strategies. Strategies not in this list are blocked from
   placing orders.
2. `STRATEGY_CELL_ALLOWLIST` expanded from 7 cells to 24 cells (all
   Phase 2 winners + Tier 2 additions).
3. **Default-deny gate**: strategies/symbols not in the allowlist
   can still scan and produce signals, but those signals are recorded
   as **shadow trades** (no live order). This lets unvalidated cells
   continue accumulating data toward future validation without spending
   real capital.

## What we should DO based on this

### How unvalidated strategies continue earning their place

The shadow-trade pipeline is the path. Every triggered signal on a
non-validated (strategy, symbol, cell) gets logged in `shadow_trades`
with reason `symbol_not_validated` or `cell_not_validated`. Daily
batch resolution (existing `state.db.resolve_shadow_trade`) measures
each shadow's R-multiple by simulating the bracket against subsequent
bars. After ~30 resolved samples per cell:

- Re-run the per-cell walk-forward including the shadow trades as fresh
  OOS data
- If a cell now passes (OOS t≥1.5, n≥30, E>0), promote it to the live
  allowlist
- If it doesn't pass, keep shadow-logging — eventually retire if
  E stays clearly negative over n>=100

### What the new validated cells unlock

The 24-cell allowlist gives the trader many more "shots on goal" while
keeping the validated-only constraint. Even if the validated cells'
edge is small, they're statistically real and aggregate over many
shots. Per-day expectancy estimate: 2-4 validated triggers, ~+0.5R
average → +$50-100/day above break-even.

The **7 new gap_fill symbols** (ZB/ZF/ZT/6B/6J/6A/6C) are the highest-
value finding. They're not yet in `config/focus_universe.yaml` so
they won't live-trade until the user expands focus. Recommend the
user add ZB/ZF/ZT first (treasury curve = ZN's siblings, well-understood)
and 6J/6A second (FX edge with strong OOS).

## What does NOT carry over

- **Don't trust aggregate-level walk-forward as the only measure.**
  Today's Tier 1 confirmed: aggregate fails while specific cells pass.
  Always validate at (symbol × session × side) granularity.

- **Don't extrapolate small-n cells**. Several Tier 3 results had
  OOS n<20 and very large E (e.g., 6E 5m: OOS E=+2.26R but n=19).
  These are tantalizing but the standard error is too wide to bet
  real money. Wait for more data.

- **Don't assume Tier 3 cousins behave identically to ZN/NG/6E.**
  The walk-forward shows aggregate edge, but session/side decomposition
  on the cousins hasn't been done. Phase 2 should be re-run on these
  symbols specifically.

## Open questions

1. **Why do many Tier 2 cells have weak train but strong OOS?** This
   is statistically suspicious — usually train > OOS on small samples
   due to overfitting. The reverse (OOS > train) on multiple cells
   suggests either (a) recent regime favors these patterns, (b) the
   train set has a structural break, or (c) the small OOS samples
   are flukes. Worth running on a 90d or 180d window to disambiguate.

2. **`order_block` has zero validated cells at default params.** The
   strategy may still have edge with tuned parameters (rejection-bar
   strength, response-time bars, mitigation-zone size). Worth a Tier 4
   parameter sweep specifically on `order_block`.

3. **15m/30m gap_fill timeframes underperform purely because of small n.**
   At 60d we get 5-15 trades on most symbols at 15m. Need ≥120d data
   to evaluate properly. The PER-TRADE edge may be larger on 15m
   (signs from train: NG 15m E=+0.97R, 6E 15m E=+1.84R) — bigger trades
   with the same hit rate would mean the edge is real, just rare.
