---
type: playbook
applies_to: [risk_manager, cio, portfolio_manager]
updated: 2026-04-25
---

# Book State Playbook — Risk Manager Action Matrix

Hard-coded risk management rules for five trading regimes. This is not advisory.

## STATE 1: GREEN 1 Flat to +5 percent
Account profitable, normal operations.
- Position caps: Full (per config)
- Entry filters: Standard thesis-driven
- Stops: 2-4R asymmetry
- New entries: Yes, unlimited

## STATE 2: GREEN 2 +5 to +20 percent
Strong day, overconfidence risk.
- Position caps: Reduce 25 percent
- Entry filters: Require macro catalyst
- Stops: Tighten by 0.5 ATR
- New entries: 50 percent normal size

## STATE 3: YELLOW Early Drawdown 0 to -5 percent
Fund bleeding. Stop it, debug thesis.
- Position caps: Reduce 50 percent
- Entry filters: No new longs
- Stops: 1.5R max
- New entries: 25 percent normal
- Exits: Close losses, hold winners

## STATE 4: ORANGE Significant Drawdown -5 to -10 percent
Lost 5-10 percent, risk pods trigger.
- Position caps: 25 percent of Green 1
- Entry filters: Zero new entries
- Stops: 1R or exit on adverse tick
- Forced exits: Close all losses and breakevens
- Winners: Exit half if +2R, exit all if less

## STATE 5: RED Crisis Below -10 percent
Halt all trading. Close all positions at market immediately.

## DLL State Table
Green 1: 100 percent DLL, 50 bps per trade, Yes entries
Green 2: 100 percent DLL, 50 bps per trade, Filtered entries
Yellow: 50 percent DLL, 30 bps per trade, No entries
Orange: 25 percent DLL, 15 bps per trade, No entries
Red: 0 percent DLL, N/A, No entries

## Sign-Off
Risk Manager, every day, check: What state are we in? Execute the rules for that state.

The fund survives because risk management is hard-coded, not negotiated.
