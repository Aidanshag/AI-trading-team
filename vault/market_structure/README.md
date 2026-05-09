---
type: section_index
status: starter
created: 2026-05-09
---

# Market Structure

This section is for documentation of trading-mechanism details that affect strategy design — session mechanics, auction mechanics, option expiry details, order book dynamics. It's deliberately a SLIM section: only documents that directly inform strategy decisions belong here.

## What goes here (when relevant)

| Topic | When to write | Why |
|---|---|---|
| Session-open dynamics | When a strategy depends on session-open behavior | Affects entry timing windows |
| Auction calendar mechanics | When an event-driven strategy is added | Treasury auction days behave differently |
| Option expiry mechanics | When option-related strategies enter scope | Pin risk, gamma flips |
| Order book depth profile | When sizing matters for market impact | Currently 1-5 contracts; not yet relevant |
| Maker vs. taker pricing | When considering post-only entries | See `vault/research/slippage_mitigation_playbook.md` lever #1 |
| Globex session boundaries | When session-aware strategies need precision | We have basic 4-bucket sessioning; deeper detail goes here |

## What does NOT go here

- Pure macro/regime: see `vault/regime/`
- Strategy logic: see `vault/research/strategy_specs/` and `tools/backtest/strategies.py`
- Generic trading principles: see `vault/_meta/principles.md`
- Playbooks for specific events: see `vault/playbooks/`

## Current state

This section is a starter — empty until a strategy proposal demands documentation here. Don't pre-populate; write when needed.

## Cross-references

- `vault/_MAP.md` — vault index links here
- `vault/playbooks/event_window_procedure.md` — event-time mechanics
- `vault/research/slippage_mitigation_playbook.md` — maker-strategy considerations
