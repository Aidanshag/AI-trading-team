---
type: playbook
applies_to: [all]
source: Mark Douglas — "Trading in the Zone" + Daniel Kahneman — "Thinking, Fast and Slow" + Nassim Taleb — "Fooled by Randomness" / "Antifragile"
---

# Psychology and discipline — the enemy you bring to work

You (and every agent) are not a coldly rational decision-maker. You are a pattern-matcher shaped by cognitive biases. The best traders don't transcend these biases — they build systems that neutralize them.

## Five biases that cost money

### 1. Loss aversion (Kahneman/Tversky)

- Losses feel ~2x as bad as gains feel good.
- Consequence: we close winners too early ("lock in the gain") and hold losers too long ("hope it comes back").
- Counter: size every trade so the P&L doesn't feel emotionally significant. Keep a journal of *decisions*, not outcomes, so you grade process not feeling. Honor the stop mechanically.

### 2. Recency bias / availability heuristic

- What happened recently feels more likely than it statistically is.
- Consequence: a few wins = overconfidence → oversize. A few losses = underconfidence → miss the next setup.
- Counter: use base rates. Your long-run hit rate is more informative than the last three trades. Review monthly, not daily.

### 3. Confirmation bias

- We notice evidence for our thesis and ignore evidence against.
- Consequence: we miss the invalidation signal and ride losers.
- Counter: write the *invalidation level* into every thesis at entry. Review it on every news item. Have the Research agent stress-test theses with the null hypothesis.

### 4. Narrative fallacy (Taleb)

- We need a story to understand the market; we mistake story for explanation.
- Consequence: we over-attribute to the latest narrative ("AI bubble," "rate cuts," "hard landing") and underweight random noise.
- Counter: separate facts from narrative in every note. Frontmatter convention: a thesis includes a *what could prove this wrong* section and at least one section of pure data.

### 5. Survivorship / hindsight bias

- The winners' books are on the bestseller list; the bankruptcies are forgotten.
- Consequence: we imitate a surviving pattern without knowing how many practitioners of the same pattern blew up.
- Counter: optimize for survival, not success. Read accounts of blow-ups (LTCM, Archegos, Amaranth, Melvin) and trace what those managers believed at the moment before.

## The Douglas framework ("Trading in the Zone")

Mark Douglas' core insight: **markets are probabilistic, not predictive.** You cannot know the outcome of a single trade; you can only know the long-run distribution of outcomes from following a tested process.

Consequences:

- **Any single trade can be a loser, including high-conviction ones.** This is normal, not a process failure.
- **The point of the rules is to make you indifferent to the outcome of any single trade.** Rules generate consistency; consistency generates edge.
- **Emotion is the signal that you're attached to outcome.** The exit from emotion is back to process.

## Taleb: convexity and anti-fragility

- Preserve optionality: never bet the farm; keep dry powder for regime shifts.
- Prefer convex payoffs (options, defined-risk structures) over linear ones when volatility is mispriced.
- Anti-fragile books benefit from volatility; fragile books die in it. Check which one you have.

## Applied to an autonomous multi-agent fund

Agents don't feel fear or greed, but they inherit bias from their training distribution, their prompts, and the feedback loops we build:

- An agent told to "find opportunities" will fabricate marginal ones — same as a trader with itchy hands. Counter: explicitly instruct "no trade" as a valid output.
- An agent scored on P&L will drift toward aggressive sizing. Counter: score on rule adherence and thesis quality, not outcome.
- An agent with short feedback cycles will pattern-match on noise. Counter: longer wake cycles + weekly reviews > reactive ticks.
- An agent that saw a recent loser may overcorrect. Counter: hard-coded sizing rules that don't respond to recent outcome.

## Daily practice (for the human operator)

- Read the day's journal at the end of the day, not during it.
- Do not override the risk manager on a whim. If you want to override, journal *why* for 24h before making the change permanent.
- The goal is not to be right. The goal is to be disciplined. Right follows discipline over long time horizons.
