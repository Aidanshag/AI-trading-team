---
type: index
---

# Shadow-trade ledger

Shadow trades are proposed-but-not-executed trades. During the Topstep setup window (no broker yet), every PM-sized proposal becomes a shadow trade. After go-live, shadow trades are still used for: learning-only regimes, experimental patterns, and out-of-sample testing of new playbooks.

## Files

- `YYYY-MM-DD.md` — the day's shadow trades, one block per trade.
- `_ledger.md` — rolling ledger across all days (auto-updated by PM at session close). Tracks cumulative imaginary P&L, hit rate, average R-multiple, and which analyst generated which trades.

## Entry format (in a daily file)

```yaml
---
type: shadow_trade
symbol: CL
side: long
qty: 1
entry_assumption: 78.40
stop: 77.90
target: 79.80
risk_usd: 500
reward_to_risk: 2.8
analyst: Energies Analyst
thesis: vault/theses/CL.md
rationale: one-line
expected_hold: intraday | multi-day
---
```

Body:

- **Entry-time notes**: what the tape looks like, why now.
- **Outcome** (filled in after): hit stop? hit target? closed for other reason?
- **Outcome notes**: what we learned.

## Integrity rules

- **No back-fitting.** Once a shadow trade is entered, its entry, stop, and target do not move — ever. You can close early for a reason, but you cannot re-write history.
- **Honest slippage.** Entry assumptions use mid-price at time of publish. Fill assumes worst-of-mid-or-bid for buys, worst-of-mid-or-ask for sells.
- **Track the counterfactual honestly.** If a stop is hit intraday and then the trade would have made money by close, it's still a stopped-out loser.

## Why this matters

When the fund goes live, there's no substitute for a calibrated sense of your own setups' hit rates. Shadow trading during the setup window is the only way to have that data on Day 1 instead of Month 6.
