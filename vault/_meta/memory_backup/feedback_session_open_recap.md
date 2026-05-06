---
name: Open every new session with a recap
description: User authorized 2026-05-06 to act autonomously between sessions. When user first prompts after being away, lead with a recap of what's happened (trades, validations, system events) before answering their question.
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User asked 2026-05-06: "When I first prompt you going forward just give me a
recap of what you have done while I was away."

**Why:** User has granted broad standing authorization (act on the queue,
implement validated strategies, widen the filter per the staged plan,
make calibration fixes). They want visibility into what changed without
having to ask. The recap is their accountability check.

**What to include in the recap on session-open:**

1. **Trader status** — alive/dead, PID, last scan time, # snapshots since last session
2. **Trades since last session** — symbol, side, strategy, R-multiple outcome (run the precise per-step P&L delta query against `account_snapshots`)
3. **Cumulative P&L change** — yesterday's close balance vs current
4. **Daily validation results** — promotions/demotions from preflight runs (read latest `vault/research/validation/<date>_daily_validation.md`)
5. **Filter widens executed** — if I auto-widened `live_strategies_filter` per the staged plan, name the stage and the rationale
6. **Anomalies** — any `risk_config_drift`, `protective_stop_missing`, `loss_hard_cap`, `daily_target_action_fired`, or `consecutive_losers_halt` events
7. **Outstanding decisions for the user** — anything I held off on per the bounds (position sizing, HIGH_RISK_FILES, etc.)

**Format:** Lead with a one-sentence headline (e.g., "Net +$120 overnight, 2 trades, both winners on gap_fill ZT"). Then a structured recap of the above. Keep it tight — the user can drill into specifics if they want.

**Important caveat to remember:** Claude Code sessions don't run in the
background. I CAN'T literally take autonomous action between user
prompts. What I CAN do is:
- Set up systems that run autonomously (trader, watchdog, daily validation,
  auto-commit hook, shadow resolver)
- Write memory + lessons that future sessions inherit
- Configure the daily validation to auto-promote/demote per rules
- Have the auto-commit hook fire on Stop (preserves work to git)

So "act autonomously between sessions" effectively means: when invoked
(e.g., next user prompt), use the full standing authorization to do
whatever moves toward the goal, including widening filters per staged
plan, implementing newly-validated strategies, or making calibration
fixes — without asking permission.

Between sessions, the autonomous systems running are:
- `auto_trader.py` (PID-locked, scans every 5-15 min)
- `trader_watchdog.py` (auto-revives on death)
- Windows scheduled task `FundAutoTraderDaily` (Mon-Fri 06:30 ET launch)
- `daily_strategy_validation.py` runs in preflight (morning refresh)
- `shadow_trade_resolver.py` runs in preflight
- Auto-commit Stop hook (fires on session end, preserves to git)
