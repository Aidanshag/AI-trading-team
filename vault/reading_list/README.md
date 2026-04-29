---
type: index
---

# Reading list

Curated reading that raises the fund's intellectual floor. Agents use this list to prioritize research dives; the user uses it to stay sharp.

## Books (foundation)

- **Market Wizards** — Jack Schwager. Interviews with the best traders of their era. Every agent should quote from it.
- **The New Market Wizards** — Schwager. Sequel.
- **Hedge Fund Market Wizards** — Schwager.
- **Reminiscences of a Stock Operator** — Edwin Lefèvre. 1923, still the best trader psychology book.
- **Trading in the Zone** — Mark Douglas. Probabilistic thinking and emotional discipline.
- **Fooled by Randomness** — Nassim Taleb. Base rates and survivorship bias.
- **The Black Swan** — Taleb. Fat tails.
- **Antifragile** — Taleb. Convexity in portfolios.
- **Thinking, Fast and Slow** — Daniel Kahneman. The cognitive biases you can't avoid.
- **When Genius Failed** — Roger Lowenstein. LTCM blowup. Read before you ever size anything big.
- **The Big Short** — Michael Lewis. Pattern recognition in a bubble.
- **Flash Boys** — Michael Lewis. Market microstructure basics.
- **Inside the House of Money** — Steven Drobny. Macro traders interviewed.
- **More Money Than God** — Sebastian Mallaby. Hedge-fund history.
- **Options as a Strategic Investment** — Lawrence McMillan. Options reference.
- **Option Volatility and Pricing** — Sheldon Natenberg. Options reference.
- **The Man Who Solved the Market** — Gregory Zuckerman. Jim Simons & Renaissance — required reading for systematic discipline.

## Ongoing (subscribe or RSS-follow)

- Fed press releases + speeches (RSS: `federalreserve.gov/feeds/press_all.xml`)
- BLS releases (RSS: `bls.gov/feed/bls_latest.rss`)
- Treasury Dept press (RSS: `home.treasury.gov/rss/press.xml`)
- Calculated Risk blog (RSS) — housing and macro, free, high signal
- ZeroHedge (RSS) — noisy but occasional gems; filter aggressively
- Reuters market news (RSS)
- Liberty Street Economics (NY Fed blog)
- Bank of England / ECB / BOJ official blogs

## Podcasts

- Odd Lots (Bloomberg) — smart macro conversations
- Macro Voices — technical macro interviews
- Grant's Interest Rate Observer — cross-asset
- Capital Allocators — investor mindset
- Rough Road (commodity focus)

## Papers and long-form (read once, reread quarterly)

- "The Quantitative Investor" style guides from AQR research
- "Skewness and Kurtosis in Commodity Returns" (classic foundation for fat-tail awareness)
- The Turtle rules (Richard Dennis / William Eckhardt) — trend-following canon
- BIS quarterly reviews
- CFTC staff analyses of Commitments of Traders data

## How to use this list

- **Analysts**: pick one book per quarter. During the Topstep setup window, prioritize Market Wizards and Trading in the Zone.
- **Research agent**: when asked to deep-dive a topic, ground the answer in relevant book chapters and papers here.
- **Risk Manager**: reread When Genius Failed and Fooled by Randomness on repeat.
- **User**: already a market junkie. Use this list to compare against what you're already consuming; add your own finds here.

## Distilled output

The reading on this list does not enter agent prompts as text — token cost is real. Instead it gets distilled into:

- [`vault/_meta/principles.md`](../_meta/principles.md) — single-page canon of one-liner rules indexed by situation, with explicit citations to the source book/paper. **Every agent reads this on first wake.** When a principle is enforced in code, the entry is marked `→ encoded:`.
- [`vault/_meta/economics.md`](../_meta/economics.md) — the cost equation the team operates under. Monthly fixed cost, per-trade math, what a profitable day looks like.

The pipeline:

```
book / paper / podcast  →  one-line rule in principles.md  →  (when high-leverage) code/config rule
```

If a principle from the reading list isn't yet in `principles.md`, propose it during the weekly review. If it's been there for a quarter and isn't yet `→ encoded:`, ask whether it CAN be encoded — most should be.
