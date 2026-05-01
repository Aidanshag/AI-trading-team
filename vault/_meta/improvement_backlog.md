---
type: backlog
purpose: Prioritized queue of fund improvements, consumed by /improve-fund autonomous cycles
---

# Improvement backlog

This file is the work queue for the autonomous-improvement loop. Each entry has explicit priority, effort, risk, and status fields so cycles can pick items mechanically.

## Format

```
- [P0|P1|P2|P3] [effort: Nmin] [risk: low|medium|high] [status: open|in-progress|proposed|merged]
  Title — one-line description
  Why: motivation
  Files: target files (best guess)
  Acceptance: how to know it's done
  Auto-merge: true|false (default false)
```

---

## P0 — critical (do first)

(empty — Phase 1 closed today's critical gaps)

## P1 — high (Phase 2 work)

- [P1] [effort: 30min] [risk: low] [status: merged 2026-04-30]
  **Real-time loss alerter (Discord webhook)** — DONE
  Implemented `scripts/loss_alerter.py` with thresholds at -$100/-$200/-$400/canTrade=false.
  Wired into `auto_trader.scan_once` after each snapshot. `--test` flag fires synthetic alert.
  Activates when user adds `DISCORD_WEBHOOK_URL` to .env.

- [P1] [effort: 45min] [risk: low] [status: merged 2026-04-30]
  **Per-strategy auto-demote on negative-EV streak** — DONE
  Implemented `_strategy_recent_streak` and `_strategy_is_demoted` helpers.
  When a strategy hits 5 consecutive stop-outs in 4h, auto-suspends for the rest of UTC day
  via `risk_events.rule='strategy_demoted_today'`.

- [P1] [effort: 60min] [risk: medium] [status: open]
  **Setup confluence requirement**
  Why: lone signals fired in noisy tape today. A signal confirmed by ≥1 of: volume above 1.5× MA, ATR expansion, or another strategy showing same direction is more reliable
  Files: `scripts/auto_trader.py:find_latest_signal` or new wrapper
  Acceptance: signals not confirmed by at least one confluence factor are skipped under autonomous mode
  Auto-merge: false (touches hot path)

## P2 — medium

- [P2] [effort: 30min] [risk: low] [status: open]
  **Cost ledger in CIO daily brief**
  Why: agents need to feel the cost burn every session. CIO's brief already exists; it just needs the cost ledger pulled in.
  Files: `agents/cio.md` (prompt update), `scripts/_session_brief.py` (if it exists), or new helper
  Acceptance: every CIO session brief opens with "MTD: gross +$X, fees -$Y, API -$Z, net +$W"

- [P2] [effort: 20min] [risk: low] [status: open]
  **Lessons → strategy_blacklist auto-promotion**
  Why: when a `vault/lessons/*.md` is tagged `confidence: RULE`, suggest a `strategy_blacklist` entry during weekly review
  Files: `scripts/auto_promote_lessons.py` (already exists — extend?)
  Acceptance: weekly review surfaces RULE-tier lessons not yet in `risk_limits.yaml:strategy_blacklist`

- [P2] [effort: 45min] [risk: medium] [status: open]
  **Regime classifier (live vol/volume metric)**
  Why: today's blanket 21:00–04:00 ET rule is crude. A live regime classifier ("ATR/avg over recent N bars below threshold → choppy → block mean-reversion") would be more precise
  Files: new `tools/regime_classifier.py`, plumb into auto_trader
  Acceptance: regime_classifier.current_regime() returns one of {trending, choppy, event, thin}; auto_trader respects it

- [P2] [effort: 30min] [risk: low] [status: open]
  **`fund halt` and `fund resume` CLI commands**
  Why: single-keystroke local kill switch. Sets/clears `trading_halt_until` from a shell command
  Files: `scripts/fund.ps1`, possibly new `scripts/halt.py` and `scripts/resume.py`
  Acceptance: `fund halt 4h` sets halt 4 hours forward; `fund resume` sets to past timestamp

## P3 — long-term

- [P3] [effort: 90min] [risk: medium] [status: open]
  **Remote kill switch (HTTP endpoint, password-protected)**
  Why: kill from your phone when you see a bleed. Tiny Flask/FastAPI endpoint, password auth, sets `trading_halt_until`
  Files: new `scripts/remote_kill.py` + service install script
  Acceptance: POST to `http://localhost:PORT/halt?duration=4h` (with bearer token) writes the halt
  Note: medium risk — requires opening a port. User must approve network exposure model.

- [P3] [effort: 2h] [risk: high] [status: open]
  **A/B test new strategies in shadow mode**
  Why: new strategies should accumulate outcomes in `shadow_trades` table for N days before going live
  Files: `tools/backtest/strategies.py` (mark which are validated), `scripts/auto_trader.py` (only fire validated for live)
  Acceptance: a `validated_after: YYYY-MM-DD` field on each strategy gates whether it can fire live or only shadow
  Auto-merge: false

- [P3] [effort: 60min] [risk: low] [status: open]
  **Documentation: CLAUDE.md update with new config blocks**
  Why: the new sections (regime_gates, cost_discipline, autonomous_restrictions) need top-level documentation so future Claude sessions discover them
  Files: `CLAUDE.md` (or create), `vault/_meta/team.md`
  Acceptance: a `## Risk floor architecture` section in CLAUDE.md explains the major config knobs

---

## How items get added

- Failed sessions / new bugs → P0 or P1 with a `lesson_ref:` link to the journal/lesson file
- Audit findings during `/improve-fund` cycles → `proposed` status until user approves
- User requests → directly added at requested priority

## How items get removed

When merged, change `status: merged` and add `merged_in:` git SHA. Keep the row for ~30 days as a record, then archive to `vault/_meta/archive/improvement_backlog_YYYY-MM.md`.
