---
type: meta
period: 2026-04-25 through 2026-04-27
status: active
last_session_end: 2026-04-25T05:30:00+00:00
---

# Weekend autonomous work plan

## ⚡ RESUME HERE (read first when picking up)

If you are Claude resuming this session — or after a 5-hour limit reset:

**Last completed**: P0 risk hook tests (22/22 passing), `scripts/sunday-open.ps1`, `scripts/_cost_summary.py`. Trading halted via `risk_limits.yaml:hard_rules.trading_halted: true` for safety during autonomous weekend run.

**Next item to work** (top of P1):
1. Implement EIA-surprise event-driven backtest end-to-end in `tools/backtest/event_strategies.py`. The strategy stub already exists — wire it to actually pull EIA crude-stocks data (use cached test data first; live FRED/EIA keys later).
2. Then `tools/regime_classifier.py` — ingest FRED series, output regime quadrant. Cached test data path; works without live key.
3. Then product deep-dives (P1 list below).

**Sign-off ritual after each completion**: append to today's `vault/journal/<date>.md` under `## Autonomous wake — HH:MM UTC` with item completed, file path, git commit hash, tokens spent, next item.

**Cost discipline**: Haiku unless task demands Sonnet. Cap output 5000 tokens/wake. Cache aggressively.

**Stop conditions**: if you've completed all P0 + P1 + at least 8 product deep-dives, stop and let user review Monday.

---

# Full task queue

Prioritized task queue for autonomous Claude self-loop wakes AND Fund Engineer idle wakes through the weekend. Each wake picks one item, finishes or partial-finishes, commits to git, signs off in journal.

## P0 — safety + frictionless return

- [x] Pytest tests for `hooks/risk_gate.py` — every rule (naked short, DLL, stop required, defensive ladder, per-symbol caps, sector caps). File: `tests/test_risk_gate.py`. **22/22 passing.**
- [x] `scripts/sunday-open.ps1` — one-command preflight: verify → connect → cost summary → CIO test wake.
- [x] `scripts/_cost_summary.py` — month-to-date spend by agent + model.
- [x] `risk_limits.yaml:trading_halted: true` — safety lock during autonomous weekend run. **User must set to false before Monday's first supervised session.**

## P1 — capability unlock

- [ ] Implement EIA-surprise event-driven backtest end-to-end. Use cached weekly stocks data; live FRED/EIA keys later.
- [ ] `tools/regime_classifier.py` — ingest FRED series, output regime quadrant (goldilocks/reflation/stagflation/deflation). Works with cached test data.
- [ ] `tools/options_pricing.py` — Black-Scholes + Greeks. No external dependency.
- [ ] Wire OptionsRisk to call `tools/options_pricing.compute_greeks` when reviewing options proposals.

## P1 — content depth (Fund Engineer territory mostly)

- [ ] Product deep-dive: `NG.md` (Natural Gas)
- [ ] Product deep-dive: `RB.md` (RBOB Gasoline)
- [ ] Product deep-dive: `HO.md` (NY ULSD / Diesel)
- [ ] Product deep-dive: `BZ.md` (Brent)
- [ ] Product deep-dive: `SI.md` (Silver)
- [ ] Product deep-dive: `HG.md` (Copper)
- [ ] Product deep-dive: `PA.md` (Palladium)
- [ ] Product deep-dive: `ZS.md` (Soybeans)
- [ ] Product deep-dive: `ZW.md` (Wheat)
- [ ] Product deep-dive: `ZL.md` (Soybean Oil)
- [ ] Product deep-dive: `ZM.md` (Soybean Meal)
- [ ] Product deep-dive: `KC.md` (Coffee)
- [ ] Product deep-dive: `CT.md` (Cotton)
- [ ] Product deep-dive: `SB.md` (Sugar)
- [ ] Product deep-dive: `LE.md` (Live Cattle)
- [ ] Product deep-dive: `GF.md` (Feeder Cattle)
- [ ] Product deep-dive: `HE.md` (Lean Hogs)

## P2 — playbook expansion

- [ ] `vault/playbooks/treasury_auctions.md` — concession, takedown, post-auction setups
- [ ] `vault/playbooks/jolts_data.md` — JOLTS report reaction
- [ ] `vault/playbooks/ecb_thursday.md` — ECB rate decision day
- [ ] `vault/playbooks/boc_boe_aud_decisions.md` — secondary central bank days
- [ ] `vault/playbooks/curve_trades.md` — DV01-weighted curve spreads
- [ ] `vault/playbooks/seasonality_grains.md` — March/June reports + planting calendar

## P2 — code quality

- [ ] Refactor `runtime/orchestrator.py` — extract analyst-chain logic to `runtime/analyst_chain.py`
- [ ] Add type stubs / mypy config
- [ ] Add docstrings to every public function in `tools/projectx_client.py`

## P3 — operational polish

- [ ] Cleanup `.claude/settings.local.json` — collapse auto-appended specific entries (broad rules cover them)
- [ ] Add troubleshooting guide: `vault/_meta/troubleshooting.md`
- [ ] Document Black-Scholes assumptions used by options pricing tool

## Cost discipline (this is overnight)

- Stick to Haiku unless a task explicitly demands Sonnet (refactoring large files, writing test scaffolding)
- Cap output at 5000 tokens per wake unless needed
- Use prompt caching aggressively (system prompt + this plan file + recent journal)
- One item per wake; partial-finish is OK if budget tight

## Sign-off ritual

End every wake with a journal append:

```
## Autonomous wake — HH:MM UTC
Item completed: <title>
File written:   <path>
Git commit:     <short hash + message>
Tokens spent:   <input/output>
Next item:      <one-line>
```
