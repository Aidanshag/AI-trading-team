---
type: playbook
triggers: [US CPI release, US Non-Farm Payrolls release, US Core PCE release]
applies_to: [index_macro, rates, fx_futures, metals]
---

# CPI / NFP / PCE days

## Trigger

- CPI: 8:30 AM ET on scheduled day.
- NFP: 8:30 AM ET first Friday of the month.
- Core PCE: 8:30 AM ET on scheduled day.

## What agents must NOT do

- No new entries in the 15 min before the print or the 30 min after. Tape is noisy; fills are poor; stops get run.
- Do not add to positions intraday based on "the trend is clear now" — the first hour after these releases mean-reverts more often than not.

## Preferred structures

- For a strong view on the print: long straddle or strangle placed at least 24h before (decay-aware). Avoid buying vol the morning of.
- For post-print direction: wait 30 min, read the curve (2s10s), DXY, and index futures together. If three of four confirm, a swing position with tight-ish stop is defensible.

## What to watch

- Shelter / OER in CPI — the lagging component.
- Participation rate and wage growth in NFP — often more important than the headline jobs number.
- Supercore services in PCE.

## Exit

- Same session unless thesis is explicit multi-day; overnight holds require defined-risk wrapping.
