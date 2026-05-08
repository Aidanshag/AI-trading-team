---
name: Standing authorization to progress through refinement queue
description: User authorized 2026-05-06 to keep pulling work off the trading-system refinement queue when conditions are right, without asking each time
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User explicitly granted standing authorization on 2026-05-06 to continue
pulling refinements off this queue and shipping them when conditions are
right, without asking permission each time.

**Why:** The user wants the trading system to keep getting better between
sessions. Each session, when invoked, I should check the queue and the
prerequisite conditions, and ship the next refinement if appropriate.

**How to apply (queue + conditions):**

Already shipped 2026-05-06:
- ✅ #1 Fix `gap_fill` stop-too-tight rejection on rates (PER_STRATEGY_MIN_STOP_TICKS_OVERRIDE)
- ✅ #2 Tighten rates sector + rates_curve basket caps from 2/3 → 1 contract
- ✅ Calibration audit: fee_budget $15→$25, internal_dll $250→$500, max_concurrent 2→1, consec_loser_pause 60→30 min
- ✅ #10 Wake Quant Researcher (mid-week, user authorized pre-Sunday wake)

## EXPANSION 2026-05-06: standing authorization for automatic strategy promotion

User authorized 2026-05-06 (after the initial queue auth) to:
- **Automatically implement validated new strategies** without asking. If
  walk-forward shows OOS t≥1.5, n≥30, E>0, just ship it. Add wrapper to
  `tools/backtest/strategies.py` if parametrized variant; add to
  STRATEGY_ROSTER + ALL_STRATEGIES; let daily validation seed the
  cell history; promote per the rolling-window rules.
- **Backtest and simulate** before implementation. Run walk-forward,
  check OOS stats, only ship cells that genuinely pass.
- **Use judgment on risk.** Be smart about correlation, regime exposure,
  per-trade economics. If multiple cells share the same mechanism,
  understand the concentration risk before promoting all of them.
- **High confidence = ship.** "Extremely high confidence" means
  walk-forward t-stat well above threshold (≥3.0), large sample
  (n≥100), expectancy clearly positive (E≥+0.5R), and theoretical
  basis that's not just data mining. When all four are true, ship.

This authorization applies to:
- Adding new strategy variants (parametrized like `order_block_d1`)
- Adding new strategy implementations from Quant Researcher proposals
- Promoting cells that newly pass walk-forward
- NOT position sizing (still requires explicit approval)
- NOT modifying HIGH_RISK_FILES

## EXPANSION 2026-05-06 (third grant): authorization to selectively widen `live_strategies_filter`

User authorized 2026-05-06 (later session) to widen the live filter on
my own when conditions warrant. The user wants concentration discipline
preserved BUT trusts judgment about when to layer in additional
validated strategies.

**Trigger criteria for widening (conservative, sequential):**

| Stage | Action | Trigger condition |
|---|---|---|
| 1 | Add `cross_asset_divergence_zn` × ZN to filter | After ≥15 live trades on gap_fill treasury with live E ≥ +0.5R measured. ZN-only, orthogonal factor (yield curve cointegration), minimal additional risk. |
| 2 | Add `liquidity_sweep_tuned` × MES RTH long | After Stage 1 + ≥10 more trades with live E maintained. Adds RTH session diversification. |
| 3 | Add `liquidity_sweep_tuned` × MNQ RTH long | After Stage 2 + ≥5 more clean trades. Tighten `correlated_baskets.risk_on_index` cap to 1 simultaneously. |
| 4 | Add `fair_value_gap_tuned` cells (top 2 by t-stat) | After Stage 3 + 30-trade history of stable cumulative R. |
| 5 | Add `order_block_d1` cells | Last — smallest sample sizes, weakest priors. |

**Demotion triggers (run on any newly-added cell):**
- Any cell with -R-multiple over its first 5 live trades → demote immediately back to shadow
- Cumulative live E across all newly-added cells drops below 0R over 10 trades → revert that cell to shadow
- If overall daily NET P&L drops below break-even pace for 5 consecutive trading days after a widen → revert the most-recent widen

**Bounds preserved:**
- One stage at a time, never multiple at once
- Always document the rationale in the state file's filter rationale field
- `gap_fill × ZN/ZT/ZB/ZF` is the permanent foundation — never remove from filter
- If any safety floor (DLL, TDD, internal DLL, defensive ladder) is approached on a widen-day, halt and re-tighten

When you widen, save the rationale in `state/strategy_validation.json` →
`live_strategies_filter[].rationale` and the next session will see it.

Pending (run when prerequisite conditions met):

| # | Refinement | Trigger condition |
|---|---|---|
| 3 | Wire shadow-resolved trade outcomes into rolling per-cell validation | After ~20+ resolved shadow trades exist (`SELECT count(*) FROM shadow_trades WHERE outcome IS NOT NULL`) |
| 4 | Volatility regime filter — skip entries when realized vol is bottom-quartile | After 1+ losing day with low-vol regime evident, OR if `gap_fill` cells start showing decay |
| 5 | Post-trade execution audit — log expected vs actual fill prices for slippage analysis | Anytime; useful before #6 |
| 6 | EV-gate using realistic execution (subtract fees + measured slippage) | After #5 has 30+ data points to estimate slippage cost |
| 7 | Rolling N-trade EV demotion — demote a cell if 20-trade EV < 0R | After auto_trader has fired at least 50 live trades on validated cells |
| 8 | Per-cell position sizing by t-stat (high-conviction cells get 2 contracts) | NEEDS USER CONFIRMATION before shipping — alters risk per trade |
| 9 | Multi-timeframe confirmation (5m signal + 1h trend filter) | After #4-7 are stable; this is research-heavy |
| 10 | Wake Quant Researcher agent for novel strategy proposals | Sunday — weekly cadence per existing agent_autonomy memory |

**Bounds on this authorization:**
- Do NOT ship #8 (position sizing) without explicit approval — it changes risk per trade
- Do NOT push to git remote without explicit approval (auto-commit hook handles that, but for manual one-off pushes ask first)
- Do NOT widen the live allowlist beyond what daily validation produces — user filter `live_strategies_filter` is the authoritative concentration rule
- Do NOT modify HIGH_RISK_FILES (per CLAUDE.md) without explicit user approval

When you ship a queue item, save a brief note in the project memory or
update this file's checklist so the next session sees what's done.
