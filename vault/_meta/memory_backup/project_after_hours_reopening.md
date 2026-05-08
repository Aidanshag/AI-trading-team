---
name: 24/5 trading reopened for diagnostic visibility
description: 2026-05-04 — autonomous RTH-only gate AND thin-tape regime gate both disabled. Trader can fire any hour the broker is open. Hard floors (DLL/TDD/ladder) remain.
type: project
originSessionId: b1c69b67-a794-46cc-bb06-6e08fbeea607
---
On 2026-05-04 the user directed me to "open trading to allow for after hours" so live trades could be observed for diagnostic purposes. Two gates were turned off:

- `config/fund.yaml` → `autonomous_restrictions.rth_only: false` (was `true`, window 07:30-15:30 ET)
- `config/risk_limits.yaml` → `regime_gates.thin_tape.enabled: false` (was `true`, window 21:00-04:00 ET)

**Why:** the 2026-05-04 morning session burned a full day with zero trades because Windows force-rebooted at 07:10 ET. Combined with the RTH-only gate, the trader had a tiny window even on healthy days. User wants maximum trade surface area to surface diagnostic data — NET combine target hasn't moved in 5 days at -$1,048.68.

**How to apply:**
- The original `rth_only` gate was added 2026-04-29 specifically because of an overnight thin-tape DLL breach. If the trader starts bleeding overnight again, re-enable BOTH gates. Don't just flip one.
- Hard safety floors that stay active 24/5: DLL ($1,000), TDD ($2,000), defensive ladder (-$150/-$300/-$500), daily target lock (+$200/+$400 + 40% giveback), kill switch, halt timestamp, stop-required, per-trade $250 cap, fee budget.
- CME futures daily maintenance pauses are per-symbol (e.g., MES/ES 16:15-17:00 ET). Broker rejects orders during these as "instrument not in active trading status". Risk gate doesn't catch this — observed 2026-05-04 16:39 ET on MES. Future improvement: add a per-symbol session_window check.
- The user is also pushing for more micro-structure / mathematical strategies (FVG, order blocks, liquidity sweeps) over macro-data-dependent setups, since those work natively 24/5.
