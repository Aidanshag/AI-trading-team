---
type: reference
status: ACTIVE
purpose: Canonical data-model spec for the two-broker world (Topstep + IB). Every artifact carries a `broker` field. Cross-broker contamination is forbidden.
created: 2026-05-17
---

# Data model — broker-isolated artifacts

The fund operates two parallel broker workstreams (Topstep and IB) that share **strategies/research/knowledge** but NOT **execution/risk/state**. This document is the canonical reference for how that isolation is enforced in the data layer.

> Why this matters: when IB eventually has a live trader, the system must route every signal, order, fill, and position to the correct broker without ambiguity. The cheapest way to guarantee that is to tag every artifact with a `broker` field at the moment of creation, and enforce its presence via the separation audit.

## The `broker` field

Every persistence artifact below carries a `broker` field with one of two values:

| Value | Meaning |
|---|---|
| `"topstep"` | Topstep / ProjectX path (futures, Combine rules, prop capital) |
| `"ib"` | Interactive Brokers path (equities, options, futures, personal capital) |

Future brokers (if any) get their own short identifier. There is no `"shared"` value — every concrete signal/trade/order belongs to exactly one broker.

## Artifacts carrying `broker`

### Live allowlist (`state/strategy_validation.json:live_allowlist`)

Each cell entry includes `broker`. Example:

```json
{
  "symbol": "MNQ",
  "strategy": "fair_value_gap",
  "session": "Asian",
  "side": "long",
  "broker": "topstep",
  ...
}
```

- All 35 cells as of 2026-05-17 are `broker: "topstep"`.
- An IB cell (when one exists) appears in the same file but with `broker: "ib"`. The IB trader (when built) reads only `broker: "ib"` cells; the Topstep trader reads only `broker: "topstep"` cells. They literally cannot fire each other's cells.

### `shadow_trades` table (`state/fund.db`)

`broker TEXT NOT NULL DEFAULT 'topstep'` — added via runtime ALTER TABLE on 2026-05-17.

### Other state tables also carry `broker`

For consistency, every workstream-scoped table received the column:
- `orders`
- `positions`
- `account_snapshots`
- `decisions`
- `risk_events`
- `daily_pl`

All default to `'topstep'` (so existing rows are correctly attributed). Tables that are genuinely cross-broker (e.g. `costs`, `news_items`) do not need it.

## Code-layer isolation

| Concern | Topstep | IB |
|---|---|---|
| Trader script | `scripts/live_trader.py` | (not yet built) `scripts/ib_trader.py` |
| Brain signaler | `scripts/brain_signaler.py` | (eventually a shared signaler that emits broker-tagged signals) |
| Broker client | `tools/projectx_client.py`, `tools/topstep.py` | `tools/ib_client.py` |
| Strategy registry | `tools/backtest/strategies.py:STRATEGY_REGISTRY` (shared) | `tools/backtest/ib_strategies.py:IB_STRATEGY_REGISTRY` (IB-only) |
| Risk hook | `hooks/risk_gate.py` (Topstep rules) | (eventually separate IB risk module) |
| Risk config | `config/risk_limits.yaml` | (eventually separate `config/ib_risk_limits.yaml`) |

### Cross-import rules

- `scripts/live_trader.py` and `scripts/brain_signaler.py` must NEVER import `tools.ib_client` or `tools.backtest.ib_strategies`.
- Any future `scripts/ib_trader.py` must NEVER import `tools.projectx_client`, `tools.topstep`, `scripts.live_trader`, `hooks.risk_gate`.
- The `tools/separation_audit.py` check fails loudly on violations.

## Vault structure

| Path | Purpose |
|---|---|
| `vault/futures/` | Topstep-only knowledge (Combine rules, futures playbooks, futures journal) |
| `vault/ib/` | IB-only knowledge (data pulls, equity/options strategies, IB journal) |
| `vault/_meta/`, `vault/principles/`, `vault/lessons/`, `vault/research/` | Shared cross-broker knowledge |
| `vault/sessions/` | Shared (claude session summaries) |

## The audit

`python -m tools.separation_audit` runs the following checks and exits non-zero on any violation:

1. Every `live_allowlist` cell has a `broker` field with value `"topstep"` or `"ib"`.
2. Every `shadow_trades` row has a non-null `broker`.
3. Topstep scripts don't import IB-only modules; IB scripts don't import Topstep-only modules.
4. No equity ticker (SPY/QQQ/AAPL/...) appears in `broker: "topstep"` allowlist (Topstep is futures-only).

The audit is part of `scripts/preflight.py` and the weekly audit (`vault/_meta/weekly_audit.md`). It also runs in the `/improve-fund` cycle so any code change that breaks the boundary is caught before merge.

## When adding a new broker (future)

1. Pick a short identifier (e.g. `"alpaca"`)
2. Add it to the valid-brokers set in `tools/separation_audit.py`
3. Create `vault/<broker>/` with its own README following the IB pattern
4. Create `scripts/<broker>_trader.py` and `tools/<broker>_client.py`
5. Tag any new allowlist cells with the new broker value
6. Run `python -m tools.separation_audit` to verify clean isolation

## Anti-patterns (these are bugs)

- A signal in code without a `broker` field — fix: add it before emission
- A cross-broker import (Topstep importing IB or vice versa) — fix: move shared logic to `tools/backtest/` or `vault/research/`
- A shadow trade without `broker` — fix: backfill the column, then make the writer set it explicitly
- Manually editing a Topstep cell to `broker: "ib"` to "move it to IB" — fix: don't do that; create a new IB cell and validate independently. Strategies that work on futures may need recalibration on equities.

## Related

- [[feedback-topstep-vs-ib-separate-workstreams]] — user directive establishing the separation
- `vault/ib/README.md` — IB workstream root
- `tools/separation_audit.py` — the enforcement check
- `state/schema.sql` — TODO: canonicalize broker columns (added at runtime 2026-05-17)
