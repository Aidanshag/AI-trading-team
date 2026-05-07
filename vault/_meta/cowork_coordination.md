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
