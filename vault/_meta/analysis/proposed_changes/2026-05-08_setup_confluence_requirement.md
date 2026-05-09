---
type: proposed_change
date: 2026-05-08
author: Cowork (Claude)
priority: P1
status: PROPOSED — needs user/CC review before merge
references:
  - vault/_meta/improvement_backlog.md (P1 "Setup confluence requirement")
  - vault/_meta/cowork_coordination.md (2026-05-08 queue item #10)
  - scripts/live_trader.py:find_latest_signal
---

# Proposed: signal confluence requirement

## Why this is a proposal, not a direct ship

Same logic as the passive-entries proposal: this changes when a signal
gets to the trade-placement layer in `live_trader.py`. Behavior change
on the live path. Not HIGH_RISK_FILES but deserves explicit sign-off
before Sunday's kickstart.

## What it changes

**Today**: `find_latest_signal` returns the first valid signal a
strategy emits. Trader fires on that single signal alone.

**Proposed**: when the strategy is in autonomous mode, require the
signal to be confirmed by ≥1 of three confluence factors. If none
confirm, skip:

1. **Volume confluence**: bar volume > 1.5 × 20-bar moving-average
   volume at signal time. Indicates real flow behind the move.
2. **Volatility expansion**: ATR(5) > 1.2 × ATR(50). Signals are more
   reliable when volatility is rising into the setup, not collapsing.
3. **Cross-strategy agreement**: another strategy in the same scan
   produces a same-direction signal on the same symbol. Reduces
   single-strategy noise.

Per the original P1 backlog item:
> Why: lone signals fired in noisy tape today. A signal confirmed by
> ≥1 of: volume above 1.5× MA, ATR expansion, or another strategy
> showing same direction is more reliable.

## Implementation sketch

New helper in `live_trader.py` (or `tools/signal_confluence.py` if we
want it isolated):

```python
def has_confluence(bars, signal, peer_signals=None) -> tuple[bool, str]:
    """Return (passes, reason). Bars are the same DataFrame the
    strategy ran on; peer_signals is a list of signals from other
    strategies in the same scan for the same symbol."""

    last_idx = bars.index.get_loc(signal["date"])  # signal-time bar

    # Volume check
    vol_ma = bars["Volume"].rolling(20).mean().iloc[last_idx]
    vol_now = bars["Volume"].iloc[last_idx]
    vol_ok = vol_now > 1.5 * vol_ma if vol_ma > 0 else False

    # ATR expansion check
    atr5 = _atr(bars, 5).iloc[last_idx]
    atr50 = _atr(bars, 50).iloc[last_idx]
    atr_ok = atr5 > 1.2 * atr50 if atr50 > 0 else False

    # Cross-strategy check
    side = signal["side"]
    cross_ok = any(p["side"] == side for p in (peer_signals or [])
                   if p is not signal)

    if vol_ok or atr_ok or cross_ok:
        reasons = []
        if vol_ok: reasons.append(f"vol {vol_now/vol_ma:.1f}x MA")
        if atr_ok: reasons.append(f"ATR5/ATR50={atr5/atr50:.1f}x")
        if cross_ok: reasons.append("cross-strategy agree")
        return True, "+".join(reasons)
    return False, "no confluence (vol+atr+cross all fail)"
```

Caller in `scan_once`:

```python
# After the strategy returns a signal but before place_bracket:
if AUTONOMOUS_MODE:
    confluence_ok, reason = has_confluence(bars, signal,
                                            peer_signals=other_signals_today)
    if not confluence_ok:
        _record_shadow_for_unvalidated(db, label, symbol, signal,
            conviction, f"no_confluence: {reason}")
        continue  # skip to next strategy
```

## Tradeoff

**Pro**: cuts false signals, especially in the thin/choppy regimes
that produced the 4/29 disaster. Each filter individually reduces fire
count by ~30-50%; OR-ing three of them keeps most real signals while
gating the worst.

**Con**: reduces trade frequency, which matters for the cost equation.
If we cut from 4 trades/day to 2 trades/day but each fired trade has
+0.5R higher expectancy, NET P&L improves. If we cut from 1 trade/day
to 0.4, that hurts (no trade is a -$26 day).

**Calibration**: should be measured. After ~30 live signals with vs
without confluence applied, compare hit rate and expectancy. The
implementation should let CIO toggle confluence on/off via a
risk_limits.yaml flag so we can A/B.

## Compatibility with #8 (passive entries)

These two changes compose well:
- Confluence reduces signal count to high-quality only
- Passive entries reduce slippage on the high-quality signals that fire

Both should be opt-in per strategy. For gap_fill family, both ON.
For trend-following (wide_session_drive when validated), confluence ON
but passive entries OFF.

## Recommended ship sequence

1. CC/user reviews this proposal alongside #8
2. Add `has_confluence` helper in `tools/signal_confluence.py`
3. Add `risk_limits.yaml:autonomous.require_confluence: true` flag
4. Wire into `scan_once` behind the flag (default false initially)
5. Run shadow comparison: log every signal's confluence verdict
   without actually gating — accumulate data for ~1 week
6. After data confirms confluence-passing signals have higher OOS-vs-live
   match, flip flag to true

## Status

**PROPOSED.** Not implemented in code. Cowork has the design ready; CC
or the user makes the ship call.
