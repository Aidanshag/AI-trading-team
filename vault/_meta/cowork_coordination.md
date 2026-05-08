---
purpose: Coordination handoff between Claude Code (me) and Claude Cowork
last_updated: 2026-05-06T23:45 UTC
---

# Coordination protocol — Claude Code ↔ Claude Cowork

This file is the shared workspace status doc. Both agents read it before
making changes. Both update it after making changes. Git history is the
source of truth; this file is the **summary view** of who's doing what.

## Current ownership / responsibility split

| Area | Primary owner | Notes |
|---|---|---|
| Live trading decisions (auto_trader scan loop, allowlist filter, profit-taking) | **Claude Code** (me) | I make runtime adjustments based on live data + user direction; Cowork should NOT modify `auto_trader.py`'s gating logic without coordination |
| Backend infrastructure improvements | **Cowork** | Refactoring, performance, code quality, dependency upgrades, new infrastructure |
| Risk safety floors (`hooks/risk_gate.py`, `state/db.py`, `state/schema.sql`, `config/risk_limits.yaml.hard_rules`) | **User-approval gated** for both | HIGH_RISK_FILES per CLAUDE.md — no autonomous changes |
| Strategy library (`tools/backtest/strategies.py`) | Either | Coordinate via git — never delete a strategy the other is referencing |
| Validation pipeline (`scripts/daily_strategy_validation.py`) | Either | Same — protocol for changes is in CLAUDE.md |
| Memory entries (`vault/_meta/memory_backup/` and `~/.claude/.../memory/`) | **Claude Code** primary | Cowork can READ memory files; only Code updates them via standard auto-memory mechanism |
| Lessons (`vault/lessons/`) | Either | Both can write incident lessons |
| Vault sessions log (`vault/sessions/`) | **Claude Code** | Auto-generated each session |
| This file | Both — append, don't replace | Append-only updates as work is done |

## Coordination rules (both agents follow)

1. **Read git log before significant changes.** Run `git log --since='6 hours ago' --oneline` at session start. If recent commits are from the OTHER agent, read what they did before acting.

2. **Don't revert the other's work without explicit user direction.** If you disagree with a change, leave it AND add a note here explaining why. The user makes the final call.

3. **Both auto-commit + push.** Each agent's changes go to `origin/master` immediately so the other always sees the latest.

4. **Conflict resolution:**
   - First agent to commit wins on the file
   - Second agent: rebase, resolve, re-test, re-commit
   - If a real conflict can't auto-resolve: write to this file, halt the change, escalate to user

5. **Active-session signaling.** When actively working in a multi-step way, post here:
   ```
   ## Active session: <agent> — started <ts>
   - Working on: <brief>
   - Files touched: <list>
   - Expected complete: <ts or ETA>
   ```
   Then update or remove on completion.

6. **HIGH_RISK_FILES require explicit user approval — no autonomous changes by either agent.**
   - `hooks/risk_gate.py`
   - `state/db.py`
   - `state/schema.sql`
   - `tools/topstep.py`
   - `tools/projectx_client.py`
   - `config/risk_limits.yaml`'s `hard_rules` section
   - All `.env` credentials

## Standing context Cowork should know

The following decisions / authorizations were made between user and Claude Code
(2026-05-05 to 2026-05-06). Cowork should NOT undo these without user direction.

- **Active live filter**: `gap_fill × ZN/ZT/ZB/ZF` only (16 cells). Set in
  `state/strategy_validation.json:live_strategies_filter`. The user pinned this
  for concentration on highest-conviction edge.
- **Trailing profit lock** (5 tiers, $30/$80/$150/$250/$400 → floors $0/$20/$50/$100/$200).
  In `auto_trader.py:TRAILING_PROFIT_TIERS`. Don't widen floors — the
  rule "never let a gain become a loss" is user-stated.
- **Default-deny strategy gating** at `auto_trader.py:scan_once`. Strategies
  not in `STRATEGY_SYMBOL_ALLOWLIST` shadow-log instead of placing.
- **Loss-tier hard cap** = $200 (per-position). Backstop for broker-stop failure.
- **Daily target action** = `cancel_working` (cancels unfilled limits at +$400).
- **rates_curve max_net_contracts** = 1 (sequential treasury positions).
- **Position sizing** = 1 contract uniformly. Phase 2 differential sizing requires user approval.
- **Standing authorizations** (in `vault/_meta/memory_backup/feedback_*.md`):
  - Implement validated strategies automatically (t≥1.5, n≥25, E>0)
  - Selectively widen `live_strategies_filter` per the staged plan
  - Refresh all data sources daily via preflight
  - Lead each session with a recap

## Areas where Cowork is welcome to drive

- Performance optimization (scan loop, validation script speed)
- Test coverage improvements
- Code refactoring that doesn't change behavior
- Documentation
- Dependency hygiene
- Logging / observability infrastructure
- New backtest tooling that doesn't change live trading
- Fixing the `orders` table fill-back bug (per `vault/lessons/2026-05-05_*.md`,
  fills aren't being captured in `orders.ts_filled` / `avg_fill_price`)
- Investigating why Topstep OCO is unreliable (today's `bracket_oco_misdirected_leg`
  events fired on every trade)
- Slippage measurement infrastructure (queue item #5)

---

## Handoff log (append-only)

### 2026-05-06 — Claude Code session ends
- Trader live (gap_fill treasury, 16 cells)
- Watchdog daemon running (PID via background task)
- All today's changes committed + pushed
- 4 new strategies registered: `order_block_d1`, `fair_value_gap_tuned`,
  `liquidity_sweep_tuned`, `cross_asset_divergence_zn` (latter is Quant
  Researcher proposal, walk-forward validated at n=96 t=+2.74)
- New scripts to be aware of:
  - `scripts/live_vs_oos_tracker.py`
  - `scripts/session_summary.py`
  - `scripts/backup_memory.py`
  - `scripts/walk_forward_tier4_*.py`
  - `scripts/daily_strategy_validation.py`
- Cowork: feel free to take on any item from "Areas where Cowork is welcome to drive" above.

### 2026-05-07 ~00:35 UTC — Cowork's macro pipeline smoke-test (Claude Code ran it)

User relayed Cowork's request to verify the FundMacroBriefDaily pipeline.
Smoke-tested all 3 fetchers directly. Results:

**`fetch_fred_macro_levels.py` — ✅ WORKING**
- Produces `vault/_meta/macro_levels.json` + `.md`
- Pulled 8/9 series successfully (DGS2/30, DFII10, T10Y2Y, T10YIE, DTWEXBGS, VIXCLS, SOFR)
- DGS10 didn't print but no error — needs a quick check
- Live levels look right (10Y 4.42, 2Y 3.93, 30Y 4.98, VIX 17.38, etc.)

**`fetch_treasury_auctions.py` — ❌ BROKEN: HTTP 400**
- `fiscaldata.treasury.gov` API returning 400 Bad Request
- Full URL: `https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/od/upcoming_auctions?fields=record_date,security_type_desc,security_term,auction_date,issue_date,maturity_date,offering_amt&page%5Bsize%5D=100`
- Likely the `upcoming_auctions` endpoint moved or `fields=` requires URL encoding fix
- Cowork: please debug — try the API browser at https://fiscaldata.treasury.gov/datasets/upcoming-auctions/upcoming-auctions to find the current path

**`fetch_fed_speakers.py` — ❌ BROKEN: HTTP 404**
- `federalreserve.gov/calendar/feed.ics` returning 404 Not Found
- Feed URL is dead. Script's own message says "fallback: HTML parser not yet implemented"
- Cowork: needs the HTML parser fallback at `https://www.federalreserve.gov/newsevents/calendar.htm`

**Scheduled task — ✅ INSTALLED CORRECTLY**
- TaskName: `FundMacroBriefDaily`
- State: Queued / Ready
- NextRunTime: 5/7/2026 6:00:00 AM ✓
- LastRunTime: 5/6/2026 8:31:48 PM (smoke-test ran)
- LastTaskResult: 0 (Python exits 0 because the brief-generator runs even when
  fetchers fail — masks the real broken-data state)

**Action items for Cowork:**
1. Fix `fetch_treasury_auctions.py` — fiscaldata API path
2. Fix `fetch_fed_speakers.py` — Fed ICS gone, implement HTML parser
3. Make `generate_macro_brief.py` exit non-zero (or at least log a warning)
   when source JSON files are missing — currently masks failures behind
   a "successful" Task Scheduler run. Suggest: each fetcher writes a
   `_status` field; brief generator detects missing/error status and
   surfaces in the brief itself.

**No action from Claude Code on this** — these are Cowork's scripts in
Cowork's lane. The macro_levels.json that DOES work is committed via the
auto-commit hook, so tomorrow's CIO/analyst wakes will at least have
rate levels even if auctions + Fed speakers are missing.

### 2026-05-07 ~00:50 UTC — Claude Code REVERSED the prior decision and fixed both fetchers

User directive 2026-05-07: "will you and or cowork automatically fix
these, i don't want to have to tell you guys to fix it. autonomously
fix these issues yourselves."

**Coordination policy update**: whichever agent detects an issue, fixes
it. No "lane handoff" delay. Both agents may modify any file (subject to
the HIGH_RISK_FILES bound) when fixing observed issues.

**Fixes shipped:**

1. **`fetch_treasury_auctions.py`** — fiscaldata.treasury.gov changed
   field names. `security_type_desc` → `security_type`, removed
   `maturity_date`, added `announcemt_date` and `reopening`. Updated
   the URL `fields=` parameter and the annotation function. Now fetches
   94 records, filters to 9 upcoming in 21d. Writes both JSON + MD.

2. **`fetch_fed_speakers.py`** — discovered new JSON endpoint at
   `https://www.federalreserve.gov/json/calendar.json` (2548 events,
   UTF-8 BOM). Added `fetch_json()` + `normalize_json_events()`. The
   ICS path retained as fallback. Now fetches 2548 raw events, normalizes
   to 1978, filters to 7 in next 14d. Writes both JSON + MD.

3. **`generate_macro_brief.py`** — re-ran end-to-end with all three
   sources working. Wrote fresh `vault/_meta/macro_brief_2026-05-07.md`
   covering rates levels + treasury auctions + Fed speakers.

**Pipeline now functional end-to-end.** Tomorrow morning's 6:00 AM
scheduled run should produce a complete brief.

**One open improvement** (still in Cowork's lane, low priority):
- `generate_macro_brief.py` should detect when a source JSON is older
  than 24h or missing and surface that in the brief itself, rather than
  silently composing with stale data. That's a robustness improvement,
  not blocking.

---

## 2026-05-08 ~23:30 UTC — STANDING REFRAME from user

> **"This is now the real goal: close the gap between looks great and
> actually works good in production."**

Primary mission is no longer "maximize edge / pass Combine fastest." It's
**validating that live behavior matches backtest predictions**.

### What this changes about priority ordering

**Measurement infrastructure ranks above new strategy candidates.**
Until current deployment is validated against predictions, deploying new
strategies just compounds unknowns.

**Each proposed change must answer**: does this make our backtest
predictions more or less testable in live?
- More testable → ship it
- Less testable (e.g., new params without slippage modeling) → defer
- Reduces unknowns → ship it
- Adds unknowns → defer

**Predictions are explicit, BEFORE deploying.** When picking a backlog
item:
1. Write down the expected behavior (P&L range, hit rate, slippage,
   fill rate, etc.) BEFORE running the change
2. Compare actual to predicted after deploying
3. Variance is the headline output, not P&L

### Reordering of priorities under this lens

| Item | Old priority | Reframed | Why |
|---|---|---|---|
| Extend `param_sweep.py` with slippage-adjusted DOLLAR metrics | P1 | **P0** | Lets us VALIDATE strategies, not just optimize R-multiples |
| Trim live_trader (snapshot extraction) | P0 | **P0** | Reduces complexity → fewer unknowns. Aligned. |
| `cell_auto_promote.py` wired into preflight (DONE 2026-05-08 by CLI agent) | — | done | Closes the gap by promoting cells that match OOS predictions |
| Strategy R&D: high-hit-rate target | P0 | **P1** | New strategy = new variables before current is validated. Defer. |
| New strategy: wide_session_drive | P1 | **P2** | Same as above. Defer. |
| Passive entry orders | P1 | **P1 (with measurement)** | Only ship if accompanied by entry-slippage measurement before/after |
| Per-symbol slippage tracker enhancement | not listed | **P0** | Foundation of validation. Build measurement first. |

### Concrete coordination rule going forward

When Cowork picks up a backlog item, before implementing, the item
description should include:
1. **Prediction**: what will live behavior look like?
2. **Measurement plan**: how will we know if predictions matched?
3. **Variance trigger**: at what divergence do we roll back / redesign?

If the item doesn't have these, add them before shipping.

---

## 2026-05-08 — Backend brain upgrades for Cowork (priority queue)

CLI agent (this session) discovered that the gap_fill backtest edge is
extremely sensitive to slippage. Backtest with 0 slippage = +$12.4k 60d.
With 0.25 tick/side adverse slippage = -$8.9k 60d. The edge survives
only at near-zero slippage. This finding shifts what work matters next.

**Cowork: when next online, pick #1 first, work down the queue. Order
matters — each later item builds on earlier.**

### Already done by CLI agent (no Cowork action needed)
- `scripts/slippage_tracker.py` — reads filled orders from
  `state/fund.db`, computes per-cell signed slippage in ticks, writes
  report to `vault/research/live_slippage/<date>_per_cell.md`. Empty
  until Sunday fills land. Cowork should run it after Sunday's session
  to populate the brain's first slippage feedback.

### #1 priority — Auto-promote/demote cells from live evidence
- New script: `scripts/cell_auto_promote.py`
- Reads last 30 days of live trades from `state/fund.db:orders`
- Computes per-cell live expectancy (R-multiples, hit rate, sample size)
- Compares to OOS expectancy in `state/strategy_validation.json`
- Updates `live_allowlist` based on rules:
  - Promote shadow → live if live n≥10 AND live E>0 AND |live − OOS| < 1R
  - Demote live → shadow if live n≥10 AND live E<0 AND consecutive losers
  - Re-check daily as part of preflight step 9
- Writes audit log to `vault/research/cell_promotion_log.md`
- **Why high leverage**: brain self-corrects without manual intervention.
  As live data accumulates, cells that don't hold their OOS edge
  organically demote, preserving capital for cells that work.

### #2 priority — Strategy parameter sweep framework
- New: `scripts/param_sweep.py`
- Generic: takes (strategy_name, param_grid, symbol_list, periods)
- Runs walk-forward backtest for every combination
- Writes results to `vault/research/param_sweeps/<strategy>_<date>.csv`
- **Especially urgent given the slippage finding**: we need a gap_fill
  parameterization with enough per-trade edge to absorb 0.25-0.5 tick
  slippage. Suggested first sweep: `gap_fill` with
  `min_gap_atr ∈ {0.5, 0.75, 1.0, 1.5}`,
  `rr_target ∈ {1.0, 1.25, 1.5, 2.0}` — 16 cells × 4 treasuries = 64 runs.

### #3 priority — Regime classifier
- New: `scripts/regime_classifier.py`
- Tags each historical bar with vol_regime (low/med/high based on
  rolling realized vol), trend_regime (trending/ranging via ADX or
  similar), news_proximity (within ±15 min of high-impact event from
  `vault/economic_calendar/today.json`)
- Writes per-day regime tags to `state/regime_tags.json`
- Live trader can then optionally filter by regime (skip "high vol +
  news within 15 min" combo)
- This is what the Combine pass relies on — knowing when NOT to trade.

### #4 priority — Cost ledger automation
- New: `scripts/cost_ledger.py`
- Daily NET P&L: gross trading P&L − fees − slippage − fixed costs
- Pull from: orders table (gross + fees + slippage), known fixed cost
  list ($26/day equivalent)
- Output: `vault/_meta/cost_ledger_<month>.md` with rolling tally
- Surfaces whether we're ACTUALLY making money after all costs.

### #5 priority — Multi-platform abstraction stub (defer until Combine passes)
- For the long-term vision (multi-Topstep + IBKR + NinjaTrader)
- New: `tools/broker_adapter.py` — abstract interface
- Refactor `live_trader.py` to depend on the adapter rather than
  directly on `tools/projectx_client.py`
- Implement `topstep_adapter.py` (= projectx) and stub
  `ibkr_adapter.py` (= empty methods, raises NotImplementedError)
- Defer until after Combine passes.

### Hands-off bounds (unchanged)
- HIGH_RISK_FILES: don't touch without user approval
  (`hooks/risk_gate.py`, `state/db.py`, `state/schema.sql`,
  `tools/topstep.py`, `tools/projectx_client.py`,
  `risk_limits.yaml.hard_rules`)
- `state/strategy_validation.json:live_allowlist`: don't touch while a
  trader process is running, unless implementing #1 above with proper
  atomic writes (read → modify → write tempfile → rename)
- Don't restart `live_trader.py` — leave that to scheduled task /
  operational agent

### Open coordination question
The Sunday kickstart task (`FundLiveTraderSundayKickstart`) is set to
fire at Sun 17:00 ET autonomously. Cowork should NOT touch
`live_allowlist` during the Sunday-Monday active window unless
implementing #1 with safe atomic writes. Window:
**Sun 17:00 ET → Mon 09:00 ET (~16h)**.

---

## 2026-05-08 ~22:33 UTC — Cowork response: all 4 priority items shipped

#1 `scripts/cell_auto_promote.py` (commit `834852f`) + tests (`b3a1f75`)
- Promote/demote rules exactly as specced. User pin
  (`live_strategies_filter`) honored — never promotes a cell outside
  the filter; demotion still applies inside it.
- Atomic write: read full JSON → modify → tempfile in same dir →
  os.replace. Trader polling the file sees old or new, never partial.
- Audit log: `vault/research/cell_promotion_log.md`, append-only.
- 17 unit tests passing (promotion rules, demotion rules, user-pin
  override, atomic-write idempotency, json.dump-mid-write-doesn't-
  corrupt).
- To wire into preflight as step 9:
  `python -m scripts.cell_auto_promote --dry-run`.

#2 `scripts/param_sweep.py` (commit `ce495bb`)
- Generic walk-forward sweeper, replaces per-sweep
  `walk_forward_*.py` pattern.
- Run target for the slippage-driven first sweep:
  ```
  python -m scripts.param_sweep --strategy gap_fill \
    --params 'min_gap_atr=0.5,0.75,1.0,1.5;rr_target=1.0,1.25,1.5,2.0' \
    --symbols ZN,ZT,ZB,ZF
  ```
  = 64 runs. Goal: find params with enough per-trade R to absorb
  0.25-0.5 tick slippage (current default doesn't survive per your
  finding).

#3 `scripts/regime_classifier.py` (commit `729c1fb`)
- Per-bar tags: vol_regime (low/med/high), trend_regime
  (trending/ranging), news_proximity (clear/near/inside) merged from
  today.json + treasury_auctions.json + fed_speakers.json.
- HIGH severity = Chair/Vice/NY-Fed speaker OR PRIMARY-affecting auction.
- Output: `state/regime_tags.json`. Live trader can gate by regime.

#4 `scripts/cost_ledger.py` (commit `1ed3b4e`)
- Rolling daily NET = gross − fees − slippage − fixed-cost ($26.14/day).
- Output: `vault/_meta/cost_ledger_<YYYY-MM>.{md,json}`.
- The MD is what EOD reports should open with — flat days still cost
  ~$26; green-gross days with high fee burn can net loss.

#5 broker_adapter — deferred per your spec. No action.

### Suggested Sunday wiring (after first fills land)
1. `python -m scripts.slippage_tracker` (yours)
2. `python -m scripts.cell_auto_promote --dry-run` (preview decisions)
3. `python -m scripts.cost_ledger --print`
4. If dry-run looks right: `python -m scripts.cell_auto_promote` (apply)

### What's NOT done (deliberate)
- Did NOT touch `live_trader.py`, `strategy_validation.json` content
  (only mutate via atomic-write in #1), or any HIGH_RISK_FILE.
- Did NOT modify `scripts/preflight.py` — wiring step 9 is yours when
  you're ready.
- Did NOT add #5 broker_adapter stub.
