---
date: 2026-05-08
kind: strategic_playbook
topic: slippage_mitigation
status: reference — items implemented as user prioritizes
related:
  - vault/research/backtests/2026-05-08_slippage_sensitivity.md
  - vault/_meta/improvement_backlog.md
---

# Slippage mitigation playbook

Reference document for all known ways to reduce or insulate against
slippage on Topstep-executed strategies. Items are ranked by leverage
and effort; user/brain implements as priorities allow.

Background: discovered 2026-05-08 that gap_fill on treasuries is
slippage-fragile — backtest +$81k 60d edge flips to -$113k at realistic
0.25 tick/side. Replaced with `gap_fill_wide` which is structurally
slippage-tolerant. This playbook captures the broader landscape of
slippage-mitigation options for future implementation.

---

## Section 1: Direct slippage-reduction levers (apply to any strategy)

| # | Lever | Slippage reduction | Effort | When to implement |
|---|---|---|---|---|
| **1** | **Passive entry** (post-only limit at bid for buys, offer for sells) | -50% on entry slippage | ~2 hrs code change | Post-Sunday once we measure actual slippage |
| **2** | **Higher timeframe** (15m/1h bars instead of 5m) | Wider natural stops absorb slippage proportionally | ~1 day, requires backtesting | When cowork parameter sweep finds candidates |
| **3** | **Symbol-specific tightening** (e.g., only ZF, smallest tick value $7.81) | -60% absolute slippage cost vs ZB ($31.25) | Brain config change (allowlist) | If actual slippage > 0.5 ticks/side |
| **4** | **Bid-ask spread filter** (only trade when spread ≤ N ticks) | Conditional gating | Requires real-time tick data subscription | Major project — weeks |
| **5** | **Time-based exits** (close at market after N minutes) | Eliminates stop-fail-to-fill risk | ~3 hrs code change | If we see failed stop-limits in live data |
| **6** | **Maker / liquidity-providing strategy** (pure post-only, never cross spread) | Slippage can be NEGATIVE — collect spread | Major rewrite | Long-term |
| **7** | **Iceberg / multi-attempt limits** (try 3 times at desired price) | -30% average | Complex order logic | Long-term |
| **8** | **Reduce per-trade contract cap** (e.g., 2 instead of 5) | Linear reduction in absolute slippage cost | 1-line change | Trade-off: cuts profit edge proportionally |

### Detail on lever #1 — Passive entries

The single highest-leverage change. Currently the trader uses
**marketable-limit at +5 ticks** which crosses the spread. Replacing
with **post-only-limit at the favorable side** means we wait for the
market to come to us rather than chasing.

Implementation:
- `scripts/live_trader.py:place_bracket` — change `order_type="limit"`
  call's `limit_price` to use bid (for buys) or ask (for sells)
- Add `time_in_force="day_post_only"` if Topstep supports it, OR
- Add a 5-min cancel-and-retry loop if it doesn't fill

Trade-off:
- For mean-reversion (`gap_fill_wide`): GOOD — missed fills on momentum
  bursts naturally protect against bad fills. We're fading; momentum
  bursts are exactly the trades we'd want to skip.
- For trend-following: BAD — missed fills mean missing the trend.

This is why passive entries are particularly well-suited to our
`gap_fill_wide` deployment.

### Detail on lever #4 — Spread filter

Requires market-data infrastructure we don't yet have. ProjectX may
expose bid-ask via a separate quote endpoint; needs investigation. If
available, add `if spread > N_ticks: skip` to scan_once. Most useful
during news / thin tape.

### Detail on lever #5 — Time-based exits

Replace stop-limit (which can fail to fill) with:
- Soft stop: monitor unrealized P&L every scan
- If unrealized < -$X for >N minutes, close at market
- If hit target = limit fills as normal

Eliminates the worst-case scenario of "stop didn't fill, position
ran beyond stop and ate DLL." Adds complexity in scan logic.

---

## Section 2: Strategy categories that are inherently slippage-tolerant

| Category | How it's slippage-tolerant | Examples in our registry | Status |
|---|---|---|---|
| **Wide-target trend-following** | Per-trade $ profit dwarfs slippage cost | `donchian_breakout`, `vol_regime_trend` | Both currently lose at default params — need retuning (cowork queue) |
| **Multi-day swing** | Stops + targets in $-thousands per trade | None currently — would need daily-bar strategies | Future: cowork could implement |
| **Maker / liquidity-providing** | Slippage can be NEGATIVE (you collect spread) | None — would need post-only orders | Long-term: requires rewrite of `place_bracket` |
| **Volatility-expansion entries** | Setup specifies a wide expected range | `volatility_breakout`, `bollinger_squeeze_break` | Both lose at default params — parameters might fix |
| **Pairs / spread arb** | Spread is bid-ask agnostic (you trade the differential) | None — needs cross-asset infrastructure | Long-term: requires multi-leg order logic |
| **Wide-stop volatility breakout** | gap_fill_wide is in this category | `gap_fill_wide` ← **DEPLOYED** | Live since 2026-05-08 |

The fund's only currently-deployed slippage-tolerant strategy is
`gap_fill_wide`. Of the other categories, retuning existing
strategies (parameter sweep) is the fastest path; multi-day swing and
maker strategies are longer-term projects.

---

## Section 3: New strategy proposal — Wide-Range Session Drive

A new strategy explicitly designed for slippage tolerance. Queued for
cowork at P1.

### Concept

```
At each session boundary (Asian/London/RTH/PostClose open):
  - Wait for first 30 min to establish opening range (high - low)
  - On break of either side of opening range:
      Entry: at break price
      Stop:  entry ± 1.0 × session_range  (30-100 ticks wide)
      Target:entry ± 2.5 × session_range  (favorable RR)
  - Hold up to 4 hours or until session end
```

### Why it's slippage-tolerant

| Property | gap_fill (default) | gap_fill_wide | wide_session_drive |
|---|---|---|---|
| Typical stop distance | sub-tick | 3-5 ticks | 30-100 ticks |
| 1-tick slippage cost / stop | >100% | ~30% | ~1-3% |
| Per-trade $ edge (idealized) | $27 | $120 | $200-800 |
| Hit rate (estimated) | 60% | 67% | 35-45% |
| Trades per 60d | 4,000+ | ~100 | ~20-40 |

The wider stops and larger per-trade $ edge mean slippage becomes a
small percentage of expected gain. Hit rate is lower (more trades
stop out before reaching target) but the math works because winners
are 5-10× larger than losers.

### Differences from existing `opening_range_breakout`

ORB lost money at default params in our backtest because it used tight
stops (0.5 × ATR) that got noise-stopped. The wide_session_drive uses
the FULL session range as the unit, making stops much wider.

### Implementation spec (for cowork)

```python
def wide_session_drive(
    bars: pd.DataFrame,
    or_minutes: int = 30,
    stop_range_mult: float = 1.0,
    target_range_mult: float = 2.5,
    max_hold_hours: int = 4,
) -> Iterator[Signal]:
    """Wide-stop opening-range breakout — slippage-tolerant.

    Parameters chosen so stop is far wider than typical bid-ask, making
    1-tick slippage a small fraction of stop distance.
    """
    # 1. Identify session boundaries (Asian: 18:00 ET, London: 04:00 ET, etc)
    # 2. For each session, compute opening range over first or_minutes
    # 3. Watch for break of either side
    # 4. On break: enter, set stop = ±range, target = ±2.5×range
    # 5. Yield Signal.entry
```

### Validation plan (cowork P1)

1. Implement function in `tools/backtest/strategies.py`
2. Add to `STRATEGY_REGISTRY` and `daily_strategy_validation.py:ALL_STRATEGIES`
3. Run grid backtest across treasuries + NG + 6E + ES at slippage levels [0, 0.25, 0.5, 1.0]
4. Acceptance: positive expectancy at 0.25 slippage on n≥30 trades
5. If passes, walk-forward validation auto-runs
6. If walk-forward passes (n≥20, t≥1.5 OOS), brain auto-promotes to live_allowlist

---

## Section 4: Portfolio approach to slippage tolerance

Rather than relying on a single slippage-tolerant strategy, target a
**portfolio of 3-5 slippage-tolerant strategies** that diversify risk:

1. `gap_fill_wide` — mean-reversion, currently deployed
2. `wide_session_drive` — momentum, queued for cowork
3. Retuned `donchian_breakout` — wide-target trend-following, queued for cowork sweep
4. Future: multi-day swing on daily bars
5. Future: maker strategy with post-only orders

Each contributes:
- Different signal triggers (mean-rev vs trend vs maker)
- Different time-of-day exposure
- Different drawdown correlation
- Different slippage absorption profile

Portfolio is more robust than single-strategy concentration.

---

## Section 5: When each item gets implemented

### Immediate (post-Sunday measurement)
If actual broker slippage on `gap_fill_wide` lands at 0.10–0.25 ticks/side:
→ Current allowlist works; focus on cell-level optimization (parameter sweep)

If actual slippage is 0.25–0.5 ticks/side:
→ Implement #1 (passive entries) as priority
→ Activate #5 (time-based exits) as fallback for stop reliability

If actual slippage > 0.5 ticks/side:
→ Implement #1 + #3 (symbol-specific tightening: drop ZB)
→ Push wide_session_drive (Section 3) to top of priority

### Near-term (next 2-4 weeks)
- Lever #1: passive entries (highest single-impact change)
- Lever #5: time-based exits (reliability improvement)
- Strategy: wide_session_drive validation + deployment
- Parameter sweep results from cowork → retuned trend-followers

### Medium-term (4-12 weeks)
- Lever #2: higher-timeframe variants
- Lever #3: symbol-specific tuning per measured slippage profile
- Multi-day swing strategy development

### Long-term (3+ months, post-Combine pass)
- Lever #4: spread filter (requires market-data subscription)
- Lever #6: maker / liquidity-providing strategy
- Lever #7: iceberg orders
- Pairs / spread arb infrastructure

---

## Section 6: Measurement infrastructure

Already in place:
- `scripts/slippage_tracker.py` — reads filled orders from
  `state/fund.db:orders`, computes signed slippage in ticks per cell,
  writes `vault/research/live_slippage/<date>_per_cell.md`
- Run after each session to track slippage trend over time

Useful additions (queue):
- Per-symbol slippage tracker (separate from per-cell)
- Per-time-of-day slippage tracker (which hours have worst slippage)
- Per-market-condition tracker (vol regime, news proximity)

---

## Section 7: How to read this document

This is a strategic reference. Items here are NOT all in immediate
implementation — they're catalogued so we can pull the right lever
when conditions warrant.

The flow:
1. Sunday measures actual slippage (`scripts/slippage_tracker.py`)
2. Monday reviews the slippage report
3. If slippage is acceptable → focus on parameter optimization
4. If slippage is bad → pull from this playbook the matching mitigation
5. Implementation done by either CLI Claude (operational changes) or
   Cowork (strategy/infrastructure changes) per
   `vault/_meta/cowork_coordination.md`

This document gets updated as we implement items (mark "✓ implemented
YYYY-MM-DD") so we know what's been tried and what's still on the table.
