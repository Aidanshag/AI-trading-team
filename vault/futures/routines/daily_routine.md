---
type: routine
applies_to: [cio, pm, risk_manager, all_futures_analysts]
---

# Daily routine

## Before the open (pre-market / overnight review)

**CIO** (~30 min before major US session open, or at Asia session start):

1. Read overnight journal entries.
2. Check economic calendar for the next 12h via the market-data tool.
3. Scan news across the high-RSS feeds for the last 8h.
4. Update `vault/regime/current.md` if anything has materially shifted.
5. Publish the **daily brief** to today's journal. Format:
   - Regime read (one line: regime + confidence).
   - Top three themes for today.
   - Events to watch with times.
   - Analyst wake plan (who to wake, why).
   - Symbols on standdown (e.g. "No new /CL before EIA at 10:30 ET").
6. Wake the first analyst on the plan.

## Session open (when CME session opens)

**Each analyst the CIO wakes**:

1. Read the daily brief.
2. Read product deep-dives for your coverage (cached).
3. Pull current quotes/bars for your top 3 symbols.
4. Scan sector-specific news.
5. Decide: is there a clean setup in anything today?
   - Yes → write/update the thesis for that symbol. Propose to PM.
   - No → append a one-line "no-trade update" to today's journal. Idle.
6. Note any refinement asks or questions for the user as you go.

## Mid-session (every 30-min tick)

**CIO**:

- Rewake only if something has changed — new high-impact headline, price alert, risk event.
- If nothing changed: record a one-line "no material change" decision. Idle.

**Analysts** (only if CIO wakes them):

- Recheck the tape vs your live thesis. Does price still honor it?
- If thesis is invalidated: close the proposal; write a brief post-mortem into the journal.

**Risk Manager**:

- Runs on every order proposal (real or shadow). You don't wake on ticks unless there's a proposal or a risk event.

## Event windows (around FOMC / CPI / NFP / EIA / WASDE / etc.)

- 15 min before → freeze theses; no new proposals.
- 30 min after → analyst with coverage writes a 2-sentence tape-read note.
- Risk Manager confirms stops on existing positions are outside 1.5× ATR.
- CIO may wake Research for a deeper read on a surprise print.

## Session close

**Each analyst who published a thesis today**:

1. Mark it "played out" or "invalidated" by end-of-session price action.
2. Write a 3-bullet post-session note appended to the thesis.

**PM**:

- Close end-of-day reconciliation. All shadow trades' status updated.

**CIO**:

- Publish the **daily wrap** to today's journal: what happened, what we traded (shadow or live), what we learned, what tomorrow looks like.

**Compliance**:

- Run the end-of-day audit (see the Compliance prompt).

## Overnight (if CME session continues)

- The fund idles between the 15:50 CT cutoff and the next morning's pre-market prep.
- Haiku CIO wakes every 2h for overnight check: any news, any price alert, any Asian-session shock. Most wakes are "no change; sleeping."

## Token-budget discipline

- Analyst wake that ends in "no-trade update" should be under 1,500 tokens.
- Full thesis wake should be under 5,000 tokens.
- Risk Manager vote should be under 2,000 tokens (unless frontier-escalated).
- Exceeding these flags to Compliance for review.
