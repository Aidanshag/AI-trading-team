---
type: playbook
applies_to: [cio, portfolio_manager, analyst_rates, analyst_index_macro, analyst_fx_futures, research]
source: Stanley Druckenmiller's documented framework + George Soros's reflexivity + Louis Bacon's macro practice + Ray Dalio's regime framework
---

# Macro framework — regime first, trade second

The best macro traders don't predict. They identify the regime and position for what the regime rewards. When the regime changes, they change.

## The regime quadrant

Every moment sits in one of four regimes, defined by growth direction and inflation direction:

|                     | Growth up                  | Growth down                 |
|---------------------|----------------------------|-----------------------------|
| **Inflation up**    | Reflation — long commodities, long EM, short bonds | Stagflation — long gold, short equities, long curve |
| **Inflation down**  | Goldilocks — long equities, long bonds, long credit | Deflation — long long-end bonds, short equities, long USD |

Each regime has canonical winners and losers. The fund's positioning should reflect the current regime's playbook, not a blend. Druckenmiller: *"I don't like trading opposite sides of the same macro thesis."*

## The signals that mark a regime shift

- **Growth** — ISM PMIs (manufacturing + services), Conference Board LEI, retail sales, NFP revisions.
- **Inflation** — CPI (headline + core + supercore services), PCE, wage growth (ECI), breakevens.
- **Credit** — HY-IG spread, loan growth, banking-sector stress indicators.
- **Liquidity** — Fed balance sheet, TGA level, reverse repo, global central-bank net injection.
- **Positioning** — CFTC Commitments of Traders, equity put/call, VIX term structure.
- **Cross-asset** — DXY, 10Y TIPS real yield, gold/silver ratio, copper/gold ratio, XLY/XLP ratio.

A regime shift is identified by *multiple* signals flipping in the same direction. Don't trade off a single flip.

## Soros' reflexivity

Markets are not passive observers. A trend changes the fundamentals; the changed fundamentals reinforce the trend; until the feedback loop breaks. Trades exist at three points in a reflexive cycle:

1. **Early** — when the fundamentals have shifted but price hasn't confirmed. Highest edge, most uncertainty.
2. **Middle** — when fundamentals and price are reinforcing each other. Lower uncertainty, still good R:R.
3. **Late** — when the narrative is universally accepted and price has discounted far ahead of fundamentals. Lowest edge, often the best-feeling trade.

Druckenmiller said: *"If I can be the first guy in, my batting average is going to be higher, and my risk-reward is going to be much better."*

## The framework in practice

### Every Sunday the CIO / Index-Macro analyst updates `vault/regime/current.md`:

```yaml
---
date: YYYY-MM-DD
growth_direction: up | flat | down
inflation_direction: up | flat | down
regime: goldilocks | reflation | stagflation | deflation | transitional
confidence: low | med | high
next_check: YYYY-MM-DD
---
```

Evidence section: which signals point to the current read, which contradict, what would flip the regime.

### All analysts read the regime file on wake.

- If their proposed trade aligns with the regime → default-approve pathway.
- If their proposed trade fights the regime → requires explicit override rationale in the thesis; Risk Manager applies tighter sizing or blocks.

### The macro-flip check

A thesis that was right yesterday may be wrong today if the regime flipped. Analysts re-check their live theses against the weekly regime update; close or reduce those that no longer fit.

## Druckenmiller's three lessons

1. **Be a pig when you have the right setup.** Concentrate on high-conviction regime trades. Most years, a handful of trades make most of the return.
2. **Be humble about the rest.** When you don't have a strong regime read, run small or flat. Cash is a position.
3. **Sell before you want to.** The best macro trade is 80% done before the last 20% of its move. Don't try to catch the top tick.

## Louis Bacon's book-level approach

Bacon ran Moore Capital with a book-level view:
- No single bet is more than X% of equity.
- Correlated bets net, not gross.
- Liquidity of every position is known before entry (can I get out in 2 days at a known slippage?).
- Discipline > insight. The edge is execution, not IQ.

These principles are already in our risk framework — this playbook gives them their macro context.

## Hard don'ts

- Don't fight a clear regime on a hunch.
- Don't stack trades that are the same regime expression in different clothes (long ES + short TLT + long XLK + long DXY is one trade).
- Don't ignore cross-asset contradictions. If your equities thesis is risk-on but the curve is pricing a recession, something is wrong with one of the reads.
