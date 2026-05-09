---
type: playbook
triggers: [FOMC statement, FOMC press conference, SEP release, Fed minutes]
applies_to: [index_macro, rates, fx_futures, metals]
---

# FOMC days

## Trigger

- 2:00 PM ET statement release on FOMC decision days.
- 2:30 PM ET press conference start.
- Minutes release 3 weeks after the meeting, 2:00 PM ET.
- SEP (dots) quarterly.

## What agents must NOT do

- No new entries in the 30 min before the statement and 30 min after the press conference ends. This is a hard block in the risk hook's `pause_around_high_impact_events` logic; agents should not try to push at it.
- No outright short-rate-vol (selling vol) structures entered the day of FOMC.

## Preferred structures

- For directional views on a Fed surprise: long debit spreads (defined risk). Do NOT buy outright options — the vol crush after the press conference guts long premium.
- For cross-asset expressions: rates, DXY, and long-end gold/silver are the cleanest post-FOMC plays. Short-dated index futures are noisy.

## What to watch

- Dot shift vs market-implied path (use SOFR futures to gauge).
- Balance sheet language (QT pace).
- Chair's tone in Q&A — more informative than the statement on most days.

## Exit

- Close intraday same-session unless the thesis is explicitly multi-day.
- If held overnight, tighten stop or convert to a defined-risk structure before the close.
