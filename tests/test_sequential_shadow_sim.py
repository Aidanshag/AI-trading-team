"""Tests for tools/sequential_shadow_sim — the gate-aware simulator that
filters which shadow signals would have actually fired in production."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tools.sequential_shadow_sim import (
    ShadowSignal, simulate_day, aggregate_results, trading_day_key,
    DAILY_TRADE_COUNT_CAP, POST_STOP_COOLDOWN_MINUTES,
)


def _sig(minute: int, *, symbol: str = "GC", strategy: str = "fvg",
          side: str = "long", risk_usd: float = 100.0,
          em_outcome: str = "profit_lock",
          em_pnl_r: float = 0.0,
          sig_id: int = 0) -> ShadowSignal:
    """Build a ShadowSignal anchored at 14:00 UTC + N minutes (well before
    3:10 PM CT). Use a unique cell key by overriding strategy/symbol/side."""
    ts = datetime(2026, 5, 12, 14, 0, tzinfo=timezone.utc) + timedelta(minutes=minute)
    return ShadowSignal(
        id=sig_id, ts_signal=ts, symbol=symbol, strategy=strategy, side=side,
        risk_usd=risk_usd, exec_mirror_outcome=em_outcome,
        exec_mirror_pnl_r=em_pnl_r,
    )


def test_daily_trade_count_cap_blocks_after_N_fires():
    """The 9th distinct-cell signal of the day must be blocked."""
    signals = [
        _sig(i, strategy=f"strat_{i}", sig_id=i)
        for i in range(DAILY_TRADE_COUNT_CAP + 3)
    ]
    gated = simulate_day(signals)
    fired = [g for g in gated if g.would_fire]
    blocked = [g for g in gated if not g.would_fire]
    assert len(fired) == DAILY_TRADE_COUNT_CAP
    assert len(blocked) == 3
    for b in blocked:
        assert "daily_trade_count_cap" in (b.block_reason or "")


def test_post_stop_cooldown_blocks_next_15_minutes():
    """After a stop_hit, the NEXT signals within 15 min are blocked."""
    signals = [
        # T+0: stop_hit fires
        _sig(0, em_outcome="stop_hit", em_pnl_r=-1.0, sig_id=1),
        # T+5: should be blocked by post-stop cooldown
        _sig(5, strategy="other", em_outcome="profit_lock", em_pnl_r=0.1, sig_id=2),
        # T+10: still blocked
        _sig(10, strategy="another", em_outcome="profit_lock", em_pnl_r=0.1, sig_id=3),
        # T+16: cooldown over, should fire
        _sig(16, strategy="postcd", em_outcome="profit_lock", em_pnl_r=0.1, sig_id=4),
    ]
    gated = simulate_day(signals)
    assert gated[0].would_fire is True
    assert gated[1].would_fire is False
    assert "post_stop_cooldown" in (gated[1].block_reason or "")
    assert gated[2].would_fire is False
    assert gated[3].would_fire is True


def test_daily_profit_cap_halts_after_threshold():
    """Once cumulative P&L >= $600, subsequent signals are blocked."""
    # A single big winner that crosses the cap on its own
    signals = [
        _sig(0, em_outcome="profit_lock", em_pnl_r=7.0,
              risk_usd=100.0, sig_id=1),     # +$700 (crosses $600)
        _sig(30, strategy="next", em_outcome="profit_lock",
              em_pnl_r=0.5, risk_usd=100.0, sig_id=2),  # blocked
    ]
    gated = simulate_day(signals)
    assert gated[0].would_fire is True
    assert gated[1].would_fire is False
    assert "daily_profit_cap" in (gated[1].block_reason or "")


def test_cell_in_trade_blocks_same_cell_signal():
    """While a cell has a position open, another signal in the same cell
    must be blocked. Default cell-busy window is 30 min."""
    signals = [
        _sig(0, symbol="GC", strategy="fvg", side="long",
              em_outcome="profit_lock", em_pnl_r=0.5, sig_id=1),
        _sig(10, symbol="GC", strategy="fvg", side="long",
              em_outcome="profit_lock", em_pnl_r=0.5, sig_id=2),
        _sig(35, symbol="GC", strategy="fvg", side="long",
              em_outcome="profit_lock", em_pnl_r=0.5, sig_id=3),
    ]
    gated = simulate_day(signals)
    assert gated[0].would_fire is True
    assert gated[1].would_fire is False
    assert "cell_in_trade" in (gated[1].block_reason or "")
    assert gated[2].would_fire is True


def test_aggregate_returns_realistic_pnl_only_from_fired():
    """The aggregator's day_pnl_usd must reflect ONLY fired trades — not
    the cumulative of all signals."""
    signals = [
        _sig(0, em_outcome="profit_lock", em_pnl_r=1.0,
              risk_usd=100.0, sig_id=1),  # +$100 fires
        _sig(5, strategy="cd_blocked", em_outcome="profit_lock",
              em_pnl_r=10.0, risk_usd=100.0, sig_id=2),  # blocked... no
    ]
    # signal 2 fires since signal 1 wasn't a stop_hit. Both should fire.
    gated = simulate_day(signals)
    summary = aggregate_results(gated)
    assert summary["n_fired"] == 2
    assert summary["realistic_day_pnl_usd"] == 1100.0


def test_trading_day_key_anchors_at_17_CT():
    """Times before 17:00 CT belong to the PREVIOUS day; at/after belong
    to today's date."""
    # 22:00 UTC on 2026-05-12 = 17:00 CT (CDT) — exact boundary; should be
    # today's date.
    boundary = datetime(2026, 5, 12, 22, 0, tzinfo=timezone.utc)
    assert trading_day_key(boundary) == "2026-05-12"
    # 20:00 UTC = 15:00 CT — before the 17:00 boundary — yesterday's date
    before = datetime(2026, 5, 12, 20, 0, tzinfo=timezone.utc)
    assert trading_day_key(before) == "2026-05-11"
