---
type: backlog
purpose: Prioritized queue of fund improvements, consumed by /improve-fund autonomous cycles
---

# Improvement backlog

This file is the work queue for the autonomous-improvement loop. Each entry has explicit priority, effort, risk, and status fields so cycles can pick items mechanically.

## Format

```
- [P0|P1|P2|P3] [effort: Nmin] [risk: low|medium|high] [status: open|in-progress|proposed|merged]
  Title — one-line description
  Why: motivation
  Files: target files (best guess)
  Acceptance: how to know it's done
  Auto-merge: true|false (default false)
```

---

## P0 — critical (do first)

- [P0] [effort: 90min] [risk: low] [status: open]
  **Auto-promote/demote cells from live evidence**
  Why: gap_fill backtest edge is sensitive to slippage (2026-05-08 finding: edge flips negative at 0.25 tick/side). Live data starting Sunday will reveal whether each cell's OOS edge holds. Without auto-rebalancing, brain stays naive.
  Files: NEW `scripts/cell_auto_promote.py`, integrate into `scripts/preflight.py` step 9
  Logic: read last 30d live trades from `state/fund.db:orders`; per-cell live_E vs OOS_E from `state/strategy_validation.json`; promote shadow→live if (n≥10, E>0, |live−OOS|<1R); demote live→shadow if (n≥10, E<0). Atomic write to `live_allowlist`. Audit log to `vault/research/cell_promotion_log.md`.
  Acceptance: dry-run with current DB shows zero promotions/demotions (no fills yet); after Sunday fills land, surfaces meaningful changes.
  Auto-merge: false (touches `live_allowlist` which trader reads)

- [P0] [effort: 45min] [risk: medium] [status: open]
  **Trim live_trader.py: extract snapshot capture to tools/snapshot_writer.py**
  Why: trader at 763 lines as of 2026-05-08 after adding cleanup + Sunday-reopen gates. The capture_snapshot + compute_unrealized block is ~100 lines of "broker state observer" logic that is not core execution. Extract to tools/ keeps the knife focused.
  Files: `scripts/live_trader.py` (lines 131-226 region), NEW `tools/snapshot_writer.py`
  Acceptance: live_trader imports `capture_snapshot` from `tools.snapshot_writer`; all 25 unit tests still pass; dry-run scan output identical to pre-extraction. Trader < 700 lines.
  Auto-merge: false (touches the running trader path; user should review PR)

- [P1] [effort: 90min] [risk: low] [status: open]
  **New strategy: wide_session_drive — designed for slippage tolerance**
  Why: only gap_fill_wide currently survives realistic slippage in our registry. We need 2-3 slippage-tolerant strategies as a portfolio, not a single point of failure. Wide-stop strategies with wide targets absorb slippage as a small fraction.
  Logic: at each session boundary, define opening range (30 min), enter on break with stop = ±1.0 × range, target = ±2.5 × range. Per-trade R-multiple ~2.5; per-trade $ edge $200-800; hit rate target 35-45%.
  Files: NEW entry in `tools/backtest/strategies.py` registered in `STRATEGY_REGISTRY`; integration into `scripts/daily_strategy_validation.py:ALL_STRATEGIES`.
  Acceptance: backtest on 60d 5m bars across treasuries + NG + 6E + ES; slippage sensitivity at 0/0.25/0.5/1.0 ticks per side; demonstrate positive expectancy at 0.25 slippage on n≥30 trades. If passes, walk-forward validation auto-runs.
  Auto-merge: false (touches strategy library)

- [P1] [effort: 120min] [risk: medium] [status: open]
  **Passive entry orders (post-only / limit-at-bid)**
  Why: largest single slippage reduction lever (-50% on entry slippage). Currently using marketable-limit at +5 ticks which crosses the spread. Post-only would rest at the favorable side and only fill when market comes to us.
  Files: `scripts/live_trader.py:place_bracket` — change entry from marketable-limit to post-only-limit. Add a fill-timeout (e.g., 5 min) after which we cancel and try again or skip the signal.
  Acceptance: backtest with post-only fills (estimated fill rate 40-60%) shows net P&L improvement after accounting for missed fills. Live data confirms entry slippage reduction.
  Auto-merge: false (touches order placement code path)

- [P0] [effort: 60min] [risk: low] [status: open]
  **Strategy parameter sweep framework — gap_fill robustness sweep**
  Why: same finding as above. Need a gap_fill parameterization with enough per-trade $ edge to absorb 0.25-0.5 tick slippage. Default (min_gap_atr=0.75, rr_target=1.5) is too tight.
  Files: NEW `scripts/param_sweep.py`. First sweep: gap_fill, min_gap_atr ∈ {0.5,0.75,1.0,1.5}, rr_target ∈ {1.0,1.25,1.5,2.0}, on ZN/ZB/ZT/ZF, walk-forward 60d.
  Acceptance: produces `vault/research/param_sweeps/gap_fill_2026-05-08.csv` with per-cell hit/E/t-stat/sample-size; flags top 3 cells by slippage-adjusted EV.
  Auto-merge: true (offline analysis, no production code touched)

## P1 — high (Phase 2 work)

- [P1] [effort: 30min] [risk: low] [status: merged 2026-04-30]
  **Real-time loss alerter (Discord webhook)** — DONE
  Implemented `scripts/loss_alerter.py` with thresholds at -$100/-$200/-$400/canTrade=false.
  Wired into `auto_trader.scan_once` after each snapshot. `--test` flag fires synthetic alert.
  Activates when user adds `DISCORD_WEBHOOK_URL` to .env.

- [P1] [effort: 45min] [risk: low] [status: merged 2026-04-30]
  **Per-strategy auto-demote on negative-EV streak** — DONE
  Implemented `_strategy_recent_streak` and `_strategy_is_demoted` helpers.
  When a strategy hits 5 consecutive stop-outs in 4h, auto-suspends for the rest of UTC day
  via `risk_events.rule='strategy_demoted_today'`.

- [P1] [effort: 60min] [risk: medium] [status: open]
  **Setup confluence requirement**
  Why: lone signals fired in noisy tape today. A signal confirmed by ≥1 of: volume above 1.5× MA, ATR expansion, or another strategy showing same direction is more reliable
  Files: `scripts/auto_trader.py:find_latest_signal` or new wrapper
  Acceptance: signals not confirmed by at least one confluence factor are skipped under autonomous mode
  Auto-merge: false (touches hot path)

## P2 — medium

- [P2] [effort: 30min] [risk: low] [status: open]
  **Cost ledger in CIO daily brief**
  Why: agents need to feel the cost burn every session. CIO's brief already exists; it just needs the cost ledger pulled in.
  Files: `agents/cio.md` (prompt update), `scripts/_session_brief.py` (if it exists), or new helper
  Acceptance: every CIO session brief opens with "MTD: gross +$X, fees -$Y, API -$Z, net +$W"

- [P2] [effort: 20min] [risk: low] [status: merged 2026-05-01]
  **Lessons → strategy_blacklist auto-promotion** — DONE
  Script existed but used yaml.safe_dump which strips comments (same bug
  fixed in halt.py). Replaced with targeted text-only edit. Two tests
  added (`tests/test_auto_promote_lessons.py`) — comment preservation +
  idempotency. RULE-tier lessons now auto-encode without destroying the
  hand-curated explanations in risk_limits.yaml.

- [P2] [effort: 45min] [risk: medium] [status: open]
  **Regime classifier (live vol/volume metric)**
  Why: today's blanket 21:00–04:00 ET rule is crude. A live regime classifier ("ATR/avg over recent N bars below threshold → choppy → block mean-reversion") would be more precise
  Files: new `tools/regime_classifier.py`, plumb into auto_trader
  Acceptance: regime_classifier.current_regime() returns one of {trending, choppy, event, thin}; auto_trader respects it

- [P2] [effort: 30min] [risk: low] [status: merged 2026-04-30]
  **`fund halt` and `fund resume` CLI commands** — DONE
  Implemented `scripts/halt.py` with `4h` / `30m` / `next-open` / `clear` /
  `status` subcommands. Targeted text-edit (preserves YAML comments).
  Wired into `fund.ps1` as `fund halt` and `fund resume` verbs.

## P3 — long-term

- [P3] [effort: 90min] [risk: medium] [status: open]
  **Remote kill switch (HTTP endpoint, password-protected)**
  Why: kill from your phone when you see a bleed. Tiny Flask/FastAPI endpoint, password auth, sets `trading_halt_until`
  Files: new `scripts/remote_kill.py` + service install script
  Acceptance: POST to `http://localhost:PORT/halt?duration=4h` (with bearer token) writes the halt
  Note: medium risk — requires opening a port. User must approve network exposure model.

- [P3] [effort: 2h] [risk: high] [status: open]
  **A/B test new strategies in shadow mode**
  Why: new strategies should accumulate outcomes in `shadow_trades` table for N days before going live
  Files: `tools/backtest/strategies.py` (mark which are validated), `scripts/auto_trader.py` (only fire validated for live)
  Acceptance: a `validated_after: YYYY-MM-DD` field on each strategy gates whether it can fire live or only shadow
  Auto-merge: false

- [P3] [effort: 60min] [risk: low] [status: merged 2026-04-30]
  **Documentation: CLAUDE.md update with new config blocks** — DONE
  Created `CLAUDE.md` at project root with: top-level orientation, read-first
  order, layout map, full risk-floor architecture (all 23 hook checks listed),
  two-trading-paths note, operational scripts, autonomous infra, recent
  history. New Claude sessions discover this on attach.

---

## Strategy ideas to implement (user-supplied)

This section is the user's idea inbox for new price-action / mathematical
strategies. Drop notes, descriptions, screenshots, links, or rough sketches
here. The autonomous-improvement loop (cloud routine
`trig_011w6DUmXbojsfkjKtCaJfBa`) will pick items from this section, code
them up against the existing strategy protocol in
`tools/backtest/strategies.py`, register them in `STRATEGY_REGISTRY` and
`STRATEGY_ROSTER`, add literature priors to `tools/strategy_performance.py`,
write tests, and submit a PR.

**Strategic focus:** price-action / microstructure / mathematical. FVG is
the lead strategy. Classical TA additions go straight to P3 unless the
user explicitly asks for one.

**Format for entries:**

```
- [strategy_name] [status: idea|proposed|implemented]
  Description: what is the pattern, in plain English
  Source: where this came from (friend, book, paper, link, intuition)
  Trigger conditions: candle/structure rules
  Entry/Stop/Target: rough idea
  Symbols of interest: which markets it should run on
  Notes: any extra context
```

**Examples (currently empty — drop ideas below):**

<!-- USER: ADD IDEAS HERE -->

## Research backlog for next Quant Researcher wake (2026-05-05)

- [extended_data_validation] [status: idea]
  Description: Re-run walk_forward_phase2.py on 90+ days of intraday data once available to confirm the 7 cells deployed today don't deteriorate
  Symbols of interest: 6E, MCL, NG, GC, MES, ZN
  Notes: yfinance limits to 60d for 5m bars. Need a different data source for longer history (firstrate_csv source already wired)

- [param_sweep_gap_fill_ZN] [status: idea]
  Description: gap_fill ZN at default params shows OOS E=+1.10R t=+11.95. Earlier sweep showed min_gap_atr=1.25 hits +2.74R OOS but small n. Sweep min_gap_atr ∈ {0.5, 0.6, 0.75, 1.0, 1.25} × rr_target ∈ {1.0, 1.5, 2.0, 2.5} on more data. Find optimal cell.
  Trigger conditions: rerun walk_forward_extensions.py with extended params

- [confluence_strategies] [status: idea]
  Description: Do confluence-of-signals filters add edge? E.g., "only fire gap_fill ZN Asian when also RSI < 30 (oversold)" or "only fire pivot_reversal 6E RTH short when DXY rallying"
  Trigger conditions: design + walk-forward each combination

- [time_of_day_micro_buckets] [status: idea]
  Description: Current sessions are 4 buckets (Asian/London/RTH/PostClose). Try finer 2-hour buckets (e.g., 02:00-04:00 vs 04:00-06:00 inside Asian) to find tighter edge windows
  Notes: Risk of overfitting; require n>=30 per bucket and walk-forward

- [order_flow_microstructure] [status: idea]
  Description: Investigate whether ProjectX provides bid/ask spread or depth data. If yes, add features: imbalance, micro-price drift, sweep detection
  Source: ProjectX API docs

- [anti_strategy_research] [status: idea]
  Description: narrow_range_break has aggregate -0.09R t=-3.93. The INVERSE direction would have aggregate +0.09R. Test "fade NRB" as an explicit strategy with proper walk-forward
  Notes: only useful if t>2 OOS; avoid building on known-losing strategies

## Old example template (kept for format reference)

- [example_template] [status: idea]
  Description: (your description)
  Source: (your source)
  Trigger conditions: (your rules)
  Entry/Stop/Target: (rough sketch)
  Symbols of interest: (which markets)
  Notes: (anything else)

---

## How items get added

- Failed sessions / new bugs → P0 or P1 with a `lesson_ref:` link to the journal/lesson file
- Audit findings during `/improve-fund` cycles → `proposed` status until user approves
- User requests → directly added at requested priority

## How items get removed

When merged, change `status: merged` and add `merged_in:` git SHA. Keep the row for ~30 days as a record, then archive to `vault/_meta/archive/improvement_backlog_YYYY-MM.md`.
