# Exit-reasoner architecture (the agent that decides when to close)

Built 2026-05-12.

## Why

Mechanical trailing-profit-lock tiers (`tools/profit_protect.TRAILING_PROFIT_TIERS`)
treat every retrace the same: peak crosses tier threshold → tier floor
becomes active → trade closes on retrace below floor. This is FAST and
RELIABLE but it can't distinguish "structural reversal" from "normal
noise in a developing winner."

User-stated goal: bring *reasoning* into the exit decision while keeping
the mechanical floor as a backstop. This module is that.

## What

`tools/exit_reasoner.py` wraps `decide()`'s "should_close" signal with an
LLM (Haiku) that reads the recent bars + position state and returns:

- **CLOSE** — yes, this looks like a real reversal. Proceed with the tier-driven close.
- **HOLD** — no, this is normal noise. Skip the close this scan; re-evaluate next time.
- **FALLBACK_CLOSE** — agent unreachable. Proceed with mechanical close.

## The safety stack — what the agent CAN and CANNOT override

```
┌─ AGENT-VETO-ABLE ──────────────────────────────────────────────────┐
│                                                                    │
│   Trailing-profit-lock floors at peak ∈ [15, 750]                  │
│   These route through the agent IF feature flag enabled.           │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
┌─ MECHANICAL (NEVER vetoed by agent) ───────────────────────────────┐
│                                                                    │
│   1. Broker stop order (server-side, fires on tick)                │
│   2. LOSS_TIER_HARD_CAP_USD = $150 (decide() branch — bypasses     │
│      agent because reason ≠ "trailing_lock")                       │
│   3. Trailing tiers at peak ≥ $750 (runner zone — protected by    │
│      MAX_PEAK_USD_FOR_AGENT guard rail; the user-requested        │
│      "$1000+ gains keep mechanical" requirement is enforced here.) │
│   4. Hard-flatten clock 3:10 PM CT (runs in live_trader.scan_once  │
│      BEFORE profit_protect is called)                              │
│   5. Daily profit cap +$600 / Combine consistency rule (runs in   │
│      tools/daily_profit_cap.py before profit_protect)              │
│   6. Topstep server-side `canTrade=false` (hooks/risk_gate.py)     │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

## Agent authority caps

The agent CAN issue HOLD overrides only when ALL of these hold:

| Guard | Default | Purpose |
|---|---|---|
| `peak_unrealized_usd >= MIN_PEAK_USD_TO_INVOKE_AGENT` | $15 | Below this, the trade hasn't shown intent — let the rule fire fast |
| `peak_unrealized_usd <= MAX_PEAK_USD_FOR_AGENT` | $750 | Above this, runner tiers protect the gain mechanically |
| `consecutive_holds < MAX_CONSECUTIVE_HOLDS` | 3 | Agent can't indefinitely delay |
| `time_in_trade < MAX_AGENT_HOLD_DURATION_SECONDS` | 30 min | Same idea — bound the worst case |
| Circuit breaker not tripped | 3 failures in 5 min trips it | Self-disables on API instability |

If ANY guard fires, the agent is bypassed and the mechanical tier wins.

## Feature flag rollout

`config/exit_reasoner.yaml` controls deployment:

```yaml
enabled: false           # Master switch — false = mechanical only (current)
report_only: true        # When enabled=true and report_only=true,
                         # agent runs and logs but doesn't actually veto
enabled_cells: []        # Per-cell allowlist
denied_cells: [...]      # Per-cell blocklist (takes precedence)
```

**Rollout plan**:
1. **Now**: `enabled: false` — agent code is dormant. No live impact.
2. **After Combine clean session(s)**: flip `enabled: true` + `report_only: true`.
   Agent runs on every tier-trigger, logs to `agent_exit_vetoes`, but the
   trader still acts on mechanical tier. Two weeks of report-only data
   tells us empirically whether the agent's calls would have helped.
3. **If report-only data is positive**: set `report_only: false` and add
   the strongest 1-2 cells to `enabled_cells`. The agent's vetoes now
   actually skip closes.
4. **Full deployment**: `enabled_cells: ['*']` after a few weeks of cell-
   by-cell positive evidence.

## Empirical evidence so far

Phase 2 shadow-replay (2026-05-12, n=50 profit_lock shadows since May 1):

```
Control avg R:  +0.124   (mechanical tiers only)
Agent avg R:    +0.178   (with agent vetoes)
Delta per trade: +0.054R

5 improved, 7 worsened, 38 unchanged
HOLD=41  CLOSE=9  FALLBACK=0
```

Directionally positive but variance up. Need n≥200 sample before any
final read. Worsening cases skew big (e.g. MNQ trade: +0.42R → -1.08R
delta -1.50R) so a single bad call can dominate aggregate. Tuning
opportunities:

- Lower `MAX_CONSECUTIVE_HOLDS` to 2 (less aggressive agent)
- Raise `MIN_PEAK_USD_TO_INVOKE_AGENT` to $25 (only big enough trades)
- Prompt-tune to bias toward CLOSE in regime=high_vol

## Cost

Per-call: ~$0.002 (Haiku, ~1300 input + 50 output tokens). Typical
activity: 5-10 trades/day × 2-3 tier-trigger evaluations each = ~$0.10/day.
**Annual cost ceiling: <$40/year.**

## Logged decisions

Every veto (whether CLOSE, HOLD, FALLBACK_CLOSE, or a guard-rail bypass)
writes a row to `agent_exit_vetoes`:

```sql
ts, contract_id, symbol, side, strategy,
tier_floor_usd, peak_unrealized_usd, current_unrealized_usd,
time_in_trade_seconds, consecutive_holds,
decision (CLOSE|HOLD|FALLBACK_CLOSE), confidence, reason,
agent_model, agent_response_ms, prompt_tokens, completion_tokens,
actual_exit_usd, actual_exit_ts, agent_verdict
```

The last three columns (`actual_*`) are filled retroactively by an
audit job — once the position actually closes, we compare the agent's
prediction against reality and mark `agent_verdict ∈ {correct, wrong,
inconclusive}`. After accumulating ~30-50 verdicts, we can compute a
per-cell agent accuracy rate.

## Test coverage

`tests/test_exit_reasoner.py` — 15 tests covering:
- All authority guards (no-API path)
- API failure → FALLBACK_CLOSE
- Circuit breaker tripping + cooldown reset
- Response parsing including malformed → defaults to CLOSE
- DB logging always writes a row

## File map

```
tools/exit_reasoner.py            — The agent module (Phase 1)
tools/profit_protect.py           — Wired veto layer (Phase 1b)
tools/exec_mirror.py              — Callback for shadow replay (Phase 2)
scripts/shadow_replay_agent.py    — Phase 2 validation script
config/exit_reasoner.yaml         — Feature flag config
state/schema.sql:agent_exit_vetoes  — Decision audit table
tests/test_exit_reasoner.py       — Guard rail + parsing tests
```
