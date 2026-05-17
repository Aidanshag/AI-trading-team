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

SCAN_INTERVAL_SEC = 60           # 1-min cadence — matches brain.SCAN_INTERVAL_SEC.
                                  # 2026-05-17: tightened from 300s after
                                  # finding the mismatch: brain emits every
                                  # 60s, signal TTL is 180s, trader was scanning
                                  # at 300s — most signals expired in the queue
                                  # before the trader picked them up. New
                                  # cadence: avg signal staleness drops from
                                  # ~2:30 min to ~30 sec. consume_pending_signals
                                  # is cheap (queue read + place_bracket per
                                  # signal); no per-symbol bar fetches (brain
                                  # already did those).
POSITION_POLL_SEC = 10            # baseline poll cadence when FLAT.
POSITION_POLL_SEC_IN_TRADE = 1    # tightest reasonable REST cadence when
                                  # a position is OPEN. 2026-05-14: was 2,
                                  # tightened to 1 to halve the worst-case
                                  # latency before profit-lock fires. The
                                  # real eliminator of polling latency is
                                  # the trailing BROKER stop — broker
                                  # processes ticks at microsecond speed.
                                  # See vault/_meta/improvement_backlog.md
                                  # for the WebSocket / real-time-quote
                                  # investigation queued as P0.
                                  # 2026-05-13: 30s initial polling. 2026-05-14:
                                  # tightened to 10s. Then 2026-05-14 (later):
                                  # user observation that 10s was too slow for fast
                                  # tape — peak $61 retraced past $25 floor and we
                                  # only caught it at $12, giving back $49.
                                  # Two-tier polling: 10s when flat (cheap),
                                  # 2s when in-position (paranoid). Trade-off:
                                  # ~5× more API calls on the read path, but only
                                  # WHILE a position is open. Brain still emits at
                                  # 60s — this doesn't affect signal generation.
LOOKBACK_BARS = 6                 # find_latest_signal cutoff (30 min on 5m bars)
PER_TRADE_LOSS_CAP_USD = 150.0    # force-close if unrealized < -this
SAME_SYMBOL_COOLDOWN_MIN = 45     # default — don't re-fire same symbol within window
SAME_SYMBOL_COOLDOWN_OVERRIDES = {  # per-symbol overrides 2026-05-14: smaller-risk
                                      # contracts (micros) get tighter cooldowns since
                                      # the dollar-per-trade ceiling is lower.
    "MGC": 15,                       # micro gold — 1/10 risk of GC, fire 3× more often
}
MAX_TRADES_PER_DAY = 25           # hard cap on entries per TOPSTEP trading day (5pm
                                  # CT to 5pm CT). Raised from 8 → 15 on 2026-05-14,
                                  # then 15 → 25 on 2026-05-15 (user-directed temp
                                  # lift to give the new MES fair_value_gap cell room
                                  # to fire during today's RTH). REVERT to 15 if not
                                  # explicitly kept by user.
                                  # — the new $150 max-risk + $250 internal DLL +
                                  # 30s profit-poll bound downside at ~$300 per day
                                  # even with 15 trades, so the lower count was
                                  # overly conservative and was actively blocking
                                  # MGC trades.
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


# dll_breached extracted to tools/signal_validators.py 2026-05-17.
# Re-exported here so existing call sites and tests (which use
# lt.dll_breached) keep working unchanged.
from tools.signal_validators import dll_breached  # noqa: E402,F401


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


# compute_signal_risk_usd / signal_passes_max_risk_gate /
# projected_dll_breach / signal_passes_min_r_gate all extracted to
# tools/signal_validators.py 2026-05-17. Re-exported so existing call
# sites + tests (which use lt.compute_signal_risk_usd etc.) work unchanged.
from tools.signal_validators import (  # noqa: E402,F401
    compute_signal_risk_usd,
    signal_passes_max_risk_gate,
    projected_dll_breach,
    signal_passes_min_r_gate,
)


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

def recent_thesis_for(symbol: str, minutes: int | None = None) -> bool:
    """Per-symbol cooldown check. Uses SAME_SYMBOL_COOLDOWN_OVERRIDES[symbol]
    if defined, else SAME_SYMBOL_COOLDOWN_MIN, else the explicit `minutes` arg."""
    if minutes is None:
        minutes = SAME_SYMBOL_COOLDOWN_OVERRIDES.get(symbol, SAME_SYMBOL_COOLDOWN_MIN)
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
            # ── SHADOW LOG: outcome-aware cooldown A/B ──
            # Live still uses the flat 45-min (or override). Compare what
            # the new policy_v1 cooldown would have decided. Findings
            # accumulate in vault/research/cooldown_shadow_log.jsonl and
            # we evaluate after N decisions whether to switch live.
            try:
                from tools.cooldown_policy import classify_outcome, cooldown_decision
                from tools.trade_state import _last_trade_for_symbol  # may exist
                last = _last_trade_for_symbol(symbol) if callable(_last_trade_for_symbol) else None
                if last is not None:
                    outcome = classify_outcome(
                        last.get("realized_r"), last.get("exit_reason"))
                    live_cd = SAME_SYMBOL_COOLDOWN_OVERRIDES.get(
                        symbol, SAME_SYMBOL_COOLDOWN_MIN)
                    minutes_since = float(last.get("minutes_since", 0) or 0)
                    decision = cooldown_decision(
                        symbol, live_cooldown_min=live_cd,
                        last_outcome=outcome,
                        minutes_since_last=minutes_since,
                    )
                    import json as _j
                    from datetime import datetime as _dt, timezone as _tz
                    log_path = Path("vault/research/cooldown_shadow_log.jsonl")
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    with log_path.open("a", encoding="utf-8") as _f:
                        _f.write(_j.dumps({
                            "ts": _dt.now(tz=_tz.utc).isoformat(),
                            "symbol": symbol, "strategy": strat_name,
                            **decision,
                        }) + "\n")
            except Exception:
                pass  # shadow logging is best-effort, never blocks trader
            continue

        # Session-aware MIN_SIGNAL_R_TICKS: Asian sessions get a tighter
        # 4-tick floor since true ranges are 30-50% smaller. brain_signaler
        # emits `session` on every queued signal; default falls back to 6t.
        ok, reason = signal_passes_min_r_gate(
            sig, symbol, session=sig_obj.get("session"),
        )
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
                    # ── SHADOW LOG: passive-entry A/B ──
                    # Simulate what a post-only limit at signal_price would
                    # have done over the next 5 minutes. Real entry still
                    # used the marketable-limit path; this is purely
                    # observational. Accumulates in
                    # vault/research/passive_entry_shadow.jsonl.
                    try:
                        from tools.passive_entry_shadow import simulate_passive_entry
                        from tools.bar_fetcher import fetch_bars as _fb
                        from tools.trader_utils import _tick_size as _tsz
                        bars_after = _fb(client, symbol, 1, 6)  # next 6 min
                        ts = _tsz(symbol)
                        if bars_after is not None and ts > 0:
                            shadow = simulate_passive_entry(sig, bars_after, tick_size=ts)
                            import json as _j
                            from datetime import datetime as _dt, timezone as _tz
                            log_path = Path("vault/research/passive_entry_shadow.jsonl")
                            log_path.parent.mkdir(parents=True, exist_ok=True)
                            with log_path.open("a", encoding="utf-8") as _f:
                                _f.write(_j.dumps({
                                    "ts": _dt.now(tz=_tz.utc).isoformat(),
                                    "symbol": symbol, "strategy": strat_name,
                                    "side": side, "signal_price": sig.get("price"),
                                    **shadow,
                                }) + "\n")
                    except Exception:
                        pass  # shadow logging is best-effort
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
    from tools.profit_protect import check_and_close, _resolve_tick_economics, _contract_to_symbol, _strip_exchange_suffix
    # tick_protect: register open positions for millisecond-latency exits via
    # the WebSocket on-tick callback (vs this 1-sec poll). Backup remains
    # the existing check_and_close call below.
    try:
        from tools import tick_protect
        from tools.tick_stream import get_stream as _get_stream
        from tools.alert import send_alert as _alert
        tick_protect.configure(client=get_client(), log_fn=_log, alert_fn=_alert)
        _log("tick_protect configured (ms-latency on-tick exits enabled)")
        # ── HEALTHCHECK: verify the callback → close path actually works ──
        # Synthetic position + mock client + tick → measure close latency.
        # If this fails, log critical alert but DO NOT abort startup —
        # the 1-sec poll path is still active as backup safety net.
        try:
            from tools.tick_protect_healthcheck import run_healthcheck
            hc = run_healthcheck(log_fn=lambda _m: None)
            if hc.get("passed"):
                _log(f"  tick_protect healthcheck PASSED ({hc['latency_ms']}ms)")
            else:
                _log(f"  tick_protect healthcheck FAILED: {hc.get('errors')}")
                try:
                    _alert(
                        f"CRITICAL: tick_protect healthcheck FAILED on startup: "
                        f"{hc.get('errors')}. Falling back to 1-sec poll only.",
                        level="crit",
                    )
                except Exception:
                    pass
            # Re-configure after healthcheck wiped state with reset_for_test()
            tick_protect.configure(client=get_client(), log_fn=_log, alert_fn=_alert)
        except Exception as e:
            _log(f"  tick_protect healthcheck skipped: {type(e).__name__}: {e}")
        _tick_protect_ready = True
    except Exception as e:
        _log(f"tick_protect init failed (poll-only fallback): "
              f"{type(e).__name__}: {e}")
        _tick_protect_ready = False
    while not stop_event.is_set():
        try:
            client = get_client()
            account_id = get_account_id()
            # check_and_close returns the list of positions it processed.
            # Empty list = flat = use the relaxed cadence.
            # Non-empty = in-position = tight cadence to minimize slippage
            # past the active tier floor.
            closed = check_and_close(client, account_id, log_fn=_log)
            try:
                positions = client.get_positions(account_id) or []
                has_open = any(int(p.get("size") or 0) != 0 for p in positions)
            except Exception:
                positions = []
                has_open = False
            # ── Sync tick_protect's position registry + on-tick callbacks ──
            if _tick_protect_ready:
                try:
                    stream = _get_stream()
                    open_cids: set[str] = set()
                    for pos in positions:
                        size_ = int(pos.get("size") or 0)
                        if size_ == 0:
                            continue
                        cid = str(pos.get("contractId") or "")
                        if not cid:
                            continue
                        open_cids.add(cid)
                        raw_sym = _contract_to_symbol(cid) or ""
                        sym = _strip_exchange_suffix(raw_sym)
                        if not sym:
                            continue
                        tsz, tval = _resolve_tick_economics(sym)
                        if tsz <= 0 or tval <= 0:
                            continue
                        type_code = int(pos.get("type") or 0)
                        side_ = "long" if type_code == 1 else "short" if type_code == 2 else (
                            "long" if size_ > 0 else "short")
                        avg_px = float(pos.get("averagePrice") or 0)
                        if avg_px <= 0:
                            continue
                        tick_protect.register_position(
                            contract_id=cid, symbol=sym, side=side_,
                            size=abs(size_), avg_price=avg_px,
                            tick_size=tsz, tick_value=tval,
                            account_id=account_id,
                        )
                        stream.register_on_tick(cid, tick_protect.on_tick)
                    # Unregister anything no longer open
                    for tracked in tick_protect.tracked_positions():
                        if tracked not in open_cids:
                            tick_protect.unregister_position(tracked)
                            stream.unregister_on_tick(tracked)
                except Exception as e:
                    _log(f"  tick_protect sync error: "
                          f"{type(e).__name__}: {e}")
        except Exception as e:
            _log(f"position-poll error: {type(e).__name__}: {e}")
            has_open = False
        next_interval = POSITION_POLL_SEC_IN_TRADE if has_open else interval_sec
        stop_event.wait(next_interval)


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

    # Initialize the SignalR tick stream so profit_protect can read
    # sub-second prices instead of polling 1-min bar closes. Failure
    # to init is non-fatal — profit_protect falls back to bar polling.
    if not args.dry_run and not args.paper:
        try:
            from tools.tick_stream import get_stream
            _client = get_client()
            _account_id = get_account_id()
            # get_client returns an unauthenticated cached instance —
            # auth must be called before reading _jwt
            if not getattr(_client, "_jwt", None):
                _client.authenticate()
            stream = get_stream(jwt=_client._jwt)
            stream.start()
            # Subscribe to contracts for symbols in the live filter so
            # the cache is warm by the time the first position opens.
            try:
                from tools.signal_queue import _live_strategies_filter as _filter
            except Exception:
                _filter = None
            warm_symbols: set[str] = set()
            try:
                import json as _json
                with open("state/strategy_validation.json", "r",
                            encoding="utf-8") as _f:
                    _data = _json.load(_f)
                for cell in _data.get("live_allowlist", []):
                    sym = cell.get("symbol")
                    if sym:
                        warm_symbols.add(sym)
            except Exception:
                pass
            for sym in warm_symbols:
                try:
                    cid = _client.front_month_contract_id(sym)
                    stream.subscribe(cid)
                except Exception:
                    pass
            _log(f"tick_stream started; subscribed to "
                 f"{len(stream.subscribed_contracts())} contracts")
        except Exception as e:
            _log(f"tick_stream init failed (non-fatal): "
                 f"{type(e).__name__}: {e}")

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
