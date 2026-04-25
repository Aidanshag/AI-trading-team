---
type: index
---

# Equities shadow-trade ledger

Same format and integrity rules as the [futures shadow-trade ledger](../../futures/shadow_trades/README.md). The equities desk uses shadow trades to calibrate pre-go-live; every analyst's shadow trades are scored against actual price action every weekend.

## Entry format

```yaml
---
type: shadow_trade
symbol: AAPL
side: buy | buy_to_open_call | iron_condor_open | ...
qty: shares or contracts
entry_assumption: price at publish mid
stop: price
target: price
risk_usd: computed
reward_to_risk: computed
analyst: Growth/Tech Analyst | Defensive | Cyclicals | Financials | Single-Name Options
thesis: vault/equities/theses/AAPL.md
structure_kind: (if options)
rationale: one-line
expected_hold: days or weeks
---
```

## Integrity rules

- No back-fitting. Entry/stop/target locked at publish.
- Options slippage: one tick worse than mid on each leg.
- Stock slippage: $0.02 per share on market orders; $0.01 per share on limits (realistic retail-size assumption).
- Track outcome honestly. Stopped out then would-have-worked = stopped out.

## Why

Pre-go-live, this is how the equity analysts build an honest baseline of their own hit rates. Post-go-live, the shadow ledger stays active for new-pattern testing before real-money deployment.
