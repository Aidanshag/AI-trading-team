---
date: 2026-05-08
kind: process_lesson
confidence: RULE
applies_to_system: trader_architecture
sample_size: 1 (the simplification event)
result: 2929 lines → 480 lines (84% reduction in execution layer)
reason: 4 days of accumulated complexity bugs; sub-tick gap_fill stops being silently rejected
---

# Layer 1 simplification — separating the brain from the knife

## What happened

Between 2026-05-04 and 2026-05-08, the `auto_trader.py` accumulated bugs faster
than they could be fixed:
- 2026-05-04: profit-lock disabled silently, $1,190 → $354 giveback
- 2026-05-05: NG bracket stop didn't fire, 7-hour ride lost $702
- 2026-05-06: 5 trades all closed near break-even (target-tag mismatch)
- 2026-05-07: 0 trades fired (lookback bug + sub-tick stop rejection)
- 2026-05-08: 0 trades again — diagnosed as `MIN_STOP_TICKS=3` rejecting 100% of gap_fill signals

Root cause: the trader had grown to 2,929 lines with 14 risk gates, 3 cleanup
loops, multi-tier filters, time windows, and trailing profit locks all
interacting. Every fix introduced new failure modes. Bugs were impossible to
isolate because so many pieces were running in the same process.

## What we did

Split the trading system into two layers:

**Layer 1 ("the knife"):** `scripts/live_trader.py` (~480 lines)
- Reliable execution only
- Reads validated cells from `state/strategy_validation.json:live_allowlist`
- Direct broker integration, simple bracket placement
- Hard DLL + per-trade loss cap
- No multi-tier gates, no trailing logic, no orphan cleanup

**Layer 2 ("the brain"):** unchanged from prior architecture
- Strategy library (`tools/backtest/strategies.py`)
- Walk-forward validation (`scripts/walk_forward_*`)
- Daily strategy validation refresh
- Live R-multiple tracker, shadow-trade resolver
- Quant Researcher agent + sector analysts + CIO chain
- Memory + lessons + research vault
- Cowork coordination

The brain produces a flat `live_allowlist` of validated cells; the knife
consumes it deterministically. **The brain keeps growing for the long-term
multi-account multi-platform vision; the knife stays simple per-account.**

## What we should DO based on this

### Immediate (this deployment)

- **Cut over Sunday 2026-05-10 at 5 PM ET Globex reopen**: install new
  scheduled task, disable v1, verify v2 starts cleanly
- **Watch the first 24 hours closely** for: daily_cap_hit, dll_halt, fills
  matching planned prices, per-trade outcomes vs OOS predictions

### Architectural rules going forward

1. **Execution layer stays under 500 lines.** If we need to add a feature,
   add it to the brain. If it has to be in the knife, replace something else
   to stay under budget.

2. **Per-execution-layer feature, ask: does this need to run on every scan?**
   - Yes → maybe in the knife
   - No → put in the brain (refresh daily, hourly, or on-demand)

3. **No new safety gate without proven need.** Each gate I add is one more
   thing that can fire spuriously and prevent trading. The DLL + per-trade
   loss cap are the backstops. Everything else has to earn its keep.

4. **Brain → knife interface is one file**: `state/strategy_validation.json`.
   If the brain wants the knife to do something different, it changes that
   file. Knife code does not change to add new strategies.

### When to add a new strategy

1. Implement in `tools/backtest/strategies.py` (and register in `STRATEGY_REGISTRY`)
2. Add to `ALL_STRATEGIES` in `daily_strategy_validation.py`
3. Walk-forward picks it up; if cells pass, they go into `live_allowlist`
4. Knife auto-trades them at next scan
5. **Knife code untouched.** That's the win.

### When to add a new symbol

1. Add to `config/symbols.yaml` with tick economics
2. Add to `config/focus_universe.yaml` if it's tradeable now
3. Brain validates new cells on the new symbol
4. Knife auto-trades them. Untouched.

### When to add a new platform (years out)

1. Write a new ~500-line knife adapter (e.g., `live_trader_ibkr.py`)
2. Reads same `state/strategy_validation.json`
3. Translates signals to that platform's API
4. Brain doesn't care which platform. Both knives can run in parallel.

## What does NOT carry over

This simplification is a one-time architectural reset, not a recurring template.
Lessons from it:

- **The complex auto_trader was not "wrong" architecturally** — it was wrong
  for the goal (pass $50K Combine). For a real fund managing OPM, the gates
  and ladders make sense. For a single-trader $50K Combine, they were overkill.
- **Don't rebuild the v1's complexity into v2 incrementally.** When a feature
  feels needed, ask whether the brain can handle it instead.

## Open questions for future sessions

1. **The sub-tick stop issue** is unresolved. The strategy's natural stops on
   treasury futures are often <1 tick — backtest accepts these but live
   execution will get noise-stopped by spread. Either:
   - Reparameterize gap_fill to require larger gaps (separate from this lesson)
   - Accept tiny-stop trading with the per-trade loss cap as backstop
   - Find different strategies whose natural stops are bigger
2. **Topstep OCO reliability** — the v1 misdirected_leg events on every trade
   suggested broker-side OCO is flaky. The v2 trusts it; if that's wrong,
   trades will close at unexpected prices. Live data tomorrow tells us.
3. **When to merge brain expansions back** — if Cowork or Quant Researcher
   add a new analytic capability, it goes in the brain. The knife stays.

## Files changed in this simplification

Added (NEW):
- `scripts/live_trader.py` (~480 lines)
- `scripts/install-livetrader-daily.ps1`
- `tests/test_live_trader.py` (20 unit tests)
- `vault/_meta/deployment_runbook_layer1_simplification.md`
- `vault/lessons/2026-05-08_layer1_simplification.md` (this file)
- Branch: `simplification/layer1-minimal-knife`

Preserved unchanged:
- `scripts/auto_trader.py` (v1, 2929 lines)
- `scripts/auto_trader_v1_complex.py` (explicit archive copy)
- All other scripts, tools, runtime, hooks, agents, vault, state, config

The cutover is a scheduled-task swap, not a file deletion. The v1 trader
stays in the repo as reference and rollback target.
