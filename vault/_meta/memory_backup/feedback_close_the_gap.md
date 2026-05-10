---
name: Real goal — close the gap between backtest and production
description: User reframe 2026-05-08 — primary mission is validating that what ships matches what was predicted, not maximizing edge or hit rate
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User directive (2026-05-08, end of session):

> "Just so you understand this is now the real goal: close the gap between
> looks great and actually works good in production"

This is a meta-level reframe of what we're optimizing for. It supersedes
optimization-focused goals when they conflict.

## What this means

**The headline metric is no longer P&L. It's "did live behavior match
backtest predictions?"**

A 60% hit-rate strategy that does exactly what the backtest predicted is
**worth more** than a 70% hit-rate strategy that exhibits surprising
divergence in live execution. The first is reliable infrastructure; the
second is gambling.

The slippage discovery on 2026-05-08 was the founding incident — a
strategy that backtested at +$81k 60d collapsed to -$113k under realistic
slippage, because the backtest didn't model fills correctly. The path to
fund profitability runs through closing such gaps, not through finding
ever-cleverer strategies.

## How to apply

### 1. Prioritize measurement over optimization
- Build measurement infrastructure FIRST, then optimize
- Every new strategy must come with: backtest prediction → live measurement → variance report
- "Edge improvement" claims must include slippage, latency, fill rate
- A worse-but-validated edge beats a better-but-unvalidated one

### 2. Predictions are explicit and logged
- BEFORE deploying a change, write down what we expect (P&L range, hit
  rate, fill rate, slippage profile)
- AFTER each session, compare actual to predicted
- Variance is the primary signal. If actual matches predicted: trust grew.
  If diverges: find the gap before adding new things.

### 3. The list of known unknowns is explicit
At any moment, we should be able to enumerate:
- What we measured directly from production
- What we extrapolated from adjacent data
- What we assumed without measurement

Each unknown gets a plan to either measure or accept.

### 4. Reject improvements that compound unknowns
When evaluating a proposed change, ask: "Does this make our backtest
predictions more or less testable?" If less (e.g., adding parameters
without slippage modeling, or stacking strategies before validating
each), defer the change until the validation infrastructure catches up.

### 5. Operational reliability is part of "production works"
- Process crashes, OCO race conditions, order rejections, latency
- These are gap items even though they don't show up in backtest
- Watchdog, monitoring, alerts are all "close the gap" investments

## Concrete behavior changes

**Before this directive:**
- "What's the highest-edge strategy we can deploy?"
- "How can we improve P_pass for Combine?"
- "What param tweak boosts expected return?"

**After this directive:**
- "What did backtest predict for last session vs what actually happened?"
- "What unknowns are we still operating on?"
- "What's the smallest change that would let us measure the next gap?"

## Practical examples this session

**Right call (matches new framing):**
- Deploying gap_fill_wide and locking it in for Sunday → measurement value
- Building slippage_tracker.py → infrastructure first
- Refusing to ship cowork's param change tonight → preserves measurement

**Wrong call (would violate framing):**
- Stacking 5 strategies before validating one
- Optimizing params based on R-multiples without slippage modeling
- Adding watchdog the night before deploy (new failure modes)
- Saying "99% probability profitable" without measurement plan

## How this interacts with prior memories

- `feedback_continuous_trader_trim.md` — keep the knife small (compatible)
- `feedback_session_open_recap.md` — recap should now lead with
  prediction-vs-actual, not just "what happened"
- `feedback_two_layer_architecture.md` — brain/knife split serves this
  goal: brain produces predictions, knife produces actuals
- `feedback_silent_default_means_off.md` — same root principle: assumption
  ≠ measurement

## North star phrasing

If unsure what to do: ask "does this close the gap between backtest and
production, or widen it?" Choose the closing-the-gap path.
