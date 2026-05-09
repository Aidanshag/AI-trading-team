---
type: playbook
applies_to: [all]
source: Renaissance Technologies / Jim Simons, Two Sigma, Citadel quant, D.E. Shaw, AQR — published practice
---

# Quant principles — what systematic shops do that every trader should steal

You don't have to run a quant fund to benefit from quant discipline. The best systematic shops have spent billions figuring out what actually works. The principles are free.

## Principle 1 — Ensemble beats single-signal

One signal is always wrong sometimes. Three independent signals pointing the same direction is a better bet than one signal pointing very hard.

- Applied: every thesis must cite at least two independent lines of evidence. "The chart + my gut" is one line of evidence, not two.
- Applied: CIO should weight an analyst's thesis higher when it converges with another analyst's thesis via an independent path.

## Principle 2 — Data beats stories

- What actually happens in the tape beats what "should" happen. When the story and the price disagree, trust the price.
- But beware: "the tape is telling me X" is also a story, a particularly seductive one.
- The fix: pre-commit to a signal specification before you look at the tape. If the signal fires, trade. If it doesn't, don't trade even if the tape "looks right."

## Principle 3 — Edge decays

No edge lasts forever. What worked in 2015 may not work in 2025.

- Applied: every playbook and every pattern in this vault gets reviewed quarterly. If a pattern's hit rate over the last 100 occurrences has materially decayed, it gets downgraded or retired.
- Applied: the weekly review is the mechanism. Compliance flags theses whose hit rate has drifted.

## Principle 4 — Out-of-sample is all that matters

In-sample backtest performance is nearly worthless. Every signal looks great in the period it was discovered.

- Applied: for every new playbook or rule, track it on a paper/shadow basis for at least 30 trades before it's allowed to influence real-money sizing.
- Applied: don't trust yourself when you say "it worked in the past." Show it working in the walk-forward.

## Principle 5 — Execution eats alpha

A signal with 20 bps of edge pays for nothing if slippage + fees + taxes take 25 bps. Real-money returns are net of friction.

- Applied: model slippage conservatively in all shadow trades (mid-to-cover for limits, realistic market-impact for larger size).
- Applied: Execution Trader logs slippage on every fill; weekly review computes realized-vs-modeled and adjusts.

## Principle 6 — Risk in units that compose

A book is easier to manage when every position is sized in the same risk unit. Not "5 contracts of /CL and 20 shares of AAPL" — but "50 bps of risk on /CL and 50 bps of risk on AAPL."

- Applied: PM converts every proposal to "bps of equity at risk" before deciding whether to approve. This is the only number that composes across asset classes.

## Principle 7 — Rebalance (don't let winners run unbounded on the book)

Even trend-followers rebalance. A single position that has grown to 30% of the book carries idiosyncratic risk the portfolio didn't sign up for.

- Applied: if any single position exceeds 3× its original sizing (through trailing stop staying wide and the thing running), PM re-sizes or partially takes profit.

## Principle 8 — The house never sizes a bet it can't afford to lose

Kelly-optimal sizing is mathematically log-optimal but psychologically unrunnable. Practical sizing is ≤ 0.25× Kelly.

- Applied: 50 bps per trade cap is ~0.25 Kelly for a reasonably-edged discretionary trader.

## Principle 9 — Automate the rules; humanize the exceptions

Rules are code. Exceptions are journal entries. When you break a rule, record *why*. Over time, you'll see: the exceptions that made money become the next rule; the exceptions that lost money are removed from your vocabulary.

- Applied: the risk hook is rule automation; journal entries describing risk-manager overrides (which are rare and logged) are exception humanization.

## Principle 10 — Compound, don't swing

Renaissance's Medallion Fund returned ~39% annualized (net of enormous fees) for 30+ years — through boring, repeatable, small-edge trades. There are no secret crazy positions. The secret is compounding a boring edge for a very long time.

- Applied to the fund: we are not chasing moonshots. We are chasing a small, repeatable, disciplined edge that compounds. Every rule in this vault is in service of that compounding.
