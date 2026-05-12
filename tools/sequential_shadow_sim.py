"""Sequential shadow simulator — applies production gates between trades.

The per-trade exec_mirror in `tools/exec_mirror.py` answers "what would
this signal have realized?" but it answers it independently for every
signal. Production reality has SEQUENTIAL GATES:

  * 15-min post-stop cooldown — after a stop_hit, no new entries for
    15 minutes (any cell). This is the trader's `_skipped_cooldown`
    counter — anti-tilt protection.
  * 8-trade daily count cap — autonomous mode stops opening new trades
    after 8 fills in a single trading day (17:00 CT → 17:00 CT window).
  * Daily profit cap — at +$600 day P&L, production flattens and halts
    for the rest of the session (Combine consistency rule).
  * Same-cell cooldown — once a cell is in a trade, it can't fire
    another signal until the current position closes.

Shadow recording captures every signal regardless of these gates. To
build an apples-to-apples comparison with production, we replay the
day chronologically and mark each shadow as `would_fire` or
`blocked_by_<gate>`.

Built 2026-05-12 in response to the user's "tie shadow as close to
real system as possible" directive.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional


# Production gate parameters (mirrored from scripts/live_trader.py +
# hooks/risk_gate.py). Updating these here keeps the sequential simulator
# aligned with whatever the trader uses.
POST_STOP_COOLDOWN_MINUTES = 15
DAILY_TRADE_COUNT_CAP = 8
DAILY_PROFIT_CAP_USD_COMBINE = 600.0


@dataclass
class ShadowSignal:
    """Mirrors a row from `state.shadow_trades` (plus its exec_mirror
    outcome). Inputs to the sequential simulator."""
    id: int
    ts_signal: datetime
    symbol: str
    strategy: str
    side: str
    risk_usd: float
    exec_mirror_outcome: Optional[str]   # stop_hit | profit_lock | hard_flatten ...
    exec_mirror_pnl_r: Optional[float]


@dataclass
class GatedShadow:
    """Output: a signal with its production-eligibility annotation."""
    signal: ShadowSignal
    would_fire: bool
    block_reason: Optional[str]
    cumulative_pnl_usd_after: float  # day P&L after this signal's contribution


def simulate_day(
    shadows: list[ShadowSignal],
    *,
    daily_profit_cap_usd: float = DAILY_PROFIT_CAP_USD_COMBINE,
    daily_trade_count_cap: int = DAILY_TRADE_COUNT_CAP,
    post_stop_cooldown_minutes: int = POST_STOP_COOLDOWN_MINUTES,
) -> list[GatedShadow]:
    """Walk shadows chronologically; apply gates; return annotated list.

    Assumes `shadows` are already sorted by ts_signal and all fall
    within a single trading day (17:00 CT yesterday → 17:00 CT today).
    """
    shadows = sorted(shadows, key=lambda s: s.ts_signal)
    out: list[GatedShadow] = []
    fired_count = 0
    cumulative_pnl = 0.0
    halt_until: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    in_trade_until_by_cell: dict[str, datetime] = {}

    for sig in shadows:
        block_reason: Optional[str] = None

        if halt_until is not None and sig.ts_signal < halt_until:
            block_reason = f"daily_profit_cap_reached(+${daily_profit_cap_usd:.0f})"

        elif cooldown_until is not None and sig.ts_signal < cooldown_until:
            block_reason = (f"post_stop_cooldown ({post_stop_cooldown_minutes}min "
                             f"until {cooldown_until.strftime('%H:%M')})")

        elif fired_count >= daily_trade_count_cap:
            block_reason = f"daily_trade_count_cap({daily_trade_count_cap})"

        else:
            # Cell-busy check
            cell_key = f"{sig.symbol}_{sig.strategy}_{sig.side}"
            busy_until = in_trade_until_by_cell.get(cell_key)
            if busy_until is not None and sig.ts_signal < busy_until:
                block_reason = (f"cell_in_trade(until {busy_until.strftime('%H:%M')})")

        would_fire = block_reason is None

        if would_fire:
            fired_count += 1
            # Estimate trade P&L from exec_mirror
            pnl_usd = 0.0
            if sig.exec_mirror_pnl_r is not None and sig.risk_usd:
                pnl_usd = float(sig.exec_mirror_pnl_r) * float(sig.risk_usd)
            cumulative_pnl += pnl_usd

            # If this trade was a stop, trigger post-stop cooldown
            if sig.exec_mirror_outcome == "stop_hit":
                cooldown_until = sig.ts_signal + timedelta(
                    minutes=post_stop_cooldown_minutes)

            # Estimate hold duration for cell-busy — assume avg trade lasts
            # 30 min for sequential blocking purposes. This is approximate;
            # exact resolution would require ts_resolved per shadow.
            cell_key = f"{sig.symbol}_{sig.strategy}_{sig.side}"
            in_trade_until_by_cell[cell_key] = sig.ts_signal + timedelta(minutes=30)

            # Daily profit cap check (after adding this trade)
            if cumulative_pnl >= daily_profit_cap_usd:
                halt_until = sig.ts_signal + timedelta(days=2)  # halt rest of day+

        out.append(GatedShadow(
            signal=sig,
            would_fire=would_fire,
            block_reason=block_reason,
            cumulative_pnl_usd_after=cumulative_pnl,
        ))

    return out


def aggregate_results(gated: list[GatedShadow]) -> dict:
    """Summary stats over a day's gated shadows.

    Returns:
      {
        n_total: int,
        n_fired: int,
        n_blocked_by_<reason>: int (per reason),
        realistic_day_pnl_usd: float (sum of fired exec_mirror $ outcomes),
        end_of_day_pnl_usd: float,
        first_block: ts (when gates started filtering, if any)
      }
    """
    summary = {
        "n_total": len(gated),
        "n_fired": sum(1 for g in gated if g.would_fire),
        "realistic_day_pnl_usd": (gated[-1].cumulative_pnl_usd_after
                                    if gated else 0.0),
    }
    block_reasons: dict[str, int] = {}
    for g in gated:
        if not g.would_fire and g.block_reason:
            # Bucket the reason (the dynamic suffix in some reasons makes
            # naive grouping noisy; bucket on the leading word).
            key = g.block_reason.split("(")[0].strip()
            block_reasons[key] = block_reasons.get(key, 0) + 1
    summary["n_blocked"] = sum(block_reasons.values())
    summary["blocked_by"] = block_reasons
    return summary


def trading_day_key(ts_utc: datetime) -> str:
    """Topstep trading day boundary = 17:00 CT (= 22:00 UTC in CDT,
    23:00 UTC in CST). Returns 'YYYY-MM-DD_afterCT17' anchored at the
    most recent boundary before `ts_utc`."""
    try:
        from zoneinfo import ZoneInfo
        ts_ct = ts_utc.astimezone(ZoneInfo("America/Chicago"))
    except Exception:
        ts_ct = ts_utc - timedelta(hours=5)
    # If hour >= 17, current trading day is today's date.
    # Else, it's yesterday's date.
    if ts_ct.hour >= 17:
        d = ts_ct.date()
    else:
        d = (ts_ct - timedelta(days=1)).date()
    return d.isoformat()
