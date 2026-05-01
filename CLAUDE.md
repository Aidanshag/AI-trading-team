# CLAUDE.md — orientation for future Claude sessions

You are working on an **AI-driven futures trading fund** that trades CME futures via Topstep / ProjectX. The fund's single goal right now is **passing the $50K Topstep Combine** (cumulative +$3,000 profit, no DLL/TDD breach, ≥5 trading days, no day > 50% of total profit).

## Read these first, in order

1. `vault/_meta/current_goal.md` — the single top-level goal (currently: pass the Combine, above everything else)
2. `vault/_meta/economics.md` — the cost equation (~$575/month fixed costs; NET monthly P&L is the only KPI)
3. `vault/_meta/principles.md` — distilled trading canon (Bellafiore, Schwager, Tharp, Steenbarger, etc.) with `→ encoded:` markers showing which principles are already in code/config
4. `vault/_meta/improvement_backlog.md` — work queue for the autonomous improvement loop

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

## What success looks like

The fund's only KPI is **NET monthly P&L** (gross trading − Topstep fees − API spend − subscriptions). Until the Combine is passed, the secondary KPI is **days-without-rule-violation**. A clean no-trade day is fine. A day with a $300 win + $100 loss is fine. A day with $1,000 of churn is failure even if NET is positive.
