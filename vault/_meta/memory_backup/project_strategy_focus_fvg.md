---
name: Strategic focus — Price-action strategies (FVG primary)
description: 2026-05-04 directive — Price-action strategies are the fund's primary focus. FVG specifically is the lead strategy. Classical TA (Bollinger, RSI, ORB, etc.) demoted to support role.
type: project
originSessionId: b1c69b67-a794-46cc-bb06-6e08fbeea607
---
On 2026-05-04 the user designated **price-action strategies as the fund's primary focus**, with **Fair Value Gap (FVG)** as the lead strategy. Origin: a personal friend of the user's runs FVG as his primary strategy with "immense success." User then broadened the mandate to "price action strategies" generally.

**Hierarchy:**
1. **Primary**: FVG (Fair Value Gap) — 3-candle imbalance, mitigation entry
2. **Secondary supports** (price-action family):
   - Order blocks (last opposite candle before strong displacement)
   - Liquidity sweeps (stop-hunt fade after price spikes through prior high/low)
   - Break of structure (BOS) / change of character (CHoCH)
   - Premium/discount zones, imbalances
3. **Demoted to backstop only** (classical TA): Bollinger, RSI2, ORB, donchian, keltner, vwap_reversion, etc. Still in the roster, but lower conviction by default and only fire if no price-action setup is active.

**Why this matters:**
- Price-action strategies are pattern-based math derived from price alone — they work natively 24/5 (the same date the user opened gates to after-hours).
- Classical TA strategies need volume/range conditions that thin out overnight.
- Friend's anecdotal FVG success is hearsay, not validated edge — but the user has given it strategic weight.

**How to apply:**
- When proposing strategy work, default to price-action additions over classical-TA tweaks.
- The `STRATEGY_ROSTER` in `scripts/auto_trader.py` lists price-action strategies first; do not reorder without explicit approval.
- Literature priors in `tools/strategy_performance.py` give price-action strategies medium-to-high expectancy priors.
- Auto-demote rule (5 consecutive losers → benched) applies equally — even FVG can get benched if it underperforms on real data. Empirical performance reshapes weights once n>=20 trades.
- If user asks to disable or remove a price-action strategy without context, push back and confirm — that's a meaningful direction change, not a routine config edit.
