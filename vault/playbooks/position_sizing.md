---
type: playbook
applies_to: [portfolio_manager, equity_pm, risk_manager, all_analysts]
source: Kelly criterion, vol targeting, Tudor Jones/Druckenmiller practice, RenTech-style risk budgeting
---

# Position sizing — the only thing you control

## The hierarchy

Three sizing frameworks, from simplest to most disciplined. Use the tightest one that's realistic given your data:

1. **Fixed fractional** — risk X% of equity per trade. Simple, robust, boring. Default.
2. **Vol-targeted** — size inversely to the instrument's recent volatility so every trade carries the same $-risk. Slightly better than fixed fractional when ATR varies across symbols.
3. **Fractional Kelly** — size by edge × odds, but cap at 0.25× full Kelly (never more). Requires an honest estimate of edge.

This fund uses **vol-targeted** sizing by default, with a fractional-Kelly overlay for high-conviction ideas.

## The math you need

### Per-trade risk in USD

```
risk_usd = entry_price - stop_price * contracts * tick_value_per_tick_distance
```

Simplified: *(stop distance in ticks) × (tick value) × (contracts) = $-risk*.

Example: Long /MCL at 78.40, stop 77.90. Distance = 50 ticks. Tick value = $1.00. One contract = $50 risk.

### Position sizing from a risk budget

```
contracts = floor( risk_budget_usd / (stop_distance_ticks * tick_value) )
```

If the result rounds down to zero, the trade is too rich for the stop — widen the stop (more ATR room) or pass.

### Fractional Kelly

```
f* = edge_per_trade / odds  (simplified, for binary outcomes)
```

Where *edge* is your honest long-run expectancy per $1 risked. Cap at **f* × 0.25**. "Full Kelly" is the path to blow-up — the log-optimal sizing is far larger than what you should run in real life because of (a) estimation error in edge, (b) fat tails, (c) psychological drawdown tolerance.

## Conviction multipliers (how the fund actually sizes)

Base budget = 0.5% of equity per trade. Scale by conviction:

| Conviction | Multiplier | Risk as % of equity |
|---|---|---|
| low    | 0.25× | 12.5 bps |
| med    | 0.5×  | 25 bps |
| high   | 1.0×  | 50 bps (cap) |

Never go above 50 bps per trade. Even the most brilliant idea does not justify more — the edge estimate is almost certainly biased upward.

## Pyramiding (scaling in on winners)

Paul Tudor Jones' rule: *"Add to winners, never to losers."*

- Permitted only on trades already in profit by at least 1R.
- Each add is half the original size.
- Each add carries the trade's original stop or a tighter trailing stop.
- Maximum three adds per trade.
- Pyramiding a loser is explicitly forbidden.

## The anti-patterns that destroy accounts

- **Martingale** — doubling after a loss. Guarantees ruin over enough trials.
- **Revenge sizing** — bigger after a loss to "get it back." Destroys discipline.
- **Averaging down** — adding to losers "because it's cheaper." Adds risk at the worst time.
- **Stop-widening** — "I'll just give it more room." Nothing ruins more accounts than moving a stop against the position.
- **All-in-on-one-signal** — concentration without edge-verification. If you don't have hit-rate data on this exact setup, full-size is gambling.

## The weekly calibration

Every Sunday, review: were your stops realistic? Did you size correctly for conviction? Did you pyramid where the rules allowed? Did you violate the rules anywhere? Log findings to `vault/reviews/weekly_sizing_review.md`.

## For the fund specifically

- `config/risk_limits.yaml:account.per_trade_risk_pct_of_equity` = 0.005 (50 bps) — the hard cap.
- PM computes position size using the stop distance from the analyst's thesis. If rounding drops contracts to zero, PM rejects the proposal and returns to analyst for a wider-stop revision.
- Risk Manager verifies the sizing math independently before approving.
