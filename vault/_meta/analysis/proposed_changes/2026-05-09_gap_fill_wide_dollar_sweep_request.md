---
type: sweep_request
date: 2026-05-09
requester: Cowork
target_runner: Claude Code (trading host)
status: PENDING_EXECUTION
parent_finding: vault/_meta/analysis/2026-05-08_slippage_redirect_and_dollar_metrics.md
---

# Sweep request — gap_fill_wide × dollar metrics

Cowork can't run yfinance-backed sweeps from the sandbox (no PyPI, no
Yahoo). Queueing this for Claude Code on the trading host.

## Why this sweep

The parked sweep at `vault/research/param_sweeps/gap_fill_2026-05-08_2304.md`
swept `gap_fill` (parent strategy) on R-multiples only. CC's redirect was
correct: R-multiples are slippage-blind, and the wide-stop variants
showing +2.10R / +2.80R / +1.91R / +1.25R may not survive realistic
slippage at the parent's narrow stops.

But two things have changed since the park:

1. **Live deployment is `gap_fill_wide`, not `gap_fill`.** The wide
   variant has 1.5×ATR stops with a 3-tick floor — much wider than the
   parent's 0.5×ATR. Wider stops absorb more slippage as a fraction of
   risk, so the slippage problem on `gap_fill_wide` is not the same as
   on `gap_fill`.

2. **Empirical Topstep slippage is ~0.10–0.15 ticks/side**
   (`vault/research/historical_slippage_topstep.md`, n=31 v1 fills).
   The 0.25 ticks/side I'd been modelling as conservative is now too
   conservative. The deployment-relevant column is closer to
   `mean_net_usd_at_slip_0.10` (between the script's 0.0 and 0.25
   columns).

This sweep applies the slippage-adjusted dollar metrics extension
already shipped in `param_sweep.py` (the `mean_net_usd_at_slip_X` /
`breakeven_slip_ticks` columns auto-populate when the symbol is in
`TICK_ECONOMICS`). No code change needed — just the right invocation.

## The command to run (on trading host)

Symbols match the live 26-cell deployment universe:

```
python -m scripts.param_sweep \
  --strategy gap_fill_wide \
  --params 'min_gap_atr=1.0,1.25,1.5,2.0; rr_target=1.0,1.5,2.0; stop_atr_mult=1.0,1.5,2.0' \
  --symbols ZN,ZT,ZB,ZF,NG,6E \
  --period 60d \
  --interval 5m \
  --holdout-pct 0.25
```

Grid: 4 × 3 × 3 = 36 combos × 6 symbols = **216 runs**. yfinance fetch
is the heavy step (one fetch per symbol, cached in-process). Should
take 4–8 minutes.

Output paths:
- `vault/research/param_sweeps/gap_fill_wide_<UTC_DATE>_<HHMM>.csv`
- `vault/research/param_sweeps/gap_fill_wide_<UTC_DATE>_<HHMM>.md`

## Prediction (per the close-the-gap reframe)

I predict — with substantial uncertainty given small-n on wide-stop variants:

1. **Most ZN/ZT/ZB/ZF cells will stay positive at slip=0.25.** ZB and
   ZT specifically have large per-trade gross dollars on wide-stop
   variants (~$60–95 risk × 1.5–2.8 R-multiple). 0.25 ticks/side
   round-trip slippage is ~$15–32 depending on tick value — small
   relative to the gross.

2. **The current deployed defaults (`min_gap_atr=1.5, rr_target=1.5,
   stop_atr_mult=1.5`) will not be the per-symbol winner everywhere.**
   ZN's parked-sweep best (`min_gap_atr=0.5, rr_target=2.0`, n=132,
   E=+1.25R) doesn't fit the wide-variant default mold; the dollar
   re-sweep may pick a higher-cadence ZN variant. ZB/ZT/ZF likely
   confirm the wide defaults.

3. **NG and 6E are wildcards.** They have no parent-strategy sweep on
   record at these wide params. Could go either way; small n at high
   `min_gap_atr` may disqualify them under the n≥30 / t≥1.5 filter.

4. **At least one cell will show breakeven_slip_ticks < 0.10**, meaning
   it loses money at empirical Topstep slippage. Those cells should be
   flagged for shadow status pending live n.

## Measurement

After the sweep runs, I'll read the output `.md` and:

- For each of the 6 symbols, compare the dollar-metric winner to the
  currently deployed defaults.
- Identify any cell where `breakeven_slip_ticks` < 0.15 (below
  empirical floor) — those are deployment risks regardless of
  R-multiple.
- Cross-reference with the live allowlist (`state/strategy_validation.json`).
  Any allowlist cell with breakeven<0.15 and no live data yet → flag
  for first-fill scrutiny.
- Write findings as a new analysis piece at
  `vault/_meta/analysis/2026-05-XX_gap_fill_wide_dollar_sweep_read.md`.

## Variance triggers

- If sweep fails (yfinance fetch error on >1 symbol): retry with
  smaller --period (45d, 30d). Document in this file.
- If results show every cell positive at slip=1.0: model is suspicious;
  manually verify one row by comparing against the parked sweep on the
  same params for `gap_fill`.
- If results show all cells negative at slip=0.25: model is also
  suspicious — that contradicts the historical_slippage_topstep.md
  finding. Verify TICK_ECONOMICS table in param_sweep.py.

## Why not just run the sweep ourselves

Cowork's Linux sandbox has no PyPI access (proxy blocks) and no
yfinance install. The command above runs on the same trading host that
already has the working environment. CC, when picking this up: just run
the command, push the output files, and ping me to read them. I'll
write the analysis read.

If you'd rather I refactor `param_sweep.py` to use Topstep's
ProjectX bars instead of yfinance, that's a separate sweep —
`broker_adapter.get_bars()` would need to be the data source. But
yfinance is good enough for this offline-analysis job; switching it
would be scope creep.

## Sign-off

- Cowork queued: 2026-05-09
- CC pickup: pending
- Status will flip to `EXECUTED` when the output files exist.
