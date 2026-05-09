---
type: meta
status: active
started: 2026-04-23
expected_end: 2026-04-28   # ~4-5 day window; user to update when Topstep is live
updated: 2026-04-23
---

# Topstep setup window — learning mode

The Topstep account is not yet open. Broker connectivity, Combine rules, and live order flow are all **not wired**. The user expects to finish Topstep setup in 4–5 days (~2026-04-28). Until then, the fund is in **learning mode**.

## Every futures agent reads this on wake

**You are not paused. You are preparing.** The 4–5 day window is a deliberate sprint to sharpen the fund's edge before live capital is at risk. Treat this as a paid week of training in a hedge-fund internship. What you produce this week compounds for the rest of the fund's life.

## What every analyst produces this week

By end of window, each sector analyst should have:

1. **At least 6 product deep-dive notes** under `vault/futures/product_deep_dives/{SYMBOL}.md`. One per tradeable symbol in your coverage, or the top 6 if coverage is larger. Use the template at `vault/futures/product_deep_dives/TEMPLATE.md`.
2. **A current watchlist** at `vault/futures/watchlists/{sector}.md` — which symbols you'd trade this week if you could, with preliminary conviction levels.
3. **At least 5 shadow trades** at `vault/futures/shadow_trades/YYYY-MM-DD.md` — full thesis + size + stop + target, tracked against actual price action. Honest only: no back-fitting, no moving the entry after the fact.
4. **A pattern note** at `vault/futures/patterns/{sector}_playbook.md` — 2–3 recurring setups you'd trade in your sector, with specific trigger criteria and invalidation levels.
5. **One "what I didn't know at wake-1" note** at the end of the window in `vault/journal/` — document what you learned that you'll carry forward.

## What the CIO and PM produce

- **CIO**: update `vault/regime/current.md` daily; publish the daily brief; review what analysts produced and flag gaps.
- **PM**: size every shadow trade as if it were real. Keep a shadow-ledger at `vault/futures/shadow_trades/_ledger.md` tracking cumulative imaginary P&L, hit rate, average R-multiple — the calibration data the fund will need on Day 1.

## What the Risk Manager produces

- Vote on every shadow trade as if it were real. Your verdicts set the precedent for live-trading culture.
- Spend at least one wake reviewing the trader-wisdom playbooks under `vault/playbooks/` and cross-reference them with our current risk limits. If any limit is out of step with best practice, flag to the user via a journal note under `## Refinement ask — Risk Manager — ...`.
- Spend at least one wake stress-testing the Topstep Combine rules against a realistic weekly schedule of shadow trades — would we have passed? where would we have tripped consistency or DLL?

## What the Options Risk agent produces

- A worked example of each allowed options structure in `vault/futures/patterns/options_structures.md` — entry criteria, Greeks profile, IV-regime fit, exit rules.
- A note on futures-options specifics: `/ES` options expiry cycles (weeklies, AM-settled, PM-settled), `/CL` options pin risk, etc.

## What Compliance produces

- Sanity checks on the audit trail daily. Every shadow trade has a thesis note, a PM proposal, a risk vote.
- An end-of-window summary at `vault/reviews/topstep_setup_window_summary.md` — what worked, what didn't, where the process needs tightening before live.

## What the Research agent does

- Research is invoked only for genuinely hard questions. Use it sparingly in this window (budget: 5 calls total across the week).
- Candidate questions worth burning a Research call on:
  - "What are the highest-probability regime shifts we should be prepared for when we go live next week?"
  - "Given the current Topstep Combine rules, what is the optimal trade cadence and size profile to pass without taking catastrophic tail risk?"
  - "Which of our sector analysts' shadow-trade track records in this window is most and least calibrated? What does that tell us about trusting them at size on Day 1?"

## Conservation reminder

The user has emphasized API cost conservation. During learning mode, this matters more, not less — no paying customer, just training.

- Default cadence is **30 min ticks** during the day (not 15).
- CIO wakes one analyst per tick, not all of them.
- Wake Sonnet/balanced only for genuinely hard thesis moments; default to Haiku.
- Prompt-cache aggressively on the stable context (team preamble, playbooks, symbol registry, product deep-dives once written).

## Ending the window

When the user updates `expected_end` and flips the `status` field to `completed`, the fund transitions to live (paper-live on Topstep Combine). Continue learning habits — the shadow-trade discipline continues, but real orders now flow through the same pipeline.
