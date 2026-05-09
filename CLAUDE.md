# CLAUDE.md — orientation for future Claude sessions

You are working on an **AI-driven futures trading fund** that trades CME futures via Topstep / ProjectX. The fund's near-term goal is **passing the $50K Topstep Combine**. The longer-term plan is to **scale via copy-trading across multiple Topstep accounts**, not by chasing higher per-account returns.

## Anchor principles (added 2026-05-09)

These are the architectural truths that guide every decision. If a proposed change conflicts with these, defer it.

1. **5-10% per year per account is the realistic target.** Anyone projecting more is fitting noise. Scale comes from N accounts, not from per-account alpha.
2. **Friction-first design.** Slippage, fees, subscriptions are the FIRST inputs to every model, not afterthoughts. Default assumption: pessimistic. Lowering it requires evidence.
3. **Close the gap between backtest and production.** The headline metric is "did live behavior match what we predicted?" — not P&L. Variance is the primary signal. (See `feedback_close_the_gap.md` in memory + `vault/_meta/strategic_roadmap.md`.)
4. **Reliability >> peak performance.** A 7%/yr strategy that never blows up beats 30%/yr that occasionally gives back 50%.
5. **Replicability matters.** Every component must be deterministic, copy-able to a fresh account, documentable for the future multi-account world.
6. **Build to outlast individuals.** Every agent replaceable, every decision documentable, every metric reproducible.

## Read these first, in order

1. `vault/_meta/strategic_roadmap.md` — north-star phased plan + what we'd do differently (read for vision)
2. `vault/_meta/current_goal.md` — the single top-level goal (currently: pass the Combine)
3. `vault/_meta/data_strategy.md` — what we pay for, what we don't, what we accumulate ($0 path)
4. `vault/_meta/economics.md` — the cost equation (~$575/month fixed costs; NET monthly P&L is the only KPI)
5. `vault/_meta/principles.md` — distilled trading canon with `→ encoded:` markers
6. `vault/research/slippage_mitigation_playbook.md` — slippage levers + slippage-tolerant strategy categories
7. `vault/_meta/improvement_backlog.md` — work queue for the autonomous improvement loop
8. `vault/_meta/cowork_coordination.md` — parallel agent coordination state

## Layout

| Path | Purpose |
|---|---|
| `agents/*.md` | Agent prompts (CIO, Risk Manager, PM, Edge Hunter, Quant Researcher, Compliance, etc.) |
| `config/*.yaml` | Risk limits, fund toggles, symbol metadata, focus universe |
| `hooks/risk_gate.py` | The PreToolUse safety hook — last line of defense before any order |
| `runtime/orchestrator.py` | Agent chain wiring, scheduler integration |
| `scripts/auto_trader.py` | Heuristic strategy library + broker integration (the "trader" itself) |
| `scripts/preflight.py`, `eod.py`, `halt.py`, `loss_alerter.py` | Operational CLIs |
| `state/db.py`, `state/schema.sql` | SQLite persistence (orders, positions, decisions, risk_events, account_snapshots, daily_pl) |
| `tools/topstep.py`, `tools/projectx_client.py` | Broker integration |
| `vault/` | Obsidian vault — playbooks, lessons, journals, principles, agent docs |
| `tests/` | pytest suite (~200 tests; one file `test_overnight_fixes.py` has a known SDK-budget failure unrelated to safety) |

## The risk safety floor (must understand before editing risk code)

Every order goes through `hooks/risk_gate.py`. Checks fire in this order:
1. `_check_kill_switch` — manual halt + auto-expiring halt timestamp
2. `_check_broker_can_trade` — Topstep `canTrade=false` server-side flag
3. `_check_thin_tape_regime` — 21:00–04:00 ET window (regime gate)
4. `_check_autonomous_rth_window` — 07:30–14:30 ET when autonomous mode on
5. `_check_snapshot_freshness` — refuse to trade with snapshot >5min old (autonomous only)
6. `_check_focus_universe` — blocks symbols outside the focus list
7. `_check_strategy_blacklist` — blocks symbol+strategy combos from RULE-tier lessons
8. `_check_active_lessons` — RULE/HARD-tier lessons in `vault/lessons/` veto matching trades
9. `_check_post_stop_cooldown` — 15-min anti-tilt window after stop_hit_observed
10. `_check_high_impact_blackout` — ±5min around high-impact economic events
11. `_check_combine_defensive_ladder` — progressive tightening at -$150/-$300/-$500 (lockdown)
12. `_check_daily_target_lock` — profit-protect at +$200/+$400 + 40% giveback
13. `_check_daily_trade_count` — 8/day cap (autonomous mode)
14. `_check_session_window` — Globex maintenance break
15. `_check_no_naked_shorts` — naked short OPTIONS only (futures relaxed 2026-04-29)
16. `_check_defined_risk_structures`
17. `_check_stop_required` — every outright order must have a stop
18. `_check_daily_loss_limit` — DLL + projected DLL
19. `_check_trailing_drawdown` — TDD + projected TDD
20. `_check_per_symbol_limits`
21. `_check_sector_and_basket_limits`
22. `_check_consistency_rule` — Topstep 50% advisory (warn-tier, doesn't block)
23. `_check_options_structure_allowed`

The auto_trader has its OWN parallel checks (it doesn't go through the SDK PreToolUse hook). See `scripts/auto_trader.py:scan_once` — same gates, plus its own:
- `_capture_account_snapshot` — writes the snapshot the hook reads
- `_in_thin_tape_window` — local regime check
- `_today_fees_usd` / `_today_total_trade_count` / `_today_trade_count_for_symbol` — cost-discipline
- TDD-anchor-leading halt
- Internal-DLL hard kill
- Consecutive-loser pause + agent-cascade auto-halt

## Strategic focus — gap_fill on ZN/NG/6E (validated 2026-05-04)

The fund's **validated headline edge** is `gap_fill` on Treasury futures (ZN), nat gas (NG), and euro FX (6E). 60-day walk-forward backtest (45d train / 15d held-out OOS) on 5m intraday bars:

- **ZN gap_fill (Asian + PostClose)**: train E=+0.87R t=+15.21 | **OOS E=+1.10R t=+11.95** (n=256 OOS) — fund's primary edge
- **6E gap_fill**: train E=+1.50R | **OOS E=+2.65R t=+3.63** (small n but strong)
- **NG gap_fill**: train E=+0.64R | OOS E=+0.83R t=+1.53 (borderline holds)

Gating is enforced via `scripts/auto_trader.py:STRATEGY_SYMBOL_ALLOWLIST` — `gap_fill` ONLY fires on `{ZN, NG, 6E}`. On MES/MNQ/MCL/GC the strategy didn't validate OOS and is blocked.

**Do not promote any other strategy to high conviction without walk-forward validation showing OOS t>2.0 on at least n=100 trades.** Earlier session-state experiments (FVG/order_block/liquidity_sweep at default params) showed coin-flip expectancy and have been demoted to "low" conviction pending parameter tuning.

**Removed entirely 2026-05-04**: `vwap_reversion` — confirmed broken across all symbols (hit rate 1-10%, t-stat as bad as −24 on MNQ RTH OOS). Code deleted from `tools/backtest/strategies.py`.

The strategic intent is still price-action / mathematical — gap_fill IS a price-action mean-reversion strategy, just one that happens to be more rigorously validated than the ICT-flavored FVG/OB/LS at our parameter set. If walk-forward parameter sweeps later validate FVG/OB on a per-symbol/session basis, re-promote them.

## Two parallel trading paths (important)

- **Agent chain** (CIO → Analyst → PM → Risk Manager → Execution Trader): orders go through `mcp__topstep__topstep_place_order`, gated by `hooks/risk_gate.py`
- **auto_trader** (`scripts/auto_trader.py`): heuristic strategy library, calls broker directly, applies the same gates manually via `apply_risk_gate()`

Today (2026-04-30) the agent chain is largely dormant — the auto_trader does the actual trading. The agents do regime reads, post-mortems, weekly reviews. This split is documented in `vault/_meta/trading_process.md`.

## Operational scripts

```
fund start          # launches auto_trader (5-min scans)
fund stop           # kills all python processes
fund preflight      # fail-closed pre-session checklist
fund eod            # cost ledger (today's NET P&L)
fund halt 4h        # set trading_halt_until forward
fund resume         # clear halt
```

## Autonomous infrastructure

- **Windows scheduled task `FundAutoTraderDaily`** — auto-starts the trader Mon-Fri 06:30 ET (installed via `scripts/install-autotrader-daily.ps1`). Runs preflight first; aborts on failure.
- **Cloud Claude routine `trig_011w6DUmXbojsfkjKtCaJfBa`** — daily 09:00 UTC. Reads the improvement backlog, picks one item, implements, tests, auto-merges (non-risky) or opens PR (high-risk). Manage at https://claude.ai/code/routines.

## Recent history (read for context before making changes)

- **2026-04-29** — Topstep Combine DLL breached during overnight thin tape (-$1,013). Root cause: empty `account_snapshots` table → DLL/TDD/ladder/consistency-rule checks all silent. Plus strategies firing in untradeable Asian-session tape. Massive rebuild of safety floor that night (snapshot pipeline, regime gate, cost discipline, autonomous_restrictions, projection on DLL/TDD/ladder, sector-aware MIN_STOP_TICKS, hit-rate-aware EV gate). See `vault/lessons/2026-04-29_*.md`.
- **2026-04-30** — Account locked by Topstep until DLL reset. New safety floor first-day validation. No trades placed (gates blocked overnight + outside-RTH starts). Cloud improvement routine + scheduled-task auto-start installed.

## Working with this code

**When editing risk-related code:** read `hooks/risk_gate.py` and the existing checks. New checks should fail closed. Add a test in `tests/test_risk_gate.py`.

**When editing the auto_trader:** mirror the structure of existing checks. The PID lock prevents duplicates; cooldown floor is 15 min in live mode; fee budget caps the day.

**When adding tests:** target `python -m pytest tests/ -q --ignore=tests/test_overnight_fixes.py`. The `test_overnight_fixes.py` file has a pre-existing SDK-budget regression that's not safety-related.

**When changing config:** prefer text edits over `yaml.safe_dump` — the latter strips comments. See `scripts/halt.py` for the regex-edit pattern that preserves comments.

**Never edit `hooks/risk_gate.py`, `state/db.py`, `state/schema.sql`, `tools/topstep.py`, `tools/projectx_client.py`, or `risk_limits.yaml.hard_rules` without explicit user approval.** These are the HIGH_RISK_FILES per the auto-merge policy.

**Never push to master from the cloud routine if any HIGH_RISK_FILES were touched** — open a PR instead.

## Code-review checklist — Pattern A and Pattern B

Two structural failure shapes have caused real losses (4/29 and 5/5 incidents). Both are documented as PATTERN-tier in `vault/_meta/analysis/2026-05-07_lesson_meta_patterns.md`. Every code or config change — Cowork, Claude Code, `/improve-fund` cycle, or sector analyst — must check itself against these before merging.

### Pattern A — fail-silent defaults

When a gate or check reads a value that may be missing, empty, zero, or `None`, the default behavior MUST NOT be "treat as safe to proceed."

Before merging any change that touches a gate, telemetry write, or default value, ask:
1. *If this value is missing or zero, what gates depend on it?*
2. *Do those gates currently read missing/zero as "safe to proceed"?*
3. *If yes, either change the default to a fail-closed marker, or add an explicit assertion that fires loudly when the value isn't fresh.*

Past examples this would have caught:
- 2026-04-29: empty `account_snapshots` table → DLL/TDD/ladder/consistency-rule checks all silently no-op'd → −$1,013 drawdown.
- 2026-05-05: `unrealized_pl_usd` hardcoded to `0.0` in `_capture_account_snapshot` → DLL/TDD/ladder projections blind to NG bleeding $702 over 7 hours.
- 2026-05-05: `daily_hard_target_usd: 0` written by uncommitted config edit → profit-lock silently disabled until the `risk_config_drift` audit fix.

Already-encoded defenses to model new code on: `_audit_risk_config_drift` (warns on zeroed gates), `degraded_heartbeat` pattern in `_capture_account_snapshot` (fail-closed snapshot when fetch fails).

### Pattern B — wrong-context validation

A metric calibrated under one set of conditions applied under a different set. The metric is correct *somewhere* but wrong *here*.

Before merging any change that adds a strategy, threshold, calibration, or signal filter, ask:
1. *Where will this be deployed?* (symbol set, session window, side, timeframe)
2. *Where was the threshold calibrated?* (data source, regime, time range, granularity)
3. *Are the deployment regime and the calibration regime the same?*
4. *If not, recalibrate against the deployment regime, OR carry the calibration scope as an explicit constraint that gates firing.*

Past examples this would have caught:
- 2026-04-29: ZN ORB used RTH volume thresholds (1500-3000 contracts/bar baseline) in overnight thin tape (5-15 contracts/bar baseline). "3× confirmation" meant something completely different cross-regime.
- 2026-05-05: aggregate-level walk-forward passed while cell-level (symbol × session × side) failed. Trader fired at cell-level, validation was at aggregate. → strategy validation lockdown.

Already-encoded defenses: `STRATEGY_CELL_ALLOWLIST` (cell-level granularity), `live_strategies_filter` (hand-picked subset), thin-tape regime block. Open encoding gap: volume thresholds aren't yet session-aware (calibrate-then-deploy version of the principle isn't enforced for volume).

### When the checklist catches something

If applying either pattern surfaces a real risk in the proposed change, the change should either be modified to address it OR the analysis piece (`2026-05-07_lesson_meta_patterns.md`) updated with a note explaining why this case is OK to merge as-is. Don't silently ship around the pattern.

If a third real-world incident matching either pattern emerges despite this checklist, escalate to hard-encoding the check as a CI test that fails the build.

## What success looks like

The fund's only KPI is **NET monthly P&L** (gross trading − Topstep fees − API spend − subscriptions). Until the Combine is passed, the secondary KPI is **days-without-rule-violation**. A clean no-trade day is fine. A day with a $300 win + $100 loss is fine. A day with $1,000 of churn is failure even if NET is positive.
