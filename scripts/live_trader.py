"""Layer 1 minimal-knife trader.

The simple, reliable execution layer. Reads validated cells from the
brain (state/strategy_validation.json), trades them via Topstep direct
API, halts on hard DLL. Nothing else.

What this DOES:
  - Read live_allowlist from state/strategy_validation.json
  - For each (strategy, symbol, session, side) cell, fetch bars + run strategy
  - On signal: place bracket (entry-limit + stop-limit + target-limit)
  - Verify protective legs working after entry fills
  - Force-close any position whose unrealized loss exceeds per-trade cap
  - Halt for the day on DLL breach

What this does NOT do (per the simplification):
  - Multi-tier strategy roster, cell allowlist, time windows (brain handles)
  - Defensive ladder, trailing profit lock, multiple safety floors
  - Orphan cleanup, misdirected leg detection, grace periods
  - Snapshot freshness gates, autonomy guardrails, agent integration
  - Memory, lessons, validation pipeline (those run separately as the brain)

The brain (Layer 2) is unchanged. This file replaces auto_trader.py
in production. The 2,900-line auto_trader.py is preserved as
auto_trader_v1_complex.py for reference.

USAGE:
  python -m scripts.live_trader              # live continuous loop
  python -m scripts.live_trader --once       # single scan + exit
  python -m scripts.live_trader --dry-run    # signals + decisions, no orders
  python -m scripts.live_trader --paper      # paper-mode (bars, signals, simulated fills)

Environment:
  FUND_MODE=live|paper          (paper = no orders placed)
  PROJECTX_*                    (broker credentials)
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
load_dotenv()

# Project root
_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)
sys.path.insert(0, str(_HERE))

from tools.projectx_client import (
    get_client, get_account_id, ProjectXError,  # noqa: E402
)
from state.db import get_db  # noqa: E402


# ────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────

SCAN_INTERVAL_SEC = 300          # 5-minute cadence
POSITION_POLL_SEC = 30            # sub-minute poll for per-trade cap / trailing-lock.
                                  # 2026-05-13 fix: the previous "$150 per-trade cap"
                                  # fired only on the 5-min scan tick. A position could
                                  # blow past the cap in thin tape before the next scan
                                  # — the 2026-05-12 GC long went from +$70 to −$210
                                  # in a single scan window, then to −$640 by the next.
                                  # A separate background thread now polls
                                  # tools/profit_protect.check_and_close every 30s so
                                  # the cap fires within ~30s of being exceeded.
LOOKBACK_BARS = 6                 # find_latest_signal cutoff (30 min on 5m bars)
PER_TRADE_LOSS_CAP_USD = 150.0    # force-close if unrealized < -this
SAME_SYMBOL_COOLDOWN_MIN = 45     # don't re-fire same symbol within window
MAX_TRADES_PER_DAY = 8            # hard cap on entries per UTC day
MIN_SIGNAL_R_TICKS = 6            # reject signals whose stop OR target distance is < N ticks
                                  # (rationale: place_bracket adds a 5-tick marketable-limit
                                  # buffer; if the strategy R-distance is smaller than the buffer,
                                  # the trade can't escape the buffer for a profit and may
                                  # degenerate into an orphan-leg fill. 2026-05-10 incident.)
MAX_SIGNAL_RISK_USD = 150.0       # reject signals whose stop-distance × tick_value × qty
                                  # exceeds this dollar amount. Symmetric with the per-trade
                                  # loss cap. 2026-05-12/13 incident: GC long fired with a
                                  # 6.4-point ($640) stop — the only floor was Topstep's
                                  # $1,000 DLL, so a single trade chewed 64% of the daily
                                  # limit. Equivalent of `per_trade_risk_pct_of_equity: 0.005`
                                  # (50 bps on $30K active risk capital). Pattern B —
                                  # calibration mismatch (strategy stop assumed a regime
                                  # where 64 ticks was reasonable; thin overnight tape made
                                  # it the entire account).
SKIP_TARGET_LEG = True            # 2026-05-11 evening: enabled per user direction after
                                  # confirming the broker target-fill anomaly. Target LIMIT
                                  # orders were auto-filling within ~100ms at next-available
                                  # market price (limit price essentially ignored). Workaround:
                                  # place ONLY entry + stop. Position runs until stop fires,
                                  # per-trade loss cap ($150), or manual flatten.
                                  # See vault/research/analysis/2026-05-11_broker_target_fill_anomaly.md
SHADOW_ON_HALT = True             # 2026-05-12: when halt is active, continue scanning + record
                                  # what would have been placed as shadow trades. Lets us collect
                                  # validation data during the daily-profit-cap halt window
                                  # (~21h) instead of going dark. Shadow trades land in the
                                  # `shadow_trades` table and get resolved by
                                  # scripts/shadow_trade_resolver.py at next preflight.
HALT_FILE = _HERE / "state" / "live_trader_halt"   # touch to halt; remove to resume


# Pure utility helpers — extracted to tools/trader_utils.py 2026-05-08.
# Re-imported with leading-underscore aliases so existing call-sites and
# tests (which use lt._foo) keep working.
from tools.trader_utils import (
    _load_yaml,
    _now_utc,
    _utcnow_iso,
    is_sunday_reopen_blackout,
)


def _log(msg: str) -> None:
    print(f"[{_now_utc().strftime('%Y-%m-%d %H:%M:%S')} UTC] {msg}", flush=True)


# ────────────────────────────────────────────────────────────────
# Halt + DLL gates
# ────────────────────────────────────────────────────────────────

def is_halted() -> tuple[bool, str]:
    """Manual halt via touch-file OR config halt timestamp."""
    if HALT_FILE.exists():
        return True, "manual halt file present"
    risk = _load_yaml("config/risk_limits.yaml")
    halt_ts = risk.get("hard_rules", {}).get("trading_halt_until", "")
    if halt_ts:
        try:
            halt_dt = datetime.fromisoformat(str(halt_ts).replace("Z", "+00:00"))
            if halt_dt > _now_utc():
                return True, f"trading_halt_until={halt_ts}"
        except Exception:
            pass
    if risk.get("hard_rules", {}).get("trading_halted"):
        return True, "trading_halted=true"
    return False, ""


def dll_breached(snap: dict) -> tuple[bool, str]:
    """True if today's realized P&L breaches the INTERNAL daily-loss
    target (tighter floor; per-user direction "agents target THIS, not
    Topstep's"). Falls through to Topstep's `daily_loss_limit_usd` as a
    backstop if the internal target is missing.

    2026-05-13 fix: prior version read only `daily_loss_limit_usd`
    (= Topstep's $1,000 hard limit). At -$683 day P&L the gate returned
    False and the trader fired a third bracket, taking the account to
    -$1,005 and triggering Topstep server-side canTrade=0. See
    vault/lessons/2026-05-13_overnight_dll_breach.md.
    """
    acct = _load_yaml("config/risk_limits.yaml").get("account", {}) or {}
    internal = acct.get("internal_dll_target_usd")
    topstep = float(acct.get("daily_loss_limit_usd", 1000))
    # Internal first; fall through to Topstep if internal is missing.
    # Treat 0 or None as "not configured" so a wiped value can't silently
    # disable the gate (Pattern A defense).
    dll = float(internal) if internal not in (None, 0, 0.0) else topstep
    source = "internal_dll" if internal not in (None, 0, 0.0) else "topstep_dll"
    realized = float(snap.get("realized_pl_day_usd") or 0)
    if realized <= -dll:
        return True, f"{source} breach: realized_day=${realized:+.2f} <= -${dll:.0f}"
    return False, ""


# ────────────────────────────────────────────────────────────────
# Snapshot capture (heartbeat + DLL)
# ────────────────────────────────────────────────────────────────
# capture_snapshot extracted to tools/snapshot_writer.py 2026-05-08
# (continuous trim, mirrors the compute_unrealized extraction). The
# function body is unchanged — degraded-heartbeat fallback preserved.
from tools.snapshot_writer import capture_snapshot  # noqa: E402

# compute_unrealized extracted to tools/unrealized_pnl.py 2026-05-08 (continuous trim).
from tools.unrealized_pnl import compute_unrealized  # noqa: E402


# ────────────────────────────────────────────────────────────────
# Signal-risk + gate functions (LAST-MILE SAFETY FLOORS)
# ────────────────────────────────────────────────────────────────
# All BRAIN logic (load_live_cells, session_now_utc, current_regime,
# cell_passes_regime_filter, news_proximity_for, find_latest_signal,
# fetch_bars) moved to tools/brain_logic.py + scripts/brain_signaler.py
# on 2026-05-13 per the standing rule "trader places, brain decides."


def compute_signal_risk_usd(sig: dict, symbol: str, qty: int = 1) -> float | None:
    """Compute the dollar risk of a signal: stop_ticks × tick_value × qty.

    Returns None when economics can't be computed (missing price/stop,
    invalid tick, missing tick_value). Callers MUST treat None as
    'unknown — refuse to gate on it' (fail closed).
    """
    if sig.get("price") is None or sig.get("stop") is None:
        return None
    tick = _tick_size(symbol)
    if tick <= 0:
        return None
    tval = _tick_value(symbol)
    if tval <= 0:
        return None
    stop_ticks = abs(float(sig["price"]) - float(sig["stop"])) / tick
    return stop_ticks * tval * max(1, int(qty))


def signal_passes_max_risk_gate(sig: dict, symbol: str, qty: int = 1,
                                  max_risk_usd: float = MAX_SIGNAL_RISK_USD,
                                  ) -> tuple[bool, str]:
    """Reject signals whose stop-distance dollar risk exceeds max_risk_usd.

    Symmetric with the per-trade loss cap. Pattern B defense for the
    2026-05-12/13 GC incident: a strategy returned a 64-tick stop and
    the trader placed it unchecked, blowing through the $150 per-trade
    cap (which only fires AFTER fill, on a 5-min scan tick) and ending
    up at the broker stop for -$640.

    Returns (passes, reason). On reject, reason is human-readable.

    Default-deny: missing tick_value or stop → reject. Treating a missing
    value as 'unknown ok' would replicate the Pattern A failure pattern.
    """
    risk_usd = compute_signal_risk_usd(sig, symbol, qty)
    if risk_usd is None:
        return False, "missing price/stop or tick economics — refusing to gate"
    if risk_usd > max_risk_usd:
        tick = _tick_size(symbol)
        tval = _tick_value(symbol)
        stop_ticks = abs(float(sig["price"]) - float(sig["stop"])) / tick
        return False, (f"risk too large (${risk_usd:.0f} > ${max_risk_usd:.0f} cap; "
                        f"stop={stop_ticks:.1f}t × ${tval:.2f}/tick × {qty}ct)")
    return True, ""


def projected_dll_breach(snap: dict, signal_risk_usd: float
                          ) -> tuple[bool, str]:
    """True if (current day P&L − this signal's worst-case loss) would
    cross the internal DLL target. Pre-trade projection — mirrors
    hooks/risk_gate._check_combine_defensive_ladder's projection logic
    but lives in the live_trader path (auto_trader/SDK hook isn't
    invoked here).

    The defensive ladder's warn/restrict tiers are advisory only (target
    prompt-level discipline). The lockdown tier (= internal_dll_target)
    is the actual hard halt — and we already enforce it post-trade in
    dll_breached(). This function adds the PRE-TRADE projection so we
    don't fire a signal that would necessarily push us past lockdown.

    Uses day P&L = realized + unrealized (matches the hook). Falls
    through to Topstep DLL if internal is missing or zero — same
    Pattern A defense as dll_breached().
    """
    if signal_risk_usd <= 0:
        return False, ""
    acct = _load_yaml("config/risk_limits.yaml").get("account", {}) or {}
    internal = acct.get("internal_dll_target_usd")
    topstep = float(acct.get("daily_loss_limit_usd", 1000))
    dll = float(internal) if internal not in (None, 0, 0.0) else topstep
    source = "internal_dll" if internal not in (None, 0, 0.0) else "topstep_dll"
    realized = float(snap.get("realized_pl_day_usd") or 0)
    unrealized = float(snap.get("unrealized_pl_usd") or 0)
    day_pl = realized + unrealized
    projected = day_pl - signal_risk_usd
    if projected <= -dll:
        return True, (f"{source} projection: day_pl ${day_pl:+.2f} − "
                        f"${signal_risk_usd:.0f} worst-case = ${projected:+.2f} "
                        f"<= -${dll:.0f}")
    return False, ""


def signal_passes_min_r_gate(sig: dict, symbol: str,
                              min_r_ticks: int = MIN_SIGNAL_R_TICKS,
                              ) -> tuple[bool, str]:
    """Reject signals whose stop-distance OR target-distance is below
    min_r_ticks. Returns (passes, reason). On reject, reason is a
    human-readable diagnostic string.

    Rationale (2026-05-10 incident): place_bracket() places the entry
    as a marketable limit with a 5-tick slippage buffer. When the
    strategy's R-distance is smaller than the buffer, the trade can't
    escape the buffer for a profit; worse, when the strategy stop is
    closer than the buffer's full range to entry, a single tick of
    adverse movement can fire the stop leg alone (entry limit never
    fills), opening an unintended reversed position via the orphan-leg
    pathway. Block both before placement.
    """
    if sig.get("price") is None or sig.get("stop") is None:
        return False, "missing price or stop"
    tick = _tick_size(symbol)
    if tick <= 0:
        return False, f"invalid tick size for {symbol}"
    sig_price = float(sig["price"])
    sig_stop = float(sig["stop"])
    stop_ticks = abs(sig_price - sig_stop) / tick
    target_val = sig.get("target")
    target_ticks = (abs(sig_price - float(target_val)) / tick
                    if target_val is not None else float("inf"))
    if stop_ticks < min_r_ticks:
        return False, (f"stop too close ({stop_ticks:.1f}t < {min_r_ticks}t min)")
    if target_ticks < min_r_ticks:
        return False, (f"target too close ({target_ticks:.1f}t < {min_r_ticks}t min)")
    return True, ""


# ────────────────────────────────────────────────────────────────
# Bracket placement (extracted to tools/bracket_placement.py 2026-05-13)
# ────────────────────────────────────────────────────────────────

# Tick math extracted to tools/trader_utils.py
from tools.trader_utils import _tick_size, _tick_value, _round_to_tick  # noqa: E402

# Bracket placement + fill-confirm + stop-verify + emergency-flatten all
# live in tools/bracket_placement.py now. Re-exported here so existing
# tests + scan_once call sites keep working unchanged.
from tools.bracket_placement import (  # noqa: E402
    FILL_WAIT_TIMEOUT_S,
    FILL_WAIT_POLL_S,
    _position_signature,
    _position_avg_price,
    _verify_stop_landed,
    _emergency_flatten_position,
    _wait_for_entry_fill,
    place_bracket as _place_bracket_impl,
)


def place_bracket(client, account_id, symbol: str, signal: dict,
                  qty: int = 1, dry_run: bool = False) -> dict:
    """Thin wrapper around tools.bracket_placement.place_bracket that
    threads the trader's _log function and SKIP_TARGET_LEG setting."""
    return _place_bracket_impl(
        client, account_id, symbol, signal,
        qty=qty, dry_run=dry_run,
        log_fn=_log, skip_target_leg=SKIP_TARGET_LEG,
    )


# ────────────────────────────────────────────────────────────────
# Per-trade loss-cap enforcement (extracted to tools/loss_cap.py 2026-05-13)
# ────────────────────────────────────────────────────────────────

from tools.loss_cap import enforce_loss_cap as _enforce_loss_cap_impl  # noqa: E402


def enforce_loss_cap(client, account_id) -> int:
    """Thin wrapper threading the trader's _log + PER_TRADE_LOSS_CAP_USD."""
    return _enforce_loss_cap_impl(
        client, account_id,
        per_trade_cap_usd=PER_TRADE_LOSS_CAP_USD,
        log_fn=_log,
    )


# ────────────────────────────────────────────────────────────────
# Orphan-bracket cleanup (extracted to tools/orphan_cleanup.py 2026-05-13)
# ────────────────────────────────────────────────────────────────

from tools.orphan_cleanup import (  # noqa: E402
    ORPHAN_GRACE_SEC,
    cleanup_orphan_brackets as _cleanup_orphan_brackets_impl,
)


def cleanup_orphan_brackets(client, account_id) -> int:
    """Thin wrapper threading the trader's _log."""
    return _cleanup_orphan_brackets_impl(client, account_id, log_fn=_log)


# Cooldown / daily-count queries extracted to tools/trade_state.py 2026-05-08.
from tools.trade_state import recent_thesis_for as _recent_thesis_for_impl  # noqa: E402
from tools.trade_state import todays_trade_count  # noqa: E402

def recent_thesis_for(symbol: str, minutes: int = SAME_SYMBOL_COOLDOWN_MIN) -> bool:
    return _recent_thesis_for_impl(symbol, minutes)


# ────────────────────────────────────────────────────────────────
# Main scan loop — queue consumer
# ────────────────────────────────────────────────────────────────
# The brain (scripts/brain_signaler.py) emits signals to
# state/pending_signals.json. This trader reads them, applies
# last-mile safety gates, and places brackets. The legacy
# scan_once strategy-execution path was deleted 2026-05-13 as part
# of the brain/trader split.


def consume_pending_signals(*, dry_run: bool = False,
                              paper: bool = False) -> dict:
    """Queue-consumer path. Reads signals from `tools.signal_queue`,
    applies last-mile safety gates, and places brackets.

    The brain (`scripts/brain_signaler.py`) is responsible for upstream
    strategy execution, session filtering, regime filtering, and
    cooldown — that work no longer happens in the trader.

    This function is what `--use-queue` enables. The legacy `scan_once`
    (strategy execution + decisioning) remains as the fallback path for
    parallel rollout. Once we verify a clean session on this path, the
    legacy code can be removed.

    The safety gates here MUST stay even though the brain in theory
    pre-validates — they're defense-in-depth against brain bugs (a
    miscalibrated cell or stale config could emit a signal that should
    be blocked).
    """
    from tools.signal_queue import consume as _consume_queue
    summary = {"consumed": 0, "placed": 0, "blocked": 0, "shadow": 0,
                "errors": 0, "skipped_in_trade": 0, "skipped_cooldown": 0,
                "skipped_daily_cap": 0}

    halted, reason = is_halted()
    shadow_only = halted and SHADOW_ON_HALT and not paper
    if halted and not shadow_only:
        _log(f"HALTED: {reason}")
        return {"status": "halted", "reason": reason}
    if shadow_only:
        _log(f"HALTED (shadow mode active — no broker writes): {reason}")

    if is_sunday_reopen_blackout(_now_utc()):
        _log("Sunday-reopen blackout (17:00-17:30 ET): skipping new entries")
        return {"status": "sunday_reopen_blackout"}

    try:
        client = get_client()
        account_id = get_account_id()
    except Exception as e:
        _log(f"broker unavailable: {e}")
        return {"status": "broker_unavailable", "error": str(e)}

    snap = capture_snapshot(client, account_id)
    if snap and not snap.get("can_trade", True):
        _log("can_trade=false; halt scan")
        return {"status": "broker_can_trade_false"}
    if snap:
        breached, why = dll_breached(snap)
        if breached:
            _log(f"DLL BREACH: {why}")
            return {"status": "dll_halt", "reason": why}

    # 3:10 PM CT hard-flatten enforcement (same as scan_once).
    if not dry_run and not paper:
        from tools.hard_flatten_clock import (enforce_hard_flatten,
                                                should_block_new_entries)
        _hf_result = enforce_hard_flatten(client, account_id, log_fn=_log)
        if _hf_result["flattened"] or _hf_result["cancelled"]:
            _log(f"  HARD_FLATTEN window={_hf_result['window']}: "
                  f"flattened {len(_hf_result['flattened'])} position(s), "
                  f"cancelled {_hf_result['cancelled']} order(s)")
        if should_block_new_entries():
            _log("  Within 3:10 PM CT closing window — blocking new entries")
            return {"status": "hard_flatten_window", **_hf_result}
        cleanup_orphan_brackets(client, account_id)

    open_pos = (snap.get("open_contracts_total") or 0) if snap else 0
    if open_pos > 0:
        _log(f"  {open_pos} open contracts; skipping new entries")
        return {"status": "in_position", **summary}

    today_count = todays_trade_count()
    if today_count >= MAX_TRADES_PER_DAY:
        _log(f"  daily trade cap hit ({today_count}/{MAX_TRADES_PER_DAY})")
        return {"status": "daily_cap_hit", "today_count": today_count,
                **summary}

    signals = _consume_queue()
    if not signals:
        _log("queue: no pending signals")
        return {"status": "empty_queue", **summary}

    _log(f"queue: consumed {len(signals)} signal(s)")
    for sig_obj in signals:
        summary["consumed"] += 1
        symbol = sig_obj.get("symbol", "")
        strat_name = sig_obj.get("strategy", "?")
        side = str(sig_obj.get("side", "")).lower()
        qty = int(sig_obj.get("qty") or 1)

        # Trader-shaped signal dict (keys match what gates expect)
        sig = {
            "side": side,
            "price": sig_obj.get("entry_price"),
            "stop": sig_obj.get("stop_price"),
            "target": sig_obj.get("target_price"),
            "reason": sig_obj.get("notes", ""),
        }

        # Cooldown is a brain concern in principle, but defense-in-depth:
        # the trader checks too in case the brain double-emits.
        if recent_thesis_for(symbol):
            _log(f"  {symbol} {strat_name} {side}: skipped (recent thesis)")
            summary["skipped_cooldown"] += 1
            continue

        ok, reason = signal_passes_min_r_gate(sig, symbol)
        if not ok:
            _log(f"  {symbol} {strat_name} {side} blocked: {reason}")
            summary["blocked"] += 1
            continue
        ok, reason = signal_passes_max_risk_gate(sig, symbol, qty=qty)
        if not ok:
            _log(f"  {symbol} {strat_name} {side} blocked: {reason}")
            summary["blocked"] += 1
            continue
        if snap:
            signal_risk = compute_signal_risk_usd(sig, symbol, qty=qty)
            if signal_risk is not None:
                breach, breach_why = projected_dll_breach(snap, signal_risk)
                if breach:
                    _log(f"  {symbol} {strat_name} {side} blocked: {breach_why}")
                    summary["blocked"] += 1
                    continue

        try:
            if sig_obj.get("shadow_only") or shadow_only or paper:
                # Shadow / paper / brain-flagged-experimental: record but
                # don't place. Use the same shadow_trades table as scan_once
                # for consistency with the validation pipeline.
                try:
                    tick_v = _tick_size(symbol)
                    risk_usd = None
                    if sig.get("stop") is not None:
                        risk_ticks = abs(float(sig["price"]) - float(sig["stop"])) / tick_v
                        risk_usd = compute_signal_risk_usd(sig, symbol, qty=qty)
                    get_db().record_shadow_trade(
                        agent="live_trader_queue",
                        symbol=symbol, strategy=strat_name, side=side,
                        entry_price=float(sig["price"]),
                        stop_price=float(sig["stop"]),
                        target_price=float(sig.get("target") or sig["price"]),
                        shadow_reason=("brain_shadow_only"
                                          if sig_obj.get("shadow_only")
                                          else "halt_active"),
                        risk_usd=risk_usd,
                        notes=f"queue_id={sig_obj.get('id', '?')[:8]}",
                    )
                    _log(f"  SHADOW recorded: {symbol} {strat_name} {side}")
                    summary["shadow"] += 1
                except Exception as e:
                    _log(f"  shadow record failed: {e}")
                    summary["errors"] += 1
            else:
                result = place_bracket(client, account_id, symbol, sig,
                                         qty=qty, dry_run=dry_run)
                if result.get("status") in ("submitted", "dry_run"):
                    summary["placed"] += 1
                else:
                    summary["errors"] += 1
        except Exception as e:
            _log(f"  place_bracket exception: {e}")
            summary["errors"] += 1

    _log(f"  queue-summary: {summary}")
    return summary


def _position_polling_loop(stop_event, dry_run: bool, paper: bool,
                            interval_sec: int = POSITION_POLL_SEC) -> None:
    """Background thread: poll open positions every interval_sec and
    force-close any that breach the per-trade loss cap or trailing-lock
    tiers via tools/profit_protect.check_and_close.

    This runs in PARALLEL with the main 5-min scan loop so the loss cap
    fires within ~30s of being exceeded instead of waiting for the next
    scan tick. Dry-run and paper modes skip the polling entirely (no
    broker writes).

    Safe to run alongside scan_once's own call to check_and_close — both
    paths are idempotent (broker market-IOC orders fire-and-forget; a
    second close on a flat position is a no-op).
    """
    if dry_run or paper:
        return
    from tools.profit_protect import check_and_close
    while not stop_event.is_set():
        try:
            client = get_client()
            account_id = get_account_id()
            check_and_close(client, account_id, log_fn=_log)
        except Exception as e:
            _log(f"position-poll error: {type(e).__name__}: {e}")
        stop_event.wait(interval_sec)


def main() -> int:
    p = argparse.ArgumentParser(prog="live_trader")
    p.add_argument("--once", action="store_true", help="single scan + exit")
    p.add_argument("--dry-run", action="store_true",
                   help="consume signals + apply gates, no broker orders")
    p.add_argument("--paper", action="store_true",
                   help="paper-mode (no broker orders)")
    p.add_argument("--interval", type=int, default=SCAN_INTERVAL_SEC)
    args = p.parse_args()

    if os.environ.get("FUND_MODE", "live").lower() == "paper":
        args.paper = True

    if args.once:
        consume_pending_signals(dry_run=args.dry_run, paper=args.paper)
        return 0

    _log(f"=== live_trader started: interval={args.interval}s, "
          f"dry_run={args.dry_run}, paper={args.paper} ===")

    # Sub-minute position polling thread for the per-trade loss cap.
    import threading
    poll_stop = threading.Event()
    poll_thread = None
    if not args.dry_run and not args.paper:
        poll_thread = threading.Thread(
            target=_position_polling_loop,
            args=(poll_stop, args.dry_run, args.paper),
            kwargs={"interval_sec": POSITION_POLL_SEC},
            daemon=True,
            name="position-poller",
        )
        poll_thread.start()
        _log(f"position-poller started (interval={POSITION_POLL_SEC}s)")

    try:
        while True:
            try:
                consume_pending_signals(dry_run=args.dry_run, paper=args.paper)
            except KeyboardInterrupt:
                _log("interrupted; exiting")
                return 0
            except Exception as e:
                _log(f"scan error (will retry): {type(e).__name__}: {e}")
            time.sleep(args.interval)
    finally:
        poll_stop.set()
        if poll_thread is not None:
            poll_thread.join(timeout=5)


if __name__ == "__main__":
    sys.exit(main())
