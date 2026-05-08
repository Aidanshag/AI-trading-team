---
type: playbook
triggers: [any scheduled high-impact release not covered by a more specific playbook]
applies_to: [all]
---

# Event window procedure (generic)

## Definition

An "event window" = the period around a scheduled release that the risk hook has flagged as `high_impact`. Default: 15 min before to 30 min after.

## Procedure

### Before the window

1. Analysts freeze their thesis 20 min before the release. No new entries inside the window.
2. Risk manager confirms stops on existing positions are outside recent ATR × 1.5 — tight stops get shaken on events.
3. PM reviews aggregate exposure; if the event could swing multiple positions correlated, consider reducing gross before the window.

### During the window

- No agent opens a new position.
- Existing stops stand. Do not pre-emptively tighten them.
- Compliance records the window open/close to the day's journal.

### After the window

1. Read the print.
2. Analyst with coverage writes a 2-sentence tape-read note to the day's journal — what happened, what it means.
3. New entries allowed 30 min after release IF: tape direction is consistent with thesis, liquidity has returned to normal, and risk manager approves the now-tighter DLL headroom.

## What never happens in an event window

- No outright short positions opened.
- No short-vol structures opened.
- No entries without a stop.
