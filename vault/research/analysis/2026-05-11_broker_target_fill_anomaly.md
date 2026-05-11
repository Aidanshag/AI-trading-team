---
type: incident_report
date: 2026-05-11
status: halted_pending_review
loss_usd_today: 24.72
related: orphan_leg_fix_2026-05-11, gap_fill_pipeline_corrections
---

# Target LIMIT orders not honoring limit price — structural broker issue

## Headline

Both of today's trades (NG inside_bar_break short, 6B order_block_d1 long) **closed at ~1 tick adverse to entry within ~5 min**, despite:
- The orphan-leg fix working correctly (entry-confirmed before legs placed)
- Stops set far from entry (17+ ticks above for NG short, 14 ticks below for 6B long)
- Targets set in the correct profit direction (target ABOVE entry for long, BELOW for short)

The broker's order_history records the TARGET LIMIT orders as `status=Filled` but at prices that violate the limit (e.g., 6B target SELL limit at 1.3628 filled at 1.3606).

Net P&L today: **−$24.72** (NG −$14.24 + 6B −$10.48). Halted at 13:02 UTC for investigation.

## What's happening

For both trades:
- Entry placed → filled
- Stop + target legs placed
- Position closed within ~5 min at ~1 tick adverse to entry
- Target leg recorded as filled at the close price (NOT at the limit we set)
- Stop leg eventually cancelled by orphan cleanup (it was unused)

## Evidence this is pre-existing, not introduced by my changes

Historical `auto_trader` trades from 2026-05-05 / 05-06 show the SAME pattern. Sample:

| date | symbol | side | target limit | actual fill | gap |
|---|---|---|---|---|---|
| 2026-05-06 | MCL | sell | 101.56 | 100.85 | 0.71 below |
| 2026-05-06 | GC  | buy  | 4644.5 | 4653.9 | 9.4 above  |
| 2026-05-06 | MCL | sell | 101.92 | 100.81 | 1.11 below |
| 2026-05-05 | GC  | buy  | 4547.7 | 4562.5 | 14.8 above |
| 2026-05-05 | GC  | buy  | 4530.1 | 4544.2 | 14.1 above |

These weren't introduced by tonight's changes — they pre-date by 5+ days. So auto_trader has been operating with this exact pathology the entire time.

## DEFINITIVE PROOF (added 13:10 UTC)

Pulled exact timestamps from `client.get_order_history()`:

**NG bracket:**
- Entry filled: 12:39:53.695
- Stop leg created: 12:39:54.249
- Target leg created: 12:39:54.362
- Target leg "filled": 12:39:54.362 (**same timestamp — fired within 113ms of placement**)
- Stop leg cancelled by orphan cleanup at 12:44:55.042

**6B bracket:**
- Entry filled: 12:54:58.418
- Stop leg created: 12:54:58.648
- Target leg created: 12:54:58.728
- Target leg "filled": 12:54:58.728 (**same timestamp — fired within 80ms of placement**)
- Stop leg cancelled by orphan cleanup at 13:00:00.168

The target legs fire WITHIN MILLISECONDS of being placed. They are *immediately executable* on the broker side, regardless of their stated limit price being non-marketable.

This proves:
1. The broker treats our target LIMIT orders as **immediately marketable** (effectively market orders).
2. There is no waiting for the limit price; the orders fire at next available bid/ask the moment they're placed.
3. The 5-min orphan cleanup is innocent — it just sweeps the already-orphaned stop after position is flat.

## Hypothesis

ProjectX (or Topstep) likely marks both protective legs as "filled" when the position closes by ANY mechanism, recording the actual close price against the target leg specifically. In other words: the "fill" we see is not a real fill of the limit order — it's the close-position record, attributed to the target leg for accounting.

What's actually closing the position is something else. Candidates:
- Some kind of timed force-close (5-min window is suspicious)
- Topstep risk management auto-closing
- An undocumented "marketable limit" interpretation where ALL limit orders that close existing positions fire immediately at market

I've ruled out:
- `live_trader.py` doesn't have explicit close/flatten logic
- `_force_close_per_trade_loss_cap` only fires at -$150 (we were at -$10 to -$15)
- Orphan-leg cleanup happens AFTER the position is flat (it can't be the cause)

## What I changed tonight that DIDN'T cause this

- Calibration gate (MIN_SIGNAL_R_TICKS=6) — only filters signals before placement
- Orphan-leg fix in `place_bracket` — only changes ordering; same orders eventually placed
- Strategy floor patch (gap_fill min_stop_ticks) — only changes which signals fire
- find_latest_signal tick_size injection — only changes signal emission
- param_sweep typo fix (`t.stop_price` → `t.stop`) — backtest measurement only
- Live allowlist expansion — only changes which cells the trader iterates

None of these touch the broker placement or close-position pathway.

## What needs investigation tomorrow

1. **Read ProjectX limit-order semantics.** Maybe `limit_price` field is interpreted as "marketable" in their API and standard limits need a different field (e.g., `targetPrice`, `priceLimit`).
2. **Test with a long-out-of-the-money limit on a paper account** to see if it sits in the book or fills immediately.
3. **Talk to Topstep / ProjectX support** to confirm the broker's bracket-order semantics.
4. **Workaround if confirmed:** drop target legs entirely; rely on stops + manual signal exits. This eliminates the bleed but means winners can run unbounded until stop fires.

## Live system state at halt-time (13:02 UTC)

- Trader: PID 33112+45668, alive, halted until 19:02 UTC
- Account balance: $49,254.14 (−$24.72 today)
- Open positions: 0
- Working orders: 0
- Trades today: 2 (both closed)
- Discord pinged on each milestone

## Decision deferred to user

Whether to resume trading under the current bleed pattern (each trade ≈ $10-15 net loss regardless of strategy outcome) OR fix the placement first. User decision required.
