---
name: Two-layer architecture — Brain (research) separate from Knife (execution)
description: User authorized 2026-05-07 a strategic two-layer split. Build minimum viable execution NOW for cash flow; preserve the research/intelligence brain for the long-term multi-account multi-platform vision.
type: feedback
originSessionId: 66111817-55d9-4a4c-b2ae-864b18030e59
---
User directive 2026-05-07: vision is **two-layer architecture**:
- **Right now**: needs functional + profitable trading for constant cash flow
- **Long-term (years out)**: multiple Topstep accounts, additional markets/platforms,
  AI-augmented research engine that gets smarter every day

## The two layers

### Layer 1: "The Knife" — minimum viable execution
**Purpose**: make money TODAY by reliably executing a validated edge.
**Properties**: small, dumb, debuggable, fails predictably.
**Target size**: ~500 lines.

Includes:
- ONE strategy (`gap_fill`) — only what's actively earning
- Direct broker integration (Topstep / ProjectX)
- Bracket orders (entry + stop + target)
- Hard DLL ($1,000) + per-trade loss cap
- Process watchdog (alive check + auto-revive)
- Simple position size config (1 contract for now)
- Halt switch (config flag, kills entries)

NOT in Layer 1:
- Strategy roster / cell allowlist / time-window gates (Layer 2 produces a single validated signal)
- Memory, lessons, agent prompts, validation pipeline
- Shadow trades, R-multiple trackers, daily refresh scripts
- Multi-strategy logic, defensive ladder, trailing profit tiers
- Anything that adds debugging surface area

### Layer 2: "The Brain" — research + intelligence platform
**Purpose**: get smarter every day; design new edges; manage strategy lifecycle.
**Properties**: complex, multi-tier, slow but valuable.
**Target size**: keep growing.

Includes (mostly already built):
- 24+ strategy library (`tools/backtest/strategies.py`)
- Walk-forward validation pipeline (`scripts/walk_forward_*`)
- Daily validation refresh (`scripts/daily_strategy_validation.py`)
- Live R-multiple tracker (`scripts/live_vs_oos_tracker.py`)
- Shadow trade resolver
- Quant Researcher agent + agent chain
- Memory + lessons + research vault
- Cowork coordination doc

The brain produces output for the knife: **a single "trade now" signal** with
entry/stop/target. Knife consumes deterministically.

## Multi-account / multi-platform expansion path (vision, years out)

Same brain, multiple knives. Each Topstep account gets its own Layer 1
instance, all reading from a shared Layer 2 brain. When new platforms
become available (other prop firms, retail brokers, crypto, etc.):
- Layer 2 emits platform-agnostic signals
- New Layer 1 adapter per platform translates to that broker's API
- Brain doesn't care which platform; knife is per-platform thin

This is the standard quant-fund architecture (alpha generation separate
from execution / order management). Building Layer 2 now pays off when
we scale to multiple accounts/markets later.

## WEEKEND CHECKPOINT (Saturday 2026-05-09)

Brought forward from Monday per user directive 2026-05-07: weekends are
zero-opportunity-cost (CME futures close Fri 4 PM ET, reopen Sun 5 PM ET).
Doing the simplification Sat-Sun means a fresh simplified trader is
ready for Sunday evening's Globex reopen — Monday morning starts with
one overnight run already under its belt.

**Trigger**: when user opens any session on or after Saturday 2026-05-09,
check Thursday-night + Friday-day-and-night data. If NOT clean, execute
the simplification autonomously per the playbook below. Do NOT wait
for permission. Surface the work in the session-open recap.

**Definition of "clean"**:
- ≥3 live trades fired
- Per-trade fill data captured cleanly (no target-tag mismatch)
- At least one trade closed at its planned target OR planned stop (not
  break-even churn)
- No DLL approach, no loss-cap fires, no overnight catastrophe

**Definition of "no clean session"**:
- Same target-tag bug recurs / trades close at unexpected prices
- 0 trades fire again (lookback + window fix didn't help)
- Multiple loss-cap fires (broker stop unreliability persists)
- Wifi / preflight prevents trader from running stably

**If no clean session by Saturday — autonomous simplification path** (timed for the weekend):

**Saturday 2026-05-09** (markets closed):
1. Branch off `simplification/layer1-minimal-knife` from master
2. Write `scripts/live_trader.py` (~500 lines, see specs below)
3. Test compile + unit tests pass
4. Run paper-mode dry-run against historical bars

**Sunday 2026-05-10** (markets closed until 5 PM ET):
5. Polish + edge cases
6. Run paper-mode rehearsal against final 60-min of bars before Globex reopen
7. ~4 PM ET: install scheduled task pointing to `live_trader.py` (archive `auto_trader.py` → `auto_trader_v1_complex.py`)
8. ~5 PM ET when Globex reopens: trader goes live with simplified architecture

**Monday 2026-05-11 morning**:
9. First recap with simplified trader includes Sunday-evening + Monday-morning data
10. If Monday's session is clean → keep simplified. If still broken → it's a deeper Topstep API issue, escalate.

The original simplification path below applies; just compressed into the weekend window.

**Original simplification path (now scheduled for Sat-Sun)**:

1. **Branch off** `simplification/layer1-minimal-knife` from master
2. **Write** new `scripts/auto_trader_v2.py` (or `live_trader.py`):
   - ~500 lines max
   - Reads validated signal from `state/strategy_validation.json` (Layer 2 output)
   - Direct ProjectX bracket placement
   - Reads halt switch from `config/risk_limits.yaml`
   - Reads DLL + per-trade cap from same config
   - One scan loop, one strategy, one filter — gap_fill ZN only initially
3. **Keep the brain intact**: `daily_strategy_validation.py`, all `walk_forward_*`,
   memory, lessons, vault — all stay. They produce signals; new trader consumes them.
4. **Test** in `FUND_MODE=paper` for 1 day before going live
5. **Switch over**: install scheduled task pointing to new trader; archive old
   `auto_trader.py` as `auto_trader_v1_complex.py` for reference (not deleted)
6. **Document** in `vault/lessons/2026-05-XX_simplification_to_two_layer.md`

**Success metric for the simplified trader**:
- 5 consecutive clean trading days (signals fire, fills tracked, no anomalies)
- Then: scale by adding ZT/ZB/ZF (one symbol per week)
- Then: re-add validated cells from Layer 2 (one strategy per week)

Each addition tested for 5 days before next. Slow growth, reliable foundation.

## What I will NOT do during simplification

- Delete the existing `auto_trader.py` — archive to `_v1_complex.py`
- Remove the validation pipeline, memory, lessons, agent prompts
- Discard any of the diagnostic infrastructure (fill-back, R-tracker, etc.)
- Modify HIGH_RISK_FILES without user approval
- Cut features the user has explicitly asked for (Cowork coordination,
  Discord notifications when configured, etc.)

The simplification PRESERVES the brain and BUILDS A SIMPLER KNIFE.
The brain is the long-term moat; the knife just needs to be reliable
right now for cash flow.

## Brain inventory (everything that stays during simplification)

**Agents** (`agents/*.md` — keep all 100%):
- CIO (chief investment officer / regime read + agent dispatcher)
- Risk Manager (Citadel/Jane-Street-grade risk officer)
- Portfolio Manager (pursue/pass decisions)
- Edge Hunter (proposes new candidate setups)
- Quant Researcher (novel strategy proposals; deep-dive backtest analysis)
- Compliance (rule-set checks)
- Sector analysts: Energies, Metals, Ag, Rates, FX Futures, Index/Macro
- Execution Trader (legacy; under v2, knife replaces this)

**Obsidian vault** (`vault/` — keep all 100%):
- `vault/_meta/` — current_goal, economics, principles, improvement_backlog,
  trading_process, strategy_performance, cowork_coordination, memory_backup
- `vault/lessons/` — RULE/HARD/PATTERN/ADVISORY tier lessons
- `vault/playbooks/` — strategy playbooks
- `vault/journal/` — daily session briefs
- `vault/research/` — backtests, validation, live_vs_oos, strategy_proposals
- `vault/sessions/` — auto-generated session summaries
- `vault/economic_calendar/` — daily economic events + auctions + Fed speakers
- `vault/_templates/` — note templates
- `vault/reading_list/` — research reading queue

**Research + intelligence scripts** (keep all):
- `scripts/walk_forward_phase2.py`, `walk_forward_extensions.py`,
  `walk_forward_gapfill.py`, `walk_forward_tier4_*`
- `scripts/daily_strategy_validation.py`
- `scripts/live_vs_oos_tracker.py`
- `scripts/shadow_trade_resolver.py`
- `scripts/strategy_deep_analysis.py`, `backtest_price_action.py`
- `scripts/auto_promote_lessons.py`
- `scripts/fetch_*` (treasury auctions, fed speakers, FRED macro)
- `scripts/generate_macro_brief.py`
- `scripts/session_summary.py`, `backup_memory.py`

**Orchestration + agent infra** (keep all):
- `runtime/orchestrator.py` — agent chain wiring (CIO → analyst → PM → Risk → Exec)
- `runtime/event_loop.py`, scheduler integration
- `tools/topstep.py` — broker tools used by agents
- `state/db.py`, `state/schema.sql` — SQLite persistence
- `hooks/risk_gate.py` — PreToolUse hook for the agent chain

**Memory + cross-session**:
- All `~/.claude/projects/.../memory/` feedback + project entries
- `MEMORY.md` index (33+ entries)
- All Cowork coordination + handoff logs

## What the knife (Layer 1) consumes from the brain

The brain writes its decision to a known interface that the knife reads.
Likely formats (TBD when implementing):

1. **`state/strategy_validation.json`** — already exists. Contains
   `live_allowlist` of validated cells. Knife reads this and only fires
   on listed cells.

2. **`state/active_signal.json`** (NEW, possibly) — brain writes the
   single "trade now" decision: symbol, side, entry, stop, target,
   strategy, conviction. Knife polls this every scan, fires the bracket
   if a signal is fresh and the knife isn't already in a trade.

3. **`config/risk_limits.yaml`** — knife reads DLL, per-trade cap,
   halt timestamp. User-controlled, not brain-controlled.

The knife does NOT read agent outputs directly, decisions tables, or
any of the brain's internal state. It just reads a clean signal file
and a config file. Everything else — the entire brain — runs in
parallel as research/intelligence and influences the next signal.

## Future expansion (years out, vision)

When new platforms become available (other prop firms, crypto exchanges,
retail brokers), each platform gets its own thin knife (~500 LOC adapter
to that broker's API). They all read from the same brain's signal file.
When the brain validates a new strategy or symbol, ALL knives can act on
it without per-knife code changes. That's the multi-account, multi-platform
vision the user wants.
