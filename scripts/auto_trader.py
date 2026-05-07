"""Deterministic auto-trader — bypasses the Claude SDK for trigger evaluation.

WHY THIS EXISTS:
The orchestrator's wake_agent flow depends on the Claude Agent SDK
spawning the claude.exe CLI as a subprocess. On this machine, that
subprocess fork has been failing intermittently (FileNotFoundError on
the CLI binary, despite the file existing). Detection of trigger
conditions (Bollinger squeeze, ORB, RSI2, Donchian, vol spike, etc.)
is pure math on OHLCV bars — it doesn't need an LLM.

This script runs the full strategy library directly in Python, applies
the SAME risk hook checks the SDK chain would, and places real orders
through the existing topstep/ProjectX integration. It produces real
trades and real data, today.

LLM use is reserved for what LLMs are uniquely good at: regime reads,
post-mortems, the weekly review. None of that is needed for the
trigger phase.

USAGE:
    python -m scripts.auto_trader            # live, focus universe
    python -m scripts.auto_trader --once     # one scan and exit (debug)
    python -m scripts.auto_trader --dry-run  # find triggers, don't place

Environment:
    FUND_MODE=live      # if 'paper', no orders are placed
    PROJECTX_*          # required for live broker calls
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from dotenv import load_dotenv
load_dotenv()

# Ensure cwd resolves project paths regardless of where the script was launched
_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)

from state.db import get_db, utcnow_iso
from tools.projectx_client import ProjectXError, get_account_id, get_client
from tools.backtest import strategies as strats
from hooks.risk_gate import (
    _check_kill_switch, _check_focus_universe, _check_strategy_blacklist,
    _check_active_lessons, _check_post_stop_cooldown, _check_high_impact_blackout,
    _check_combine_defensive_ladder, _check_daily_target_lock,
    _check_daily_trade_count, _check_session_window,
    _check_no_naked_shorts, _check_stop_required, _check_per_symbol_limits,
    _check_sector_and_basket_limits, _load_yaml,
)


# ── Strategy roster (ordered by what we trust) ───────────────
# Each tuple: (callable, default kwargs, conviction floor, label)
# We try strategies in this order; first trigger wins per symbol per scan.
# =============================================================
# STRATEGY ROSTER — fund's strategic focus is PRICE-ACTION trading
# =============================================================
# Order matters: scanned top-to-bottom, first trigger wins per symbol/timeframe.
#
# TIER 1 — PRICE ACTION (primary, added 2026-05-04 per user directive):
#   Fair Value Gap (FVG) is the designated LEAD strategy. Order blocks
#   and liquidity sweeps are supporting price-action setups. All three
#   are pure-price microstructure plays that work 24/5 — they don't
#   need volume confirmation, regime filters, or macro context.
#   Conviction = "high" so they pass the autonomous min_conviction floor
#   even when other rosters are gated.
#
# TIER 2 — CLASSICAL TA (backstop, scanned only if Tier 1 doesn't trigger):
#   Bollinger / RSI / Donchian / breakout / mean-reversion family. These
#   were the original lineup pre-2026-05-04. Demoted but retained because
#   they still produce edges in specific regimes (RTH, range days).
#
# Do NOT reorder Tier 1 below Tier 2 without explicit user approval —
# the price-action focus is a strategic mandate, not just a default.
STRATEGY_ROSTER: list[tuple[Any, dict, str, str]] = [
    # ── TIER 1: PRICE ACTION ─────────────────────────────────
    # 2026-05-04 backtest verdict: at default params these strategies
    # produce ~33% hit rate at 2:1 R:R = -0.02R expectancy across 30d
    # of intraday data on 7 symbols (5,593 trades). That's coin-flip,
    # not edge. Conviction lowered to "low" so they do NOT fire under
    # autonomous min_conviction=med — they remain in the roster (still
    # scanned + logged for diagnostic visibility) but blocked from
    # placing orders until walk-forward parameter sweep + per-time/symbol
    # analysis identifies edge windows. Re-elevate to "high"/"med" only
    # after positive expectancy is demonstrated on a held-out test set.
    (strats.fair_value_gap,    {}, "low", "fair_value_gap"),
    (strats.order_block,       {}, "low", "order_block"),
    # 2026-05-05 Phase 2: bumped to "med" — validated on 6E London long + MES RTH long
    (strats.liquidity_sweep,   {}, "med", "liquidity_sweep"),
    # ── HEADLINE EDGE: gap_fill (validated 2026-05-04 walk-forward) ──
    # Walk-forward 60d split (45 train / 15 OOS) on ZN/NG/6E:
    #   ZN: train n=585 E=+0.87R t=+15.21 | OOS n=256 E=+1.10R t=+11.95
    #   6E: train n= 37 E=+1.50R t= +2.44 | OOS n= 17 E=+2.65R t= +3.63
    #   NG: train n= 72 E=+0.64R t= +2.86 | OOS n= 38 E=+0.83R t= +1.53
    # OOS hit rate (69.9%) > train hit rate (65.7%) — strong sign of real
    # edge, not curve-fit. Allowlist gating to ZN/NG/6E enforced via
    # STRATEGY_SYMBOL_ALLOWLIST below. high conviction so it passes the
    # autonomous min_conviction=med floor.
    (strats.gap_fill, {}, "high", "gap_fill"),
    # ── TIER 2: CLASSICAL TA (backstop) ──────────────────────
    (strats.rsi2_extreme_reversion, {}, "med", "rsi2_extreme_reversion"),
    (strats.bollinger_squeeze_break, {}, "med", "bollinger_squeeze_break"),
    (strats.narrow_range_break, {}, "med", "narrow_range_break"),
    (strats.donchian_breakout, {}, "low", "donchian_breakout"),
    (strats.vol_regime_trend, {}, "med", "vol_regime_trend"),
    (strats.keltner_breakout, {}, "low", "keltner_breakout"),
    (strats.bollinger_mean_reversion, {}, "low", "bollinger_mean_reversion"),
    (strats.range_mean_reversion, {}, "low", "range_mean_reversion"),
    # 2026-05-05 Phase 2: bumped from "low" to "med" — passed walk-forward
    # validation in specific cells (see STRATEGY_CELL_ALLOWLIST).
    (strats.inside_bar_break, {}, "med", "inside_bar_break"),
    (strats.vol_spike_fade, {}, "low", "vol_spike_fade"),
    (strats.pullback_in_trend, {}, "low", "pullback_in_trend"),
    (strats.volatility_breakout, {}, "low", "volatility_breakout"),
    (strats.support_resistance_bounce, {}, "low", "support_resistance_bounce"),
    # vwap_reversion REMOVED 2026-05-04 — backtest+walk-forward both
    # confirmed broken: ~2-10% hit rate, t-stat as low as -24 on MNQ RTH.
    # Was a stop-loss factory across all symbols/sessions.
    (strats.volume_spike_reversal, {}, "low", "volume_spike_reversal"),
    # 2026-05-05 Phase 2: bumped to "med" — validated on 6E London long + RTH short
    (strats.pivot_reversal, {}, "med", "pivot_reversal"),
    # ORB excluded — strategy_blacklist already vetoes ZN+ORB and NG+ORB
    # but we keep it last so it can fire on MES/GC/6E if no other does
    (strats.opening_range_breakout, {}, "low", "opening_range_breakout"),
    # 2026-05-06 Tier 4 parametrized variant: order_block tuned with
    # displacement_atr=1.0 (default 1.5 produced 0 validated cells).
    # Tuned version found 4 validated cells: 6B London long, 6E RTH short,
    # MNQ Asian short, 6B Asian short. "med" conviction so autonomous mode
    # accepts it. See vault/research/backtests/2026-05-06_*tier4_order_block_sweep.md.
    (strats.order_block_d1, {}, "med", "order_block_d1"),
    # 2026-05-06 Tier 4 multi-sweep — fair_value_gap tuned (rr=2.5).
    # Found 15 validated cells, top: 6E Asian short t=+3.41 E=+0.99R.
    (strats.fair_value_gap_tuned, {}, "med", "fair_value_gap_tuned"),
    # 2026-05-06 Tier 4 multi-sweep — liquidity_sweep tuned (rr=2.5).
    # Found 6 validated cells, top 3 all use rr=2.5 swing=10.
    (strats.liquidity_sweep_tuned, {}, "med", "liquidity_sweep_tuned"),
    # 2026-05-06 Quant Researcher proposal #3 — yield-curve cointegration.
    # Single-leg ZN trade vs ZT spread divergence. Untested in walk-forward
    # at the time of registration; daily validation will gate live trading.
    (strats.cross_asset_divergence_zn, {}, "med", "cross_asset_divergence_zn"),
]


# Per-strategy symbol allowlist. A strategy listed here ONLY fires on the
# named symbols. Strategies NOT in this dict have no symbol restriction.
#
# 2026-05-04: gap_fill walked-forward edge confirmed only on ZN/NG/6E.
# MES/MNQ/MCL/GC failed validation. Restrict to the validated set.
#
# 2026-05-04: narrow_range_break aggregate has NEGATIVE expectancy
# (-0.09R, t=-3.93 across 60d × 7 symbols). The only validated cell is
# GC Asian SHORT (n=160, +0.35R, t=+2.85; OOS confirmed). Gating to GC
# only as a first cut — the full session+direction filter is in
# STRATEGY_CELL_ALLOWLIST below.
#
# DEFAULT-DENY (2026-05-05 user directive): a strategy not listed below
# is BLOCKED from live trading. Unvalidated strategies still scan + log
# as shadow trades (see scripts/shadow_logger.py) so they continue to
# accumulate data toward future validation, but they don't place orders.
STRATEGY_SYMBOL_ALLOWLIST: dict[str, set[str]] = {
    # ── Validated headline edge (CLAUDE.md walk-forward 2026-05-04) ──
    # 2026-05-05 Tier 3 added 7 cousin symbols (Treasury curve + 4 FX);
    # all hold OOS at 5m. Live trading on these requires expanding
    # config/focus_universe.yaml — currently they will pass this allowlist
    # but get blocked by the focus-universe gate. ZB/ZF/ZT/6B/6J/6A/6C are
    # validated; user decides whether to add them to focus.
    "gap_fill": {"ZN", "NG", "6E",
                 # Treasury curve cousins (5m) — Tier 3 walk-forward 2026-05-05
                 "ZB", "ZF", "ZT",  # OOS E=+0.98/+1.16/+1.41R, t=+10.5/+7.95/+11.76
                 # FX cousins (5m) — Tier 3 walk-forward 2026-05-05
                 "6B", "6J", "6A", "6C"},  # OOS E=+0.70/+2.34/+2.19/+0.49R
    # ── Phase 2 walk-forward 2026-05-05 (24 validated cells across 837 tested) ──
    "narrow_range_break":      {"GC", "MCL", "NG"},
    "pivot_reversal":          {"6E"},
    "liquidity_sweep":         {"6E", "MES", "MNQ"},
    "inside_bar_break":        {"NG", "GC", "MES"},
    "keltner_breakout":        {"GC", "ZN", "MES", "MCL"},
    "bollinger_squeeze_break": {"6E", "MCL", "MNQ"},
    "vol_regime_trend":        {"NG"},
    "opening_range_breakout":  {"MES"},
    "vol_spike_fade":          {"MNQ"},
    "fair_value_gap":          {"GC", "NG", "MNQ", "6E"},
}


# Per-strategy CELL allowlist (symbol × session × side). A strategy listed
# here only fires when the candidate signal matches one of the validated
# cells. Strategies NOT in this dict are unconstrained on session/side.
#
# Sessions (ET): Asian=20:00-04:00, London=04:00-09:30, RTH=09:30-16:00,
# PostClose=16:00-20:00.
#
# 2026-05-05 Phase 2 walk-forward additions: 7 new validated cells with
# OOS n>=20 and OOS t>=2.0. See vault/research/backtests/2026-05-05_0148_phase2.md.
STRATEGY_CELL_ALLOWLIST: dict[str, list[dict]] = {
    # gap_fill is validated at the symbol level (no session/side restriction)
    # by the 60-day walk-forward. The Phase 2 sweep also identified
    # NG Asian short as a particularly strong sub-cell.
    "narrow_range_break": [
        {"symbol": "GC",  "session": "Asian",  "side": "short"},  # OOS E=+0.57R t=+2.28 n=33
        {"symbol": "MCL", "session": "Asian",  "side": "long"},   # OOS E=+0.69R t=+2.55 n=33
        {"symbol": "NG",  "session": "London", "side": "long"},   # OOS E=+0.37R t=+1.52 n=37
    ],
    "pivot_reversal": [
        {"symbol": "6E", "session": "London", "side": "long"},   # OOS E=+0.70R t=+2.19 n=23
        {"symbol": "6E", "session": "RTH",    "side": "short"},  # OOS E=+0.71R t=+2.15 n=21
    ],
    "liquidity_sweep": [
        {"symbol": "6E",  "session": "London", "side": "long"},  # OOS E=+0.59R t=+2.21 n=32
        {"symbol": "MES", "session": "RTH",    "side": "long"},  # OOS E=+0.57R t=+2.06 n=30
        {"symbol": "MNQ", "session": "RTH",    "side": "long"},  # OOS E=+0.48R t=+1.81 n=32
        # Tier 2 walk-forward 2026-05-05 added:
        {"symbol": "MNQ", "session": "London", "side": "long"},  # OOS E=+0.64R t=+1.95 n=22
        {"symbol": "6E",  "session": "Asian",  "side": "short"}, # OOS E=+0.59R t=+1.57 n=17
    ],
    "inside_bar_break": [
        {"symbol": "NG",  "session": "London",    "side": "short"},  # OOS E=+0.42R t=+2.15 n=46
        {"symbol": "GC",  "session": "PostClose", "side": "long"},   # OOS E=+0.87R t=+2.37 n=14
        {"symbol": "GC",  "session": "Asian",     "side": "short"},  # OOS E=+0.36R t=+1.76 n=48
        {"symbol": "MES", "session": "PostClose", "side": "long"},   # OOS E=+0.71R t=+1.74 n=8
    ],
    "keltner_breakout": [
        {"symbol": "GC",  "session": "Asian",  "side": "short"},  # OOS E=+1.17R t=+3.58 n=18
        {"symbol": "ZN",  "session": "London", "side": "long"},   # OOS E=+0.88R t=+1.59 n=8
        {"symbol": "MES", "session": "London", "side": "long"},   # OOS E=+0.75R t=+1.68 n=12
        {"symbol": "MCL", "session": "Asian",  "side": "long"},   # OOS E=+0.65R t=+1.90 n=20
    ],
    "bollinger_squeeze_break": [
        {"symbol": "6E",  "session": "Asian", "side": "short"},  # OOS E=+1.14R t=+2.07 n=7
        {"symbol": "MCL", "session": "Asian", "side": "long"},   # OOS E=+0.80R t=+2.04 n=15
        {"symbol": "MNQ", "session": "Asian", "side": "short"},  # OOS E=+0.71R t=+1.73 n=14
    ],
    "vol_regime_trend": [
        {"symbol": "NG", "session": "Asian", "side": "long"},  # OOS E=+1.10R t=+2.40 n=10
    ],
    "opening_range_breakout": [
        {"symbol": "MES", "session": "London", "side": "long"},  # OOS E=+1.00R t=+1.94 n=16
    ],
    "vol_spike_fade": [
        {"symbol": "MNQ", "session": "RTH", "side": "long"},  # OOS E=+0.59R t=+1.55 n=11
    ],
    "fair_value_gap": [
        {"symbol": "GC",  "session": "Asian", "side": "short"},  # OOS E=+0.50R t=+1.91 n=34
        # Tier 2 walk-forward 2026-05-05 added:
        {"symbol": "NG",  "session": "RTH",   "side": "short"},  # OOS E=+0.55R t=+1.80 n=24
        {"symbol": "MNQ", "session": "Asian", "side": "long"},   # OOS E=+0.55R t=+2.00 n=31
        {"symbol": "6E",  "session": "Asian", "side": "short"},  # OOS E=+0.50R t=+2.13 n=42
        {"symbol": "GC",  "session": "RTH",   "side": "short"},  # OOS E=+0.45R t=+1.71 n=33
    ],
}


def _session_bucket_et(et_hour_float: float) -> str:
    """Map an ET hour-of-day (e.g., 14.25 = 14:15 ET) to session name."""
    if 9.5 <= et_hour_float < 16:
        return "RTH"
    if 4 <= et_hour_float < 9.5:
        return "London"
    if 16 <= et_hour_float < 20:
        return "PostClose"
    return "Asian"


def _load_daily_validation_state() -> dict | None:
    """Read state/strategy_validation.json (produced daily by
    scripts/daily_strategy_validation.py). Returns parsed dict or None.

    The file is the source of truth for which cells are 'live' vs 'shadow'.
    The hardcoded STRATEGY_SYMBOL_ALLOWLIST / STRATEGY_CELL_ALLOWLIST in
    this file are the static fallback for first-run before the daily
    validator has run. Once the validator has produced state, that
    becomes the runtime authority — this lets the system promote
    strategies that earn edge and demote strategies that lose it
    without code changes.
    """
    path = Path("state/strategy_validation.json")
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


_validation_state_cache: dict | None = None
_validation_state_mtime: float = 0


def _get_dynamic_allowlists() -> tuple[dict[str, set[str]], dict[str, list[dict]]] | None:
    """Build (symbol_allowlist, cell_allowlist) from the daily validation
    state file. Returns None if no state available (use static fallback).

    Caches by file mtime so repeated calls within a scan are cheap.
    """
    global _validation_state_cache, _validation_state_mtime
    path = Path("state/strategy_validation.json")
    if not path.exists():
        return None
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    if _validation_state_cache is None or mtime != _validation_state_mtime:
        st = _load_daily_validation_state()
        if st is None:
            return None
        _validation_state_cache = st
        _validation_state_mtime = mtime

    cells = (_validation_state_cache or {}).get("live_allowlist") or []
    if not cells:
        return None

    sym_allow: dict[str, set[str]] = {}
    cell_allow: dict[str, list[dict]] = {}
    for c in cells:
        strat = c.get("strategy"); sym = c.get("symbol")
        sess = c.get("session"); side = c.get("side")
        if not (strat and sym and sess and side):
            continue
        sym_allow.setdefault(strat, set()).add(sym)
        cell_allow.setdefault(strat, []).append(
            {"symbol": sym, "session": sess, "side": side}
        )
    return sym_allow, cell_allow


def _record_shadow_for_unvalidated(db, label: str, symbol: str,
                                    signal: dict, conviction: str,
                                    reason: str) -> None:
    """When an unvalidated (strategy, symbol) or unvalidated cell triggers,
    log a shadow trade so we can resolve it later and accumulate evidence
    toward future validation. No order placed.

    Dedupe: skip if an unresolved shadow trade for the same
    (strategy, symbol, side) was logged within the last 30 minutes —
    avoids flooding the table on persistent triggers.
    """
    try:
        side = "long" if str(signal.get("side", "")).lower() in ("long", "buy") else "short"
        entry = float(signal.get("price") or 0)
        stop = float(signal.get("stop") or 0)
        target = float(signal.get("target") or 0) if signal.get("target") else entry
        if entry <= 0 or stop <= 0:
            return

        # Dedupe within 30 minutes
        cutoff = (datetime.now(tz=timezone.utc)
                  - timedelta(minutes=30)).isoformat(timespec="seconds")
        row = db.connect().execute(
            "SELECT 1 FROM shadow_trades "
            "WHERE strategy=? AND symbol=? AND side=? "
            "AND outcome IS NULL AND ts_signal >= ? LIMIT 1",
            (label, symbol, side, cutoff),
        ).fetchone()
        if row:
            return

        rr = (abs(target - entry) / max(abs(entry - stop), 0.0001)) if target else 0.0
        db.record_shadow_trade(
            agent="auto_trader", symbol=symbol, strategy=label, side=side,
            entry_price=entry, stop_price=stop, target_price=target,
            rr_planned=rr, conviction=conviction, horizon="intraday",
            shadow_reason=reason,
            notes=f"signal_reason={signal.get('reason','')[:80]}",
        )
    except Exception:
        # Never let shadow logging break a scan
        pass


def _signal_passes_cell_allowlist(label: str, symbol: str, signal: dict) -> bool:
    """True if the strategy has no cell restriction OR the signal matches
    one of the allowed cells. Called inside scan_once after a signal is
    generated, before any order placement."""
    cells = STRATEGY_CELL_ALLOWLIST.get(label)
    if cells is None:
        return True  # no restriction
    from datetime import datetime
    from zoneinfo import ZoneInfo
    now_et = datetime.now(tz=ZoneInfo("America/New_York"))
    session_now = _session_bucket_et(now_et.hour + now_et.minute / 60.0)
    side = str(signal.get("side", "")).lower()
    for c in cells:
        if (c["symbol"] == symbol
                and c["session"] == session_now
                and c["side"] == side):
            return True
    return False


CONVICTION_RR_FLOOR = {"high": 1.5, "med": 2.0, "low": 2.5, "validation": 1.5}


# ── Bar fetching ─────────────────────────────────────────────

def fetch_bars(client, symbol: str, *, minutes: int = 5, lookback: int = 200) -> pd.DataFrame | None:
    """Fetch the last `lookback` bars at `minutes`-minute resolution.

    Returns a pd.DataFrame with the same columns the strategies expect:
    Open, High, Low, Close, Volume, indexed by timestamp.
    """
    try:
        contracts = client.search_contracts(symbol, live=False)
        if not contracts:
            return None
        front = sorted(contracts,
                       key=lambda c: c.get("expiryDate") or c.get("lastTradeDate") or "")[0]
        cid = front.get("id") or front.get("contractId")
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(minutes=minutes * lookback * 2)
        bars = client.get_bars(
            contract_id=cid,
            start_time=start.isoformat(),
            end_time=end.isoformat(),
            unit=2, unit_number=minutes, limit=lookback,
            live=False,
        )
        if not bars:
            return None
        df = pd.DataFrame(bars)
        # ProjectX field names: t, o, h, l, c, v
        rename = {"t": "Date", "o": "Open", "h": "High",
                  "l": "Low", "c": "Close", "v": "Volume"}
        df = df.rename(columns=rename)
        if "Date" not in df.columns:
            return None
        df["Date"] = pd.to_datetime(df["Date"])
        df = df.set_index("Date").sort_index()
        for col in ("Open", "High", "Low", "Close", "Volume"):
            if col not in df.columns:
                return None
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df.dropna()
    except Exception as e:
        print(f"  [fetch_bars] {symbol}: {type(e).__name__}: {e}")
        return None


def find_latest_signal(bars: pd.DataFrame, strategy_fn, **kwargs) -> dict | None:
    """Run a strategy on the bars; return the LAST entry signal if any
    fired in the most recent 3 bars (i.e., still actionable)."""
    if len(bars) < 30:
        return None
    last_idx = bars.index[-1]
    cutoff = bars.index[-3] if len(bars) >= 3 else bars.index[0]
    latest = None
    try:
        for sig in strategy_fn(bars, **kwargs):
            if sig.kind != "entry":
                continue
            if sig.date >= cutoff:
                latest = sig
    except Exception as e:
        return None
    if latest is None:
        return None
    return {
        "date": latest.date, "side": latest.side, "price": float(latest.price),
        "stop": float(latest.stop) if latest.stop is not None else None,
        "target": float(latest.target) if latest.target is not None else None,
        "reason": latest.reason,
    }


# ── Risk gate (manual application) ───────────────────────────

ACTIVE_RISK_CHECKS = [
    ("kill_switch", _check_kill_switch),
    ("focus_universe", _check_focus_universe),
    ("strategy_blacklist", _check_strategy_blacklist),
    ("active_lessons", _check_active_lessons),
    ("post_stop_cooldown", _check_post_stop_cooldown),
    ("high_impact_blackout", _check_high_impact_blackout),
    ("combine_defensive_ladder", _check_combine_defensive_ladder),
    ("daily_target_lock", _check_daily_target_lock),
    ("daily_trade_count", _check_daily_trade_count),
    ("session_window", _check_session_window),
    ("no_naked_shorts", _check_no_naked_shorts),
    ("stop_required", _check_stop_required),
    ("per_symbol_limits", _check_per_symbol_limits),
    ("sector_basket_limits", _check_sector_and_basket_limits),
]


def apply_risk_gate(order: dict) -> dict | None:
    """Run the same checks the SDK PreToolUse hook would. Returns a verdict
    dict on block, None on pass."""
    db = get_db()
    limits = _load_yaml("risk_limits.yaml")
    topstep = _load_yaml("topstep.yaml")
    symbols = _load_yaml("symbols.yaml").get("symbols", {})
    snap = db.latest_account_snapshot() or {"realized_pl_day_usd": 0.0}
    positions = db.current_positions()

    for label, fn in ACTIVE_RISK_CHECKS:
        try:
            v = fn(tool_name="topstep_place_order", order=order,
                   agent="auto_trader", limits=limits, topstep=topstep,
                   symbols=symbols, snap=snap, positions=positions)
        except Exception as e:
            return {"rule": f"{label}_exception",
                    "reason": f"{type(e).__name__}: {e}"}
        if v is not None:
            return v
    return None


# ── Order placement ──────────────────────────────────────────

def _tick_size_for(symbol: str) -> float:
    """Get tick size for a symbol from config/symbols.yaml. Used to build the
    limit price for marketable-limit entries (Topstep rejects pure market orders)."""
    syms = _load_yaml("symbols.yaml").get("symbols", {})
    s = syms.get(symbol, {}) or {}
    return float(s.get("tick_size", 0.01))


# Quality thresholds — prevent the noise-trading that caused 35 circular
# round-trips today. Tightened 2026-04-29 per user directive.
MIN_STOP_TICKS = 5      # default — stops closer than 5 ticks get eaten by noise
MIN_REWARD_USD = 30.0   # default — don't trade for less than $30 even if RR looks good

# Sector-aware MIN_REWARD_USD: full-size contracts have larger fees (~$5
# round-trip vs ~$1.50 for micros) so they need bigger rewards to be
# economically interesting. Index full-size also has bigger ticks; even
# small moves are real money. 2026-04-30 enrichment.
MIN_REWARD_USD_BY_SYMBOL = {
    # Full-size index — $5 fees, $5-$12.50 per tick
    "ES": 50.0, "NQ": 50.0, "RTY": 50.0, "YM": 50.0, "NKD": 50.0,
    # Full-size energies/metals — $5 fees, can move fast
    "CL": 50.0, "NG": 50.0, "RB": 50.0, "HO": 50.0,
    "GC": 50.0, "SI": 50.0, "HG": 50.0, "PL": 50.0,
    # Full-size grains/livestock — $5 fees
    "ZC": 40.0, "ZS": 40.0, "ZW": 40.0, "ZL": 40.0, "ZM": 40.0,
    "LE": 40.0, "HE": 40.0,
    # Full-size FX — $5 fees, larger ticks
    "6E": 40.0, "6B": 40.0, "6J": 40.0, "6A": 40.0, "6C": 40.0, "6S": 40.0,
    # Rates — smaller fees ($3) but tight ticks; default is fine
    # Micros stay at default $30 (fees ~$1.50, smaller ticks)
}


def _min_reward_usd_for(symbol: str) -> float:
    return MIN_REWARD_USD_BY_SYMBOL.get(symbol, MIN_REWARD_USD)

# Sector-aware MIN_STOP_TICKS: index futures have larger tick values × tighter
# normal noise → need more ticks for the stop to survive intraday chop.
# Energies/metals tolerate the default 5. Rates need slightly more due to
# their finer tick increments. 2026-04-30: derived from incident review
# (5-tick MES stop = $6.25 loss, eaten by 1-2 sec of noise).
MIN_STOP_TICKS_BY_SECTOR = {
    "index_macro": 8,
    "rates":       10,
    "ag":          5,
    "fx_futures":  5,
    "energies":    5,
    "metals":      5,
    "crypto":      6,
}


# Per-strategy stop-floor override: gap_fill places STRUCTURAL stops just
# beyond the gap edge, not noise-buffer stops. The sector minimums above
# (designed for momentum/break strategies) are too aggressive for
# gap_fill — they reject valid structural-stop trades whose gap is small.
# 2026-05-06: today's first scan rejected ZT gap_fill with 0.18-tick
# stop using rates min=10. Below override allows gap_fill to use a
# minimum of 3 ticks across all sectors — still safer than 1-tick noise
# but doesn't reject the small-but-real gap signals that walk-forward
# validated.
PER_STRATEGY_MIN_STOP_TICKS_OVERRIDE = {
    "gap_fill": 3,
}


def _min_stop_ticks_for(symbol: str, strategy: str | None = None) -> int:
    """Sector-aware stop-distance floor (in ticks). If `strategy` is in
    the per-strategy override map, use that instead of the sector floor.
    """
    if strategy and strategy in PER_STRATEGY_MIN_STOP_TICKS_OVERRIDE:
        return PER_STRATEGY_MIN_STOP_TICKS_OVERRIDE[strategy]
    syms = _load_yaml("symbols.yaml").get("symbols", {})
    sector = (syms.get(symbol) or {}).get("sector")
    return MIN_STOP_TICKS_BY_SECTOR.get(sector, MIN_STOP_TICKS)


def _round_trip_fee_usd(symbol: str) -> float:
    """Fee per round-trip per contract for `symbol` from risk_limits.yaml.

    Critical for trade economics: if expected reward < 3x fees, the trade
    is unprofitable in expectation regardless of strategy hit rate.
    """
    limits = _load_yaml("risk_limits.yaml")
    fees = limits.get("fees_round_trip_usd") or {}
    return float(fees.get(symbol, fees.get("default", 5.00)))


def _expected_reward_usd(signal: dict, tick_value: float, tick_size: float) -> float:
    """Expected gross profit at target hit, in USD per contract."""
    entry = float(signal.get("price") or 0)
    target = float(signal.get("target") or 0)
    if target == 0 or entry == 0 or tick_size == 0:
        return 0.0
    move_ticks = abs(target - entry) / tick_size
    return move_ticks * tick_value


def _fee_decision_pass(symbol: str, signal: dict, tick_size: float) -> tuple[bool, str]:
    """Returns (pass, reason). Skip trade if reward at target is too small
    to justify the round-trip fee."""
    limits = _load_yaml("risk_limits.yaml")
    fee_rules = limits.get("fee_decision") or {}
    min_ratio = float(fee_rules.get("min_reward_to_fee_ratio", 3.0))
    if min_ratio <= 0:
        return True, ""
    syms = limits.get("per_symbol", {})
    # Get tick_value from symbols.yaml
    s = _load_yaml("symbols.yaml").get("symbols", {}).get(symbol, {})
    tick_value = float(s.get("tick_value", 1.0))
    fee = _round_trip_fee_usd(symbol)
    reward = _expected_reward_usd(signal, tick_value, tick_size)
    if reward == 0:
        return False, "no target → cannot evaluate fee economics"
    ratio = reward / fee
    if ratio < min_ratio:
        return False, (f"reward ${reward:.2f} / fee ${fee:.2f} = {ratio:.1f}x "
                       f"< required {min_ratio}x")
    return True, f"reward {ratio:.1f}x fee — economical"


def _round_to_tick(price: float, tick: float) -> float:
    """Round a price to the nearest valid tick boundary.

    CRITICAL FIX 2026-04-29: Topstep REJECTS any order whose limit/stop
    price is not exactly on a tick boundary. Strategies generate prices
    via statistical math (e.g. target = 1.173843140941422) which are
    almost never aligned. Without this rounding, ~55% of entry orders
    were rejected by Topstep, costing fees on every rejection. Round
    DOWN for buy limits / sell stops (more conservative entry / wider
    stop) to maintain favorable fill behavior; not strictly required
    but safer than nearest.
    """
    if tick <= 0:
        return price
    n = round(price / tick)
    return round(n * tick, 10)


def place_bracket(client, symbol: str, signal: dict, qty: int = 1) -> dict:
    """Place entry + stop via ProjectX directly (bypasses the SDK @tool wrapper).

    IMPORTANT: Topstep REJECTS pure market orders (status=5, instant rejection).
    Confirmed empirically 2026-04-29: NG/6E market orders rejected in 3ms with
    fill_volume=0. Solution: use marketable-limit orders (limit price set
    deliberately worse than the current quote so it fills like a market order
    but goes through Topstep's limit-order pipeline). Buy limit > expected
    fill, sell limit < expected fill, both with a 5-tick slippage buffer.
    """
    import sqlite3
    side = "buy" if signal["side"] == "long" else "sell"
    cid = f"auto_{uuid.uuid4().hex[:12]}"
    db = get_db()
    account_id = get_account_id()

    tick = _tick_size_for(symbol)
    slippage_ticks = 5
    entry_price = float(signal["price"])
    if side == "buy":
        limit_price = entry_price + slippage_ticks * tick
    else:
        limit_price = entry_price - slippage_ticks * tick

    # Pre-flight INSERT — UNIQUE(client_order_id) is our idempotency guard
    try:
        with db.tx() as c:
            c.execute(
                """INSERT INTO orders
                    (client_order_id, agent, ts_proposed, symbol, contract_month,
                     side, order_type, qty, limit_price, stop_price,
                     status, risk_verdict)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (cid, "auto_trader", utcnow_iso(), symbol, None,
                 side, "limit", int(qty), limit_price, signal["stop"],
                 "proposed", "allow"),
            )
    except sqlite3.IntegrityError:
        return {"status": "duplicate", "client_order_id": cid,
                "error": "client_order_id collision"}

    # 1. Resolve front-month contract id
    try:
        contract_id = client.front_month_contract_id(symbol)
    except ProjectXError as e:
        with db.tx() as c:
            c.execute("UPDATE orders SET status=?, risk_reason=? WHERE client_order_id=?",
                      ("rejected", f"contract_lookup_failed: {e}"[:500], cid))
        return {"status": "failed", "error": f"contract lookup: {e}",
                "client_order_id": cid}

    # Round all prices to valid tick boundaries (Topstep rejects fractional)
    limit_price = _round_to_tick(limit_price, tick)

    # 2. Submit MARKETABLE-LIMIT entry (Topstep rejects pure market)
    try:
        result = client.place_order(
            account_id=account_id,
            contract_id=contract_id,
            side=side,
            qty=int(qty),
            order_type="limit",
            limit_price=limit_price,
            stop_price=None,
            time_in_force="day",
            client_order_id=cid,
        )
    except ProjectXError as e:
        with db.tx() as c:
            c.execute("UPDATE orders SET status=?, risk_reason=? WHERE client_order_id=?",
                      ("rejected", f"broker_error: {e}"[:500], cid))
        return {"status": "failed", "error": str(e), "client_order_id": cid}

    # Detect broker-side rejection (success=False even when no exception raised).
    # Margin shortfall, tick-mis-rounding, etc. surface as success=False.
    # We log it but do NOT cooldown the symbol (per user directive 2026-04-29:
    # rely on lower scan frequency + thesis cooldown instead of per-symbol bans).
    if isinstance(result, dict) and result.get("success") is False:
        err = (result.get("errorMessage") or
               f"errorCode {result.get('errorCode', '?')}")
        with db.tx() as c:
            c.execute("UPDATE orders SET status=?, risk_reason=? WHERE client_order_id=?",
                      ("rejected", f"broker_rejected: {err}"[:500], cid))
        db.record_risk_event(
            severity="warn", rule="broker_rejected_entry",
            agent="auto_trader",
            detail={"symbol": symbol, "reason": str(err)[:200]},
        )
        return {"status": "rejected", "error": err, "client_order_id": cid}

    # 3. Mark submitted in DB with broker order id
    broker_oid = None
    if isinstance(result, dict):
        broker_oid = (result.get("orderId") or result.get("id")
                      or result.get("brokerOrderId"))
    with db.tx() as c:
        c.execute(
            """UPDATE orders SET ts_submitted=?, status=?, broker_order_id=?
                WHERE client_order_id=?""",
            (utcnow_iso(), "submitted",
             str(broker_oid) if broker_oid else None, cid),
        )

    # 4. Place the protective stop as a stop-LIMIT order (type=4).
    # IMPORTANT: Topstep rejects stop-limits when the limit is too far from
    # the stop. Empirically verified 2026-04-29: 5-tick gap → rejected;
    # 1-tick gap → accepted. The limit must be EXACTLY 1 tick past the
    # stop in the protective direction so the stop fires almost-marketable
    # while still satisfying Topstep's tight-limit rule.
    stop_cid = cid + "_stop"
    opposite = "sell" if side == "buy" else "buy"
    stop_trigger = _round_to_tick(float(signal["stop"]), tick)
    stop_limit_offset_ticks = 1   # confirmed working on Topstep
    if opposite == "sell":
        stop_limit_px = stop_trigger - stop_limit_offset_ticks * tick
    else:
        stop_limit_px = stop_trigger + stop_limit_offset_ticks * tick
    stop_limit_px = _round_to_tick(stop_limit_px, tick)
    try:
        stop_result = client.place_order(
            account_id=account_id,
            contract_id=contract_id,
            side=opposite,
            qty=int(qty),
            order_type="stop_limit",
            limit_price=stop_limit_px,
            stop_price=stop_trigger,
            time_in_force="gtc",
            client_order_id=stop_cid,
        )
        stop_broker_oid = None
        if isinstance(stop_result, dict):
            stop_broker_oid = (stop_result.get("orderId") or stop_result.get("id")
                               or stop_result.get("brokerOrderId"))
        # Record the stop in orders table too (separate row)
        try:
            with db.tx() as c:
                c.execute(
                    """INSERT INTO orders
                        (client_order_id, agent, ts_proposed, ts_submitted, symbol,
                         side, order_type, qty, stop_price, status, risk_verdict,
                         broker_order_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (stop_cid, "auto_trader", utcnow_iso(), utcnow_iso(), symbol,
                     opposite, "stop", int(qty), float(signal["stop"]),
                     "submitted", "allow",
                     str(stop_broker_oid) if stop_broker_oid else None),
                )
        except sqlite3.IntegrityError:
            pass  # stop already recorded
    except ProjectXError as e:
        # Entry filled but stop placement failed — this is bad; log breach
        db.record_risk_event(
            severity="breach", rule="bracket_stop_failed",
            agent="auto_trader",
            detail={"symbol": symbol, "client_order_id": cid,
                    "error": str(e)[:300],
                    "context": "Entry order placed but protective stop could "
                               "not be created. verify_position_stops sweep "
                               "should recover within 1 tick."},
        )

    # 5. Place the TARGET (take-profit) limit order on the OPPOSITE side.
    # MISSING-TARGET-BUG fix 2026-04-29: previously the auto-trader placed
    # entry + stop but never a target, so winning trades had no automatic
    # profit-take. Result: positions ran to either the stop or were held
    # indefinitely. Now: a passive limit order at the strategy's target
    # is placed immediately. Orphan-cancel sweep on next scan handles the
    # case where the stop fills first (target becomes orphaned).
    target_cid = cid + "_target"
    target_price = signal.get("target")
    target_broker_oid = None
    if target_price is not None and target_price > 0:
        target_price = _round_to_tick(float(target_price), tick)
        try:
            target_result = client.place_order(
                account_id=account_id,
                contract_id=contract_id,
                side=opposite,
                qty=int(qty),
                order_type="limit",
                limit_price=float(target_price),
                stop_price=None,
                time_in_force="gtc",
                client_order_id=target_cid,
            )
            if isinstance(target_result, dict):
                target_broker_oid = (target_result.get("orderId")
                                     or target_result.get("id")
                                     or target_result.get("brokerOrderId"))
            try:
                with db.tx() as c:
                    c.execute(
                        """INSERT INTO orders
                            (client_order_id, agent, ts_proposed, ts_submitted, symbol,
                             side, order_type, qty, limit_price, status, risk_verdict,
                             broker_order_id)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                        (target_cid, "auto_trader", utcnow_iso(), utcnow_iso(),
                         symbol, opposite, "limit", int(qty), float(target_price),
                         "submitted", "allow",
                         str(target_broker_oid) if target_broker_oid else None),
                    )
            except sqlite3.IntegrityError:
                pass
        except ProjectXError as e:
            db.record_risk_event(
                severity="warn", rule="bracket_target_failed",
                agent="auto_trader",
                detail={"symbol": symbol, "client_order_id": cid,
                        "error": str(e)[:300]},
            )

    return {
        "status": "submitted",
        "client_order_id": cid,
        "broker_order_id": broker_oid,
        "stop_client_order_id": stop_cid,
        "target_client_order_id": target_cid if target_price else None,
    }


# ── Main scan loop ───────────────────────────────────────────

def load_focus_universe() -> list[str]:
    cfg = _load_yaml("focus_universe.yaml") or {}
    if not cfg.get("focus_period_active"):
        # Default to a sane focus list anyway
        return ["MES", "NG", "GC", "ZN", "6E"]
    out: list[str] = []
    for syms in (cfg.get("allowed_symbols") or {}).values():
        out.extend(syms or [])
    return out or ["MES", "NG", "GC", "ZN", "6E"]


def _broker_position_for(client, account_id, symbol: str) -> dict | None:
    """Return broker position for a symbol if any, normalized."""
    try:
        positions = client.get_positions(account_id)
    except Exception:
        return None
    from hooks.risk_gate import _normalize_root
    for p in positions:
        contract = p.get("contractId", "")
        for tok in str(contract).split("."):
            if tok in ("CON", "F", "US", ""):
                continue
            if _normalize_root(tok) == symbol.upper():
                size = int(p.get("size") or 0)
                if size == 0:
                    continue
                t = int(p.get("type") or 0)
                side = "long" if t == 1 else "short" if t == 2 else (
                    "long" if size > 0 else "short")
                return {"symbol": symbol, "side": side, "size": abs(size),
                        "avg_price": float(p.get("averagePrice") or p.get("avgPrice") or 0)}
    return None


def _count_open_positions(client, account_id) -> int:
    """How many distinct contracts have an open position right now."""
    try:
        positions = client.get_positions(account_id)
    except Exception:
        return 0
    return sum(1 for p in positions if int(p.get("size") or 0) != 0)


# Position-level gain-tier auto-close thresholds (added 2026-05-04).
# When an open position's unrealized P&L exceeds these thresholds, the
# auto_trader market-closes it. Prevents both:
#   (a) "left $1190 on the table" runaway gains where target order didn't fire
#   (b) gain-then-reverse — a position at +$400 reversing to negative
# Defaults: $400 hard cap (matches daily_hard_target_usd), $150 high-water
# threshold with $50 floor (locks in $50 if peak > $150).
GAIN_TIER_HARD_CAP_USD = 400.0
GAIN_TIER_HIGH_WATER_USD = 150.0
GAIN_TIER_FLOOR_USD = 50.0

# TRAILING PROFIT LOCK (added 2026-05-06 per user directive: "don't let
# a gain turn into a loss by not taking profit correctly").
#
# Ratchet-style lock — as peak unrealized P&L grows, the floor under
# unrealized rises. The single most important rule: once a position
# has shown a meaningful gain (peak >= $30, which covers fees + a real
# profit), the position cannot close negative. Sell-the-rebound is OK,
# but giving back the entire profit is never OK.
#
# Tiers (peak_unrealized → minimum acceptable current_unrealized):
#   peak >=  $30  → floor = $0   (break-even or better — protects fees)
#   peak >=  $80  → floor = $20  (lock in $20 minimum)
#   peak >= $150  → floor = $50  (matches existing high_water rule)
#   peak >= $250  → floor = $100
#   peak >= $400  → hard close at any time (existing GAIN_TIER_HARD_CAP)
#
# When current unrealized falls below the floor, market-close the
# position. Bracket target order remains in place, so if target hits
# first, position closes there. This is the software-side belt for
# bracket-target gives-back.
TRAILING_PROFIT_TIERS = (
    # (peak_threshold_usd, floor_usd)
    (400, 200),  # locks in half the peak at extreme gains
    (250, 100),
    (150,  50),
    ( 80,  20),
    ( 30,   0),  # the critical "no gain ever becomes a loss" rule
)

# LOSS-SIDE HARD CAP: software belt-and-suspenders for the broker stop.
# 2026-05-05: NG short rode 7h losing $702 with bracket stop at $120 — the
# broker stop never fired (root cause TBD; possibly server-side cancellation
# at session boundary). With this cap, the trader market-closes the position
# at ~-$200 unrealized regardless of whether the bracket stop is alive.
# Set at 1.67× the typical per-trade $120 stop budget — generous enough to
# survive normal noise, tight enough to catch broker-stop-failure cases.
LOSS_TIER_HARD_CAP_USD = 200.0

# Per-symbol high-water tracking (process-local; resets on trader restart).
# Maps "SYMBOL_SIDE" → peak unrealized P&L seen this session.
_position_high_water: dict[str, float] = {}


def _close_high_gain_positions(client, account_id) -> list[dict]:
    """Iterate broker positions; market-close any whose unrealized P&L
    exceeds the gain-tier thresholds. Returns list of closures performed."""
    closed: list[dict] = []
    try:
        positions = client.get_positions(account_id)
    except Exception as e:
        print(f"  [gain_tier: get_positions failed: {e}]")
        return closed

    syms_cfg = _load_yaml("symbols.yaml") or {}
    symbols = syms_cfg.get("symbols", {}) or {}

    for p in positions:
        size = int(p.get("size") or 0)
        if size == 0:
            continue
        contract_id = str(p.get("contractId") or p.get("contract") or "")
        if not contract_id:
            continue

        # Resolve symbol root + tick economics
        from hooks.risk_gate import _normalize_root
        symbol = None
        for tok in contract_id.split("."):
            if tok in ("CON", "F", "US", ""):
                continue
            if len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit():
                continue
            symbol = _normalize_root(tok)
            break
        if not symbol:
            continue
        sym_cfg = symbols.get(symbol) or {}
        tick_size = float(sym_cfg.get("tick_size", 0.01))
        tick_value = float(sym_cfg.get("tick_value", 1.0))
        if tick_size <= 0 or tick_value <= 0:
            continue

        type_code = int(p.get("type") or 0)
        side = "long" if type_code == 1 else "short" if type_code == 2 else (
            "long" if size > 0 else "short")
        size = abs(size)
        avg_price = float(p.get("averagePrice") or p.get("avgPrice") or 0)
        if avg_price <= 0:
            continue

        # Get latest price via 1-min bars (cheaper than full quote).
        bars = fetch_bars(client, symbol, minutes=1, lookback=5)
        if bars is None or len(bars) == 0:
            continue
        last_close = float(bars["Close"].iloc[-1])

        # Compute unrealized P&L per position
        if side == "long":
            move = last_close - avg_price
        else:
            move = avg_price - last_close
        ticks = move / tick_size
        unrealized = ticks * tick_value * size

        # Track high-water mark
        key = f"{symbol}_{side}"
        prev_peak = _position_high_water.get(key, 0.0)
        if unrealized > prev_peak:
            _position_high_water[key] = unrealized
            prev_peak = unrealized

        should_close = False
        reason = ""

        if unrealized >= GAIN_TIER_HARD_CAP_USD:
            should_close = True
            reason = (f"hard_cap: unrealized ${unrealized:.2f} "
                      f">= ${GAIN_TIER_HARD_CAP_USD:.2f}")
        elif unrealized <= -LOSS_TIER_HARD_CAP_USD:
            # Loss-side belt-and-suspenders for broker stop failure.
            # See LOSS_TIER_HARD_CAP_USD comment.
            should_close = True
            reason = (f"loss_hard_cap: unrealized ${unrealized:.2f} "
                      f"<= -${LOSS_TIER_HARD_CAP_USD:.2f} — broker stop "
                      f"may have failed; force-flat")
        else:
            # Trailing profit lock — never let a gain turn into a loss.
            # See TRAILING_PROFIT_TIERS comment for tier definitions.
            for peak_threshold, floor in TRAILING_PROFIT_TIERS:
                if prev_peak >= peak_threshold and unrealized < floor:
                    should_close = True
                    reason = (f"trailing_profit_lock: peak ${prev_peak:.2f} "
                              f">= ${peak_threshold} → require >= ${floor}; "
                              f"current ${unrealized:.2f}")
                    break

        if not should_close:
            continue

        # Market-close
        opposite = "sell" if side == "long" else "buy"
        cid = f"gain_tier_close_{int(time.time())}_{symbol}"
        try:
            result = client.place_order(
                account_id=account_id, contract_id=contract_id,
                side=opposite, qty=int(size),
                order_type="market", time_in_force="ioc",
                client_order_id=cid,
            )
            broker_oid = None
            if isinstance(result, dict):
                broker_oid = (result.get("orderId") or result.get("id")
                              or result.get("brokerOrderId"))
            print(f"  [GAIN_TIER_CLOSE] {symbol} {side} {size}ct "
                  f"unrealized=${unrealized:.2f}  reason={reason}")
            db.record_risk_event(
                severity="info", rule="gain_tier_auto_close",
                agent="auto_trader",
                detail={"symbol": symbol, "side": side, "size": size,
                        "unrealized_usd": unrealized, "peak_usd": prev_peak,
                        "reason": reason, "broker_order_id": broker_oid},
            )
            closed.append({
                "symbol": symbol, "side": side, "size": size,
                "unrealized_usd": unrealized, "reason": reason,
            })
            # Reset high-water for this position so future re-entries start fresh
            _position_high_water.pop(key, None)
        except Exception as e:
            print(f"  [gain_tier_close FAILED on {symbol}: {e}]")
            db.record_risk_event(
                severity="warn", rule="gain_tier_close_failed",
                agent="auto_trader",
                detail={"symbol": symbol, "side": side,
                        "unrealized_usd": unrealized, "error": str(e)[:300]},
            )

    return closed


import time  # used by gain_tier function


def _refresh_calendar_if_stale() -> None:
    """Self-heal: rebuild vault/economic_calendar/today.json if missing or
    >6h old. Runs at the top of each scan so the high-impact blackout
    check has fresh data without needing a separate cron job.

    No-op on failure — the staleness warn in the risk hook already surfaces
    the issue if this can't refresh.
    """
    try:
        cal = Path("vault/economic_calendar/today.json")
        needs_refresh = True
        if cal.exists():
            age_h = (datetime.now(tz=timezone.utc).timestamp() - cal.stat().st_mtime) / 3600
            needs_refresh = age_h > 6
        if needs_refresh:
            import subprocess as _sp
            _sp.run(
                [sys.executable, "-m", "scripts.build_economic_calendar"],
                capture_output=True, timeout=30, check=False,
            )
    except Exception:
        pass


def _in_thin_tape_window() -> tuple[bool, str]:
    """True if current ET time falls inside the thin_tape regime window.

    Returns (in_window, reason). Reads `risk_limits.yaml:regime_gates.thin_tape`
    so the source of truth lives in config. Window is interpreted as a
    half-open interval [start, end) in America/New_York time.

    The window may cross midnight (e.g., 21:00 → 04:00 next day); that's
    handled by checking start <= now OR now < end when start > end.
    """
    cfg = (_load_yaml("risk_limits.yaml").get("regime_gates") or {})
    thin = cfg.get("thin_tape") or {}
    if not thin.get("enabled"):
        return False, "regime gate disabled"
    from zoneinfo import ZoneInfo
    et = datetime.now(tz=ZoneInfo("America/New_York"))
    try:
        sh, sm = (int(x) for x in str(thin.get("start_et", "21:00")).split(":"))
        eh, em = (int(x) for x in str(thin.get("end_et",   "04:00")).split(":"))
    except Exception:
        return False, "thin_tape config malformed"
    now_minutes = et.hour * 60 + et.minute
    start_minutes = sh * 60 + sm
    end_minutes = eh * 60 + em
    if start_minutes < end_minutes:
        in_window = start_minutes <= now_minutes < end_minutes
    else:
        # Window wraps midnight (start > end)
        in_window = now_minutes >= start_minutes or now_minutes < end_minutes
    relation = "INSIDE" if in_window else "outside"
    return in_window, (
        f"{et.strftime('%H:%M ET')} {relation} thin-tape window "
        f"{thin.get('start_et')}–{thin.get('end_et')} ET"
    )


def _today_fees_usd() -> float:
    """Sum of estimated round-trip fees on filled orders today.

    Reads `orders` table (status='submitted' and 'filled' both count once
    per round-trip — entry pays the fee). Uses
    `risk_limits.yaml:fees_round_trip_usd` per-symbol schedule.
    """
    db = get_db()
    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    fees_cfg = _load_yaml("risk_limits.yaml").get("fees_round_trip_usd") or {}
    default_fee = float(fees_cfg.get("default", 5.00))
    # Each entry order incurs one round-trip fee. Stops/targets are exits
    # (already counted via the entry). Filter by parent client_order_id
    # pattern: `auto_*` (no _stop/_target suffix) is the entry leg.
    rows = db.connect().execute(
        "SELECT symbol, qty FROM orders "
        "WHERE ts_proposed LIKE ? "
        "  AND agent='auto_trader' "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted', 'filled') ",
        (f"{today_utc}%",),
    ).fetchall()
    total = 0.0
    for r in rows:
        sym = r["symbol"]
        qty = int(r["qty"] or 0)
        per_contract = float(fees_cfg.get(sym, default_fee))
        total += per_contract * qty
    return total


def _engage_auto_halt(halt_until_iso: str, *, reason: str) -> None:
    """Write trading_halt_until into risk_limits.yaml so the risk hook
    auto-blocks orders until that timestamp.

    Targeted text-only edit (no yaml.safe_dump) so YAML comments are preserved.
    Idempotent: if an existing halt is later than ours, leave it alone.
    """
    import re as _re
    import yaml as _yaml
    from pathlib import Path
    path = Path("config/risk_limits.yaml")
    text = path.read_text()
    # Read existing halt only (no rewrite)
    cfg = _yaml.safe_load(text)
    existing = (cfg.get("hard_rules") or {}).get("trading_halt_until", "")
    new_halt = halt_until_iso
    if existing and str(existing) > halt_until_iso:
        new_halt = str(existing)
    if new_halt == str(existing):
        # No change needed
        return
    new_text, n = _re.subn(
        r"(^[ \t]*trading_halt_until:[ \t]*)(?:\"[^\"]*\"|'[^']*'|\S+)([ \t]*(?:#.*)?)$",
        rf'\g<1>"{new_halt}"\g<2>',
        text, count=1, flags=_re.MULTILINE,
    )
    if n != 1:
        # Refuse to corrupt the file; surface the issue.
        get_db().record_risk_event(
            severity="warn", rule="auto_halt_yaml_edit_failed",
            agent="auto_trader",
            detail={"new_halt": new_halt, "reason": reason},
        )
        return
    path.write_text(new_text)
    get_db().record_decision(
        agent="auto_trader", kind="auto_halt_engaged",
        summary=f"Auto-halt engaged until {new_halt}",
        rationale=f"Reason: {reason}", model="system",
    )


def _strategy_recent_streak(label: str, *, window_hours: int = 4) -> tuple[int, int]:
    """Return (consecutive_losers, total_in_window) for a strategy.

    A 'loser' is a thesis whose subsequent stop_hit_observed event landed
    within window_hours of the thesis. We walk most-recent-first; the
    streak count grows while events are losers, breaks on first non-loser.

    Used by the auto-demote rule: 5 consecutive losers in 4h → suspend
    the strategy for the rest of the session.
    """
    db = get_db()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(hours=window_hours)
              ).isoformat(timespec="seconds")
    # Get theses for this strategy (matched via summary LIKE — strategy
    # name is in the rationale field too, but summary is more reliable).
    rows = db.connect().execute(
        """SELECT ts, symbol FROM decisions
           WHERE agent='auto_trader' AND kind='thesis'
             AND summary LIKE ? AND ts >= ?
           ORDER BY ts DESC""",
        (f"%{label}%", cutoff),
    ).fetchall()
    if not rows:
        return 0, 0
    streak = 0
    total = len(rows)
    # For each thesis (newest first), did a stop_hit_observed for that
    # symbol fire within the next 60 minutes?
    for r in rows:
        thesis_ts = r["ts"]
        sym = r["symbol"]
        try:
            t = datetime.fromisoformat(str(thesis_ts).replace("Z", "+00:00"))
        except Exception:
            break
        end = (t + timedelta(minutes=60)).isoformat(timespec="seconds")
        hit = db.connect().execute(
            "SELECT 1 FROM risk_events WHERE rule='stop_hit_observed' "
            "  AND ts > ? AND ts < ? "
            "  AND detail LIKE ? LIMIT 1",
            (thesis_ts, end, f'%"{sym}"%' if sym else '%'),
        ).fetchone()
        if hit:
            streak += 1
        else:
            break
    return streak, total


def _strategy_is_demoted(label: str) -> bool:
    """Strategy is auto-demoted for the rest of the UTC day if it hit
    a 5-consecutive-loser streak earlier today. Stored as risk_events
    rule='strategy_demoted_today' so it survives across scans.
    """
    db = get_db()
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    row = db.connect().execute(
        "SELECT 1 FROM risk_events WHERE rule='strategy_demoted_today' "
        "  AND ts LIKE ? AND detail LIKE ? LIMIT 1",
        (f"{today}%", f'%"strategy": "{label}"%'),
    ).fetchone()
    return row is not None


def _strategy_hit_rate(label: str) -> tuple[float, int, str]:
    """Bayesian-blended hit rate for a strategy from strategy_performance.

    Returns (hit_rate, n_observed, confidence). When no data exists, falls
    back to a conservative 35% prior so unproven strategies need bigger
    rewards to justify firing.
    """
    try:
        from tools.strategy_performance import get_strategy_stats
        stats = get_strategy_stats()
    except Exception:
        return 0.35, 0, "ADVISORY"
    s = stats.get(label)
    if s is None:
        return 0.35, 0, "ADVISORY"
    hr = float(s.blended_hit) if 0 < s.blended_hit < 1 else 0.35
    return hr, int(s.n_observed), str(s.confidence)


def _consecutive_recent_losers() -> int:
    """Count consecutive recent stop-out events (newest first) before a
    non-stop-out outcome appears. Used by autonomous consecutive-loser halt.

    Reads `risk_events.rule = 'stop_hit_observed'` chronologically. We
    consider 'consecutive losers' the run of stop_hit_observed events at the
    tail with no winning event between them. Since we don't yet have a
    'target_hit_observed' counterpart, we approximate: if the most recent
    closed trade was a stop_hit, and the one before that was also a stop_hit
    (within the last 4 hours), the streak counts.
    """
    db = get_db()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(hours=4)
              ).isoformat(timespec="seconds")
    rows = db.connect().execute(
        "SELECT ts, rule FROM risk_events "
        "WHERE rule IN ('stop_hit_observed', 'target_hit_observed', "
        "               'manual_close_observed') "
        "  AND ts >= ? "
        "ORDER BY id DESC",
        (cutoff,),
    ).fetchall()
    streak = 0
    for r in rows:
        if r["rule"] == "stop_hit_observed":
            streak += 1
        else:
            break
    return streak


def _recent_agent_wake_errors(window_minutes: int) -> int:
    """How many wake_error decisions in the recent window across all agents.

    Used to detect cascade conditions where the agent chain is broken — the
    pattern from 2026-04-29 where CIO + Edge Hunter wake_errored for hours
    while auto_trader kept trading.
    """
    db = get_db()
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(minutes=window_minutes)
              ).isoformat(timespec="seconds")
    row = db.connect().execute(
        "SELECT COUNT(*) FROM decisions WHERE kind = 'wake_error' AND ts >= ?",
        (cutoff,),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _today_trade_count_for_symbol(symbol: str) -> int:
    """Count of auto_trader entry orders for `symbol` today (UTC)."""
    db = get_db()
    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    row = db.connect().execute(
        "SELECT COUNT(*) FROM orders "
        "WHERE ts_proposed LIKE ? AND agent='auto_trader' AND symbol=? "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted', 'filled') ",
        (f"{today_utc}%", symbol),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _today_total_trade_count() -> int:
    """Count of auto_trader entry orders today across all symbols."""
    db = get_db()
    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    row = db.connect().execute(
        "SELECT COUNT(*) FROM orders "
        "WHERE ts_proposed LIKE ? AND agent='auto_trader' "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target' "
        "  AND status IN ('submitted', 'filled') ",
        (f"{today_utc}%",),
    ).fetchone()
    return int(row[0] or 0) if row else 0


def _trade_urgency_level() -> tuple[int, dict]:
    """How many tiers of marginal-gate relaxation this scan should apply.

    Returns (level, info_dict). Level > 0 ONLY when ALL of:
      * autonomous_mode is True
      * zero trades have been placed today
      * now is INSIDE the configured RTH window
      * sufficient session time has elapsed without a trade

    Levels:
      0  baseline (autonomous strict floors apply unmodified)
      1  60+ min into RTH with no trades  -- relax marginal gates by one notch
      2  120+ min into RTH with no trades -- relax marginal gates by two notches

    ABSOLUTE safety floors are NEVER relaxed by this:
      * internal_dll_target_usd, daily_loss_limit_usd, trailing_drawdown_usd
      * max_trades_per_day, max_concurrent_positions, daily_fee_budget_usd
      * no_naked_shorts, broker_can_trade, snapshot_freshness
      * all 14 hook-layer checks in apply_risk_gate
    Only rr_floor and EV gate min_expected_net relax, and each has an
    absolute floor at its standard (non-autonomous) value (2.0 and $5).

    Rationale: every no-trade day costs ~$26 in subscription drag (see
    vault/_meta/economics.md). Without an opposing pressure for activity,
    the gate stack treats no-trade days as success even though they're
    losses against the cost meter. Bounded, time-decayed urgency lets
    marginal-but-still-positive-EV trades through during dry sessions.
    """
    fund_cfg = _load_yaml("fund.yaml")
    if not bool(fund_cfg.get("autonomous_mode", False)):
        return 0, {"reason": "not_autonomous"}

    if _today_total_trade_count() > 0:
        return 0, {"reason": "already_traded_today"}

    rules = fund_cfg.get("autonomous_restrictions") or {}
    if not rules.get("rth_only"):
        return 0, {"reason": "rth_only_off"}
    try:
        sh, sm = (int(x) for x in str(rules.get("rth_start_et", "07:30")).split(":"))
        eh, em = (int(x) for x in str(rules.get("rth_end_et", "14:30")).split(":"))
    except Exception:
        return 0, {"reason": "rth_parse_error"}

    from zoneinfo import ZoneInfo as _ZI
    et_now = datetime.now(tz=_ZI("America/New_York"))
    now_min = et_now.hour * 60 + et_now.minute
    rth_open_min = sh * 60 + sm
    rth_close_min = eh * 60 + em

    if not (rth_open_min <= now_min < rth_close_min):
        return 0, {"reason": "outside_rth"}

    minutes_in = now_min - rth_open_min
    if minutes_in < 60:
        return 0, {"minutes_into_rth": minutes_in}
    if minutes_in < 120:
        return 1, {"minutes_into_rth": minutes_in}
    return 2, {"minutes_into_rth": minutes_in}


def _recent_thesis_in_db(symbol: str, minutes: int = 30) -> bool:
    """True if auto_trader recorded a thesis for this symbol in the last N min.
    Prevents re-firing the same setup on every consecutive 5-min scan."""
    from datetime import datetime, timedelta, timezone
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(minutes=minutes)
              ).isoformat(timespec="seconds")
    db = get_db()
    row = db.connect().execute(
        "SELECT 1 FROM decisions WHERE agent='auto_trader' AND kind='thesis' "
        "AND symbol=? AND ts >= ? LIMIT 1",
        (symbol, cutoff),
    ).fetchone()
    return row is not None


def _compute_unrealized_pl(client, positions: list[dict]) -> float:
    """Sum unrealized P&L across open positions using latest 1-min bar close
    as the mark. Mirrors Orchestrator.capture_account_snapshot's logic.

    Returns 0.0 if positions is empty or all marks fail. A failed mark on
    one leg is treated as 0 for that leg, never raises — partial unrealized
    is better than blank (and blank is what caused the 2026-05-05 NG ride).
    """
    if not positions:
        return 0.0
    db = get_db()
    try:
        from hooks.risk_gate import _normalize_root
    except Exception:
        _normalize_root = lambda x: x
    symbols_cfg = _load_yaml("symbols.yaml").get("symbols", {})
    now = datetime.now(tz=timezone.utc)
    total = 0.0
    for p in positions:
        size = int(p.get("size") or p.get("netQuantity") or 0)
        if size == 0:
            continue
        contract_id = p.get("contractId") or p.get("contract") or ""
        if not contract_id:
            continue
        avg_price = float(p.get("avgPrice") or p.get("averagePrice") or 0)
        if avg_price <= 0:
            continue
        type_code = int(p.get("type") or 0)
        if type_code == 1:
            sign = 1
        elif type_code == 2:
            sign = -1
        else:
            sign = 1 if size > 0 else -1
        size = abs(size)
        root = None
        for tok in str(contract_id).split("."):
            if tok in ("CON", "F", "US", "") or (
                len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit()
            ):
                continue
            root = _normalize_root(tok)
            break
        meta = symbols_cfg.get(root or "", {}) if root else {}
        tick_size = float(meta.get("tick_size") or 0)
        tick_value = float(meta.get("tick_value") or 0)
        if tick_size <= 0 or tick_value <= 0:
            db.record_risk_event(
                severity="warn", rule="unrealized_pl_skipped",
                agent="auto_trader",
                detail={"contract_id": contract_id, "root": root,
                        "reason": "missing tick_size/tick_value in symbols.yaml"},
            )
            continue
        try:
            bars = client.get_bars(
                contract_id=contract_id,
                start_time=(now - timedelta(minutes=10)).isoformat(),
                end_time=now.isoformat(),
                unit=2, unit_number=1, limit=10, live=False,
            )
            mark = float(bars[-1].get("c") or bars[-1].get("close") or 0) if bars else 0
        except Exception as e:
            db.record_risk_event(
                severity="warn", rule="unrealized_pl_skipped",
                agent="auto_trader",
                detail={"contract_id": contract_id,
                        "reason": f"bars fetch failed: {e}"[:200]},
            )
            mark = 0
        if mark <= 0:
            continue
        points = mark - avg_price
        total += sign * size * (points / tick_size) * tick_value
    return total


def _capture_account_snapshot(client, account_id) -> dict | None:
    """Pull live broker state and write an account_snapshots row before the
    scan runs. Mirrors `Orchestrator.capture_account_snapshot` but lives here
    because auto_trader runs as a separate process and the orchestrator may
    not be alive.

    Without this, every P&L-aware risk check (DLL, TDD, defensive ladder,
    daily target lock) reads `snap=None` and short-circuits to allow.
    The 2026-04-29 DLL-breach incident occurred precisely because
    no process was writing snapshots while auto_trader was trading.
    """
    db = get_db()
    try:
        accounts = client.get_accounts()
        mine = next(
            (a for a in accounts if str(a.get("id")) == str(account_id)), None
        )
        if mine is None:
            db.record_risk_event(
                severity="warn", rule="snapshot_capture_failed",
                agent="auto_trader",
                detail={"error": f"account {account_id} not visible"},
            )
            return None
        balance = float(mine.get("balance", 0) or 0)
        can_trade = bool(mine.get("canTrade", True))
        positions = client.get_positions(account_id)
        open_contracts = sum(
            int(p.get("size") or p.get("netQuantity") or 0) for p in positions
        )

        # Realized day P&L = balance - first snapshot of UTC day
        first_today = db.first_snapshot_today_utc()
        realized_day = (balance - float(first_today["balance_usd"])
                        if first_today else 0.0)

        # Trailing DD = peak balance ever seen (or starting balance) − current
        risk_cfg = _load_yaml("risk_limits.yaml")
        starting = float(risk_cfg.get("account", {}).get("starting_balance", 0))
        peak = db.peak_eod_balance(fallback=starting)
        trailing_dd = max(0.0, peak - balance)
        env = str(risk_cfg.get("account", {}).get("environment", "combine"))

        # Unrealized P&L — must compute or DLL/TDD/ladder projections are
        # blind to bleeding open positions. 2026-05-05 incident: NG short
        # rode unhedged for 7h losing $702 while every snap recorded
        # unrealized=0, so no defensive ladder ever projected the loss.
        unrealized_total = _compute_unrealized_pl(client, positions)

        db.record_account_snapshot(
            balance_usd=balance, environment=env,
            unrealized_pl_usd=unrealized_total,
            realized_pl_day_usd=realized_day,
            trailing_dd_usd=trailing_dd,
            open_contracts_total=open_contracts,
            can_trade=can_trade,
        )
        if not can_trade:
            db.record_risk_event(
                severity="warn", rule="broker_can_trade_false",
                agent="auto_trader",
                detail={"balance_usd": balance,
                        "note": "Broker reports canTrade=false."},
            )
        return {"balance_usd": balance, "realized_pl_day_usd": realized_day,
                "trailing_dd_usd": trailing_dd, "can_trade": can_trade}
    except Exception as e:
        # Network down (DNS failure, broker timeout, etc.) — instead of
        # returning None and letting the trader die from snapshot-age,
        # write a DEGRADED heartbeat row using the last known balance with
        # can_trade=False. This keeps the daemon's snapshot-age check
        # fresh (no false revival thrash) while the gate still refuses
        # new orders because can_trade=False. When network recovers,
        # the next call gets fresh real data.
        # 2026-05-07: added after wifi-drop death-revive thrash diagnosis.
        err_msg = str(e)[:300]
        db.record_risk_event(
            severity="warn", rule="snapshot_capture_failed",
            agent="auto_trader", detail={"error": err_msg, "degraded_heartbeat": True},
        )
        try:
            last = db.latest_account_snapshot()
            if last:
                db.record_account_snapshot(
                    balance_usd=float(last.get("balance_usd") or 0),
                    environment=str(last.get("environment") or "combine"),
                    unrealized_pl_usd=0.0,
                    realized_pl_day_usd=float(last.get("realized_pl_day_usd") or 0),
                    trailing_dd_usd=float(last.get("trailing_dd_usd") or 0),
                    open_contracts_total=int(last.get("open_contracts_total") or 0),
                    can_trade=False,   # explicit refusal for the gate
                )
                print(f"  [degraded heartbeat written: {err_msg[:80]}]")
        except Exception:
            pass  # best-effort; if even this fails, trader will die naturally
        return None


def _enforce_daily_target_action(client, account_id, snap: dict, db) -> None:
    """When realized day P&L >= daily_hard_target_usd, take the configured
    action beyond just blocking new entries:

      block_new      → no extra action (gate already blocks new orders)
      cancel_working → cancel all unfilled entry orders so they can't
                       fire after the lock kicks in (this addresses
                       2026-05-05: a working limit could still tag and
                       open a position even though the gate refused new
                       _new_ orders).
      force_flat     → cancel + market-close all open positions.

    Fires at most once per UTC day (action is one-shot — once positions
    are flat, leaving the auto_trader to keep running is fine; it just
    won't enter new trades).
    """
    pacing = (_load_yaml("risk_limits.yaml").get("combine_pacing") or {})
    hard = float(pacing.get("daily_hard_target_usd", 0) or 0)
    action = str(pacing.get("daily_target_action", "block_new")).lower()
    if hard <= 0 or action == "block_new":
        return

    realized = float(snap.get("realized_pl_day_usd") or 0.0)
    if realized < hard:
        return

    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    already = db.connect().execute(
        "SELECT 1 FROM risk_events "
        "WHERE rule='daily_target_action_fired' AND ts LIKE ? LIMIT 1",
        (f"{today}%",),
    ).fetchone()
    if already:
        return

    cancelled = 0
    flattened = 0
    try:
        working = client.get_working_orders(account_id) or []
        for o in working:
            tag = str(o.get("customTag") or "")
            # Cancel auto-trader entries (no _stop / _target suffix)
            if tag.startswith("auto_") and not (tag.endswith("_stop")
                                                  or tag.endswith("_target")):
                try:
                    client.cancel_order(account_id, o.get("id") or o.get("orderId"))
                    cancelled += 1
                except Exception:
                    pass
            # In force_flat, also cancel protective legs (we'll close at market)
            if action == "force_flat" and tag.startswith("auto_"):
                try:
                    client.cancel_order(account_id, o.get("id") or o.get("orderId"))
                    cancelled += 1
                except Exception:
                    pass
    except Exception:
        pass

    if action == "force_flat":
        try:
            positions = client.get_positions(account_id) or []
            for p in positions:
                size = int(p.get("size") or p.get("netQuantity") or 0)
                if size == 0:
                    continue
                contract = p.get("contractId") or p.get("contract") or ""
                type_code = int(p.get("type") or 0)
                opposite = "sell" if type_code == 1 else "buy"
                try:
                    client.place_order(
                        account_id=account_id, contract_id=contract,
                        side=opposite, qty=abs(size),
                        order_type="market", time_in_force="ioc",
                        client_order_id=f"daily_target_flat_{int(time.time())}_{contract}",
                    )
                    flattened += 1
                except Exception:
                    pass
        except Exception:
            pass

    db.record_risk_event(
        severity="info", rule="daily_target_action_fired",
        agent="auto_trader",
        detail={"action": action, "realized_pl_day_usd": realized,
                "hard_target": hard,
                "cancelled_working": cancelled, "flattened_positions": flattened,
                "note": "Daily target hit — extra action beyond block_new."},
    )
    print(f"  [DAILY-TARGET-ACTION fired: action={action}, "
          f"cancelled={cancelled}, flattened={flattened}]")


def _audit_risk_config_drift(db) -> None:
    """Log a risk_event when critical gates are disabled in risk_limits.yaml.

    Fires at most once per UTC day per disabled gate. The point is visibility:
    if someone (human or agent) edits the config to disable a profit-protect
    or loss-protect gate, the EOD report shows it loud.
    """
    try:
        limits = _load_yaml("risk_limits.yaml")
        pacing = limits.get("combine_pacing", {}) or {}
        account = limits.get("account", {}) or {}

        disabled = []
        if float(pacing.get("daily_hard_target_usd", 0) or 0) <= 0:
            disabled.append(("combine_pacing.daily_hard_target_usd",
                             "profit-lock disabled — no per-day cap on entries"))
        if float(pacing.get("partial_giveback_pct", 0) or 0) <= 0:
            disabled.append(("combine_pacing.partial_giveback_pct",
                             "giveback floor disabled — peak-to-close protection off"))
        if float(account.get("daily_loss_limit_usd", 0) or 0) <= 0:
            disabled.append(("account.daily_loss_limit_usd",
                             "DLL disabled — no per-day loss cap"))
        if float(account.get("trailing_drawdown_usd", 0) or 0) <= 0:
            disabled.append(("account.trailing_drawdown_usd",
                             "TDD disabled — no trailing-drawdown cap"))

        if not disabled:
            return

        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        for path, msg in disabled:
            row = db.connect().execute(
                "SELECT 1 FROM risk_events "
                "WHERE rule='risk_config_drift' AND ts LIKE ? "
                "AND detail LIKE ? LIMIT 1",
                (f"{today}%", f"%{path}%"),
            ).fetchone()
            if row:
                continue
            db.record_risk_event(
                severity="warn", rule="risk_config_drift",
                agent="auto_trader",
                detail={"path": path, "message": msg,
                        "note": "Critical safety gate disabled in risk_limits.yaml"},
            )
            print(f"  [config_drift_warning: {path} — {msg}]")
    except Exception as e:
        # Never let the audit break the scan
        try:
            db.record_risk_event(
                severity="warn", rule="risk_config_drift_audit_failed",
                agent="auto_trader", detail={"error": str(e)[:200]},
            )
        except Exception:
            pass


def scan_once(*, dry_run: bool = False, cooldown_minutes: int = 45) -> dict:
    """One scan pass over the focus universe. Returns a summary dict."""
    db = get_db()
    try:
        client = get_client()
        account_id = get_account_id()
    except Exception as e:
        return {"status": "broker_unavailable", "error": str(e)}

    # Step −1: SNAPSHOT — pull broker state into account_snapshots so the
    # P&L-aware risk checks have data. Critical: auto_trader runs separately
    # from the orchestrator and the table goes empty otherwise. Failures
    # log + continue (better partial enforcement than zero enforcement).
    # Self-heal economic calendar (rebuild if missing or >6h old)
    _refresh_calendar_if_stale()

    # Surface critical-gate disables. 2026-05-05: a "diagnostic mode" edit
    # zeroed daily_hard_target_usd at 21:23 ET. Two minutes later the
    # trader picked up the new config on restart and entered three more
    # trades that gave back $837. This check fires once per UTC day per
    # disabled gate so the EOD report can't miss it.
    _audit_risk_config_drift(db)

    snap_result = _capture_account_snapshot(client, account_id)

    # Daily-target action (added 2026-05-05): when realized day P&L
    # exceeds daily_hard_target_usd, optionally cancel working orders
    # and/or force-flat existing positions. See risk_limits.yaml:
    # combine_pacing.daily_target_action.
    if snap_result and not dry_run:
        try:
            _enforce_daily_target_action(client, account_id, snap_result, db)
        except Exception as e:
            print(f"  [daily_target_action failed: {e}]")

    # Step −0.95: LOSS ALERTS — fire push notifications on threshold crosses.
    # No-op when DISCORD_WEBHOOK_URL / TELEGRAM_* aren't set in .env.
    # Logs locally regardless. Once-per-session dedup is in the alerter.
    if snap_result:
        try:
            from scripts.loss_alerter import check_and_alert
            check_and_alert(
                balance=snap_result["balance_usd"],
                day_pl=(snap_result.get("realized_pl_day_usd", 0)
                        + snap_result.get("unrealized_pl_usd", 0)),
                can_trade=snap_result.get("can_trade", True),
            )
        except Exception as e:
            db.record_risk_event(
                severity="warn", rule="loss_alerter_failed",
                agent="auto_trader", detail={"error": str(e)[:200]},
            )

    if snap_result and not snap_result.get("can_trade", True):
        # Topstep flipped canTrade=false. Stop the scan immediately.
        print(f"  HALTED — broker reports canTrade=false (balance "
              f"${snap_result['balance_usd']:.2f}). Skipping all symbols.")
        return {"status": "broker_halted",
                "balance_usd": snap_result["balance_usd"]}

    # Step −0.9: HARD INTERNAL-DLL KILL — independent of the hook layer.
    # The risk_gate's _check_daily_loss_limit relies on snapshots and a
    # complex projection. This is the raw "if we lost too much today,
    # stop" check that runs every scan regardless of hook plumbing.
    # 2026-04-29 incident: $1,013 drawdown despite $500 internal target.
    # Snap may be missing on first scan — fall through to broker balance.
    if snap_result:
        balance = snap_result["balance_usd"]
        risk_cfg = _load_yaml("risk_limits.yaml")
        starting = float(risk_cfg.get("account", {}).get("starting_balance", 50000))
        internal_dll = float(
            risk_cfg.get("account", {}).get("internal_dll_target_usd", 500)
        )
        topstep_dll = float(
            risk_cfg.get("account", {}).get("daily_loss_limit_usd", 1000)
        )
        # Compare today's realized P&L to the internal DLL.
        # NOTE: this is "today's realized day P&L" not "drawdown from start".
        # If account is already in drawdown when the day opens, that drawdown
        # doesn't reset — we still want to allow trading up to the daily
        # tolerance.
        today_realized = snap_result.get("realized_pl_day_usd", 0.0)
        if today_realized <= -internal_dll:
            print(f"  HALTED — today's realized P&L ${today_realized:+.2f} "
                  f"<= -${internal_dll:.0f} internal DLL. Stop trading until "
                  f"session close.")
            db.record_risk_event(
                severity="block", rule="internal_dll_hard_kill",
                agent="auto_trader",
                detail={"realized_pl_day": today_realized,
                        "internal_dll": internal_dll,
                        "balance_usd": balance},
            )
            return {"status": "internal_dll_hit",
                    "realized_pl_day_usd": today_realized}
        # TDD-ANCHOR-LEADING SAFETY HALT: replaces the old cumulative-DD
        # check that was redundantly tighter than Topstep's actual TDD.
        # Topstep's TDD floor = max(starting, peak_eod) - trailing_drawdown_usd.
        # We halt when balance is within $200 of that floor, leading Topstep
        # by a small buffer so we never reach their wall.
        tdd_usd = float(risk_cfg.get("account", {}).get("trailing_drawdown_usd", 2000))
        peak_eod = db.peak_eod_balance(fallback=starting)
        tdd_anchor = max(starting, peak_eod)
        tdd_floor = tdd_anchor - tdd_usd
        soft_halt = tdd_floor + 200
        if balance <= soft_halt:
            print(f"  HALTED — balance ${balance:.2f} within $200 of TDD floor "
                  f"${tdd_floor:.2f} (anchor ${tdd_anchor:.2f}). Halt to "
                  f"preserve headroom; need a green session before resuming.")
            db.record_risk_event(
                severity="block", rule="tdd_anchor_leading_halt",
                agent="auto_trader",
                detail={"balance": balance, "tdd_floor": tdd_floor,
                        "tdd_anchor": tdd_anchor, "soft_halt": soft_halt},
            )
            return {"status": "tdd_anchor_halt", "balance": balance}

    # Step −0.85: GLOBEX-REOPEN BUFFER — give the snapshot pipeline time
    # to write rows before any trade fires. Catches "system started fresh,
    # snapshot table empty, P&L checks no-op" pattern from 2026-04-29.
    sessions_cfg = (_load_yaml("risk_limits.yaml").get("sessions") or {})
    reopen_buffer = int(sessions_cfg.get("block_first_n_minutes_after_globex_reopen", 0))
    if reopen_buffer > 0:
        from zoneinfo import ZoneInfo as _ZI
        ct_now = datetime.now(tz=_ZI("America/Chicago"))
        # Globex re-opens at 17:00 CT Sunday and again each weekday after the
        # daily 16:00-17:00 CT maintenance break. We treat 17:00-17:30 CT every
        # day as the buffer window.
        if ct_now.hour == 17 and ct_now.minute < reopen_buffer:
            print(f"  REOPEN-BUFFER — within {reopen_buffer} min of 17:00 CT "
                  f"Globex reopen ({ct_now.strftime('%H:%M CT')}). "
                  f"Letting snapshot pipeline catch up.")
            db.record_risk_event(
                severity="info", rule="globex_reopen_buffer_block",
                agent="auto_trader",
                detail={"now_ct": ct_now.strftime("%H:%M"),
                        "buffer_minutes": reopen_buffer},
            )
            return {"status": "globex_reopen_buffer"}

    # Step −0.8: REGIME GATE — block all entries during thin-tape window.
    # 2026-04-29 incident: $1,013 lost during 03:30-07:00 UTC (Asian thin
    # tape). Strategies generated noise as signal. The blanket block is
    # the simplest and safest response.
    in_thin_tape, thin_reason = _in_thin_tape_window()
    if in_thin_tape:
        print(f"  REGIME-BLOCKED — {thin_reason}. No new entries.")
        db.record_risk_event(
            severity="info", rule="thin_tape_regime_block",
            agent="auto_trader", detail={"reason": thin_reason},
        )
        # Still run the snapshot capture (already done above) but skip the
        # symbol loop. Keeps monitoring + fee tracking alive.
        return {"status": "thin_tape_blocked", "reason": thin_reason}

    # Step −0.7: AUTONOMOUS-MODE WINDOW — when running unattended, additionally
    # restrict to RTH only (07:30-14:30 ET). Today's loss happened entirely
    # outside RTH. Read the autonomous flag from fund.yaml, not risk_limits.
    fund_cfg = _load_yaml("fund.yaml")
    autonomous = bool(fund_cfg.get("autonomous_mode", False))
    autonomous_rules = fund_cfg.get("autonomous_restrictions") or {}
    if autonomous and autonomous_rules.get("rth_only"):
        from zoneinfo import ZoneInfo as _ZI
        et_now = datetime.now(tz=_ZI("America/New_York"))
        try:
            sh, sm = (int(x) for x in str(autonomous_rules.get("rth_start_et", "07:30")).split(":"))
            eh, em = (int(x) for x in str(autonomous_rules.get("rth_end_et", "14:30")).split(":"))
        except Exception:
            sh, sm, eh, em = 7, 30, 14, 30
        now_min = et_now.hour * 60 + et_now.minute
        in_rth = (sh*60+sm) <= now_min < (eh*60+em)
        if not in_rth:
            print(f"  AUTONOMOUS-RTH-ONLY — {et_now.strftime('%H:%M ET')} "
                  f"outside {sh:02d}:{sm:02d}–{eh:02d}:{em:02d} ET window. "
                  f"Autonomous mode forbids overnight/extended-hours entries.")
            db.record_risk_event(
                severity="info", rule="autonomous_rth_only_block",
                agent="auto_trader",
                detail={"now_et": et_now.strftime("%H:%M"),
                        "rth_window": f"{sh:02d}:{sm:02d}-{eh:02d}:{em:02d}"},
            )
            return {"status": "autonomous_outside_rth"}

    # Step −0.65: HEALTH CHECKS (autonomous-mode only) — auto-halt cascade.
    # 2026-04-29 lesson: agents crashed for 4+ hours but auto_trader kept
    # trading because the two paths don't talk to each other. These checks
    # close that loop.
    if autonomous and autonomous_rules:
        # Consecutive-loser halt: 3 stop-outs in a row → 60-min pause.
        # Bellafiore "Playbook" rule, encoded.
        cl_threshold = int(autonomous_rules.get("consecutive_losers_halt", 0) or 0)
        if cl_threshold > 0:
            streak = _consecutive_recent_losers()
            if streak >= cl_threshold:
                pause = int(autonomous_rules.get("consecutive_loser_pause_minutes", 60))
                from datetime import datetime as _dt, timedelta as _td, timezone as _tz
                halt_until = (_dt.now(tz=_tz.utc) + _td(minutes=pause)
                              ).isoformat(timespec="seconds") + "Z"
                print(f"  CONSECUTIVE-LOSER HALT — {streak} stop-outs in a row "
                      f"(threshold {cl_threshold}). Pausing for {pause} min.")
                db.record_risk_event(
                    severity="block", rule="consecutive_loser_pause",
                    agent="auto_trader",
                    detail={"streak": streak, "pause_minutes": pause,
                            "halt_until": halt_until},
                )
                # Engage the standard auto-halt mechanism so the agent chain
                # also respects this. Edits risk_limits.yaml in place.
                _engage_auto_halt(halt_until,
                                  reason=f"consecutive {streak} losers")
                return {"status": "consecutive_loser_pause",
                        "streak": streak, "halt_until": halt_until}

        # Agent-wake-error cascade halt: agents are crashing → don't trade.
        ae_threshold = int(autonomous_rules.get("agent_wake_error_threshold", 0) or 0)
        ae_window = int(autonomous_rules.get("agent_wake_error_window_minutes", 30))
        if ae_threshold > 0:
            errs = _recent_agent_wake_errors(ae_window)
            if errs >= ae_threshold:
                print(f"  AGENT-CASCADE HALT — {errs} wake_errors in last "
                      f"{ae_window} min (threshold {ae_threshold}). "
                      f"Agents are broken; pausing trading.")
                from datetime import datetime as _dt, timedelta as _td, timezone as _tz
                halt_until = (_dt.now(tz=_tz.utc) + _td(hours=1)
                              ).isoformat(timespec="seconds") + "Z"
                db.record_risk_event(
                    severity="block", rule="agent_cascade_halt",
                    agent="auto_trader",
                    detail={"wake_errors": errs, "window_minutes": ae_window,
                            "halt_until": halt_until},
                )
                _engage_auto_halt(halt_until,
                                  reason=f"agent cascade — {errs} wake_errors")
                return {"status": "agent_cascade_halt",
                        "wake_errors": errs, "halt_until": halt_until}

    # Step −0.6: DAILY FEE BUDGET — halt if today's fees exceed the budget.
    # Catches the cost-frequency loop pattern (today: ~$150 in fees alone
    # over 4 hours despite per-trade gates being green).
    risk_cfg = _load_yaml("risk_limits.yaml")
    cost_cfg = risk_cfg.get("cost_discipline") or {}
    fee_budget = float(cost_cfg.get("daily_fee_budget_usd", 30.0))
    # Tighten budget under autonomous mode if configured
    if autonomous and autonomous_rules.get("daily_fee_budget_usd"):
        fee_budget = float(autonomous_rules["daily_fee_budget_usd"])
    fees_so_far = _today_fees_usd()
    if fees_so_far >= fee_budget:
        print(f"  FEE-BUDGET-HIT — today's fees ${fees_so_far:.2f} ≥ "
              f"budget ${fee_budget:.2f}. Halt new entries; manage book only.")
        db.record_risk_event(
            severity="block", rule="daily_fee_budget_exhausted",
            agent="auto_trader",
            detail={"fees_so_far": fees_so_far, "budget": fee_budget,
                    "autonomous": autonomous},
        )
        return {"status": "fee_budget_exhausted",
                "fees_so_far": fees_so_far, "budget": fee_budget}

    # Step −0.5: TOTAL TRADE-COUNT CAP (cost-aware). Independent of the hook's
    # max_trades_per_day which gates on risk_events; this gates on actual
    # broker-side filled/submitted entries.
    daily_count_cap = int(cost_cfg.get("max_trades_per_day_cost_aware", 12))
    if autonomous and autonomous_rules.get("max_trades_per_day"):
        daily_count_cap = int(autonomous_rules["max_trades_per_day"])
    today_trades = _today_total_trade_count()
    if today_trades >= daily_count_cap:
        print(f"  TRADE-COUNT-HIT — {today_trades} entries today ≥ cap "
              f"{daily_count_cap}. Halt; manage book only.")
        db.record_risk_event(
            severity="block", rule="daily_trade_count_cost_aware",
            agent="auto_trader",
            detail={"trades_today": today_trades, "cap": daily_count_cap,
                    "autonomous": autonomous},
        )
        return {"status": "trade_count_exhausted",
                "trades_today": today_trades, "cap": daily_count_cap}

    universe = load_focus_universe()
    # Show ET (Eastern Time) for human readability -- DB still stores UTC
    from zoneinfo import ZoneInfo
    _et = datetime.now(tz=ZoneInfo("America/New_York")).strftime("%Y-%m-%d %H:%M:%S ET")
    print(f"[{_et}] scanning {len(universe)} symbols: {universe}")

    # OPPORTUNITY-COST awareness: when autonomous + zero trades today + N min
    # into RTH, gradually relax marginal gates (rr_floor, EV min) toward the
    # standard (non-autonomous) floors. Hard safety floors (DLL, TDD, max
    # trades, fee budget, hook-layer) are never touched. See
    # _trade_urgency_level() docstring.
    urgency_level, urgency_info = _trade_urgency_level()
    if urgency_level > 0:
        print(f"  TRADE-URGENCY level={urgency_level} "
              f"({urgency_info.get('minutes_into_rth')} min into RTH, 0 trades). "
              f"rr_floor and EV-min are relaxed; safety floors unchanged.")
        db.record_risk_event(
            severity="info", rule="trade_urgency_relaxation",
            agent="auto_trader",
            detail={"level": urgency_level, **urgency_info},
        )

    summary = {"scanned": 0, "triggers": 0, "blocked": 0, "placed": 0,
               "skipped_already_in_trade": 0, "skipped_recent_thesis": 0,
               "errors": 0}

    # Refresh DB ↔ broker so per_symbol_limits check operates on truth
    if not dry_run:
        try:
            from scripts.reconcile_positions import reconcile
            reconcile(verbose=False)
        except Exception as e:
            print(f"  [reconcile failed: {e}]")

    # GAIN-TIER AUTO-CLOSE (added 2026-05-04): for any open broker position
    # whose unrealized P&L exceeds GAIN_TIER_HARD_CAP_USD ($400) OR whose
    # peak unrealized exceeded GAIN_TIER_HIGH_WATER_USD ($150) before
    # reverting below GAIN_TIER_FLOOR_USD ($50), market-close the position.
    # This protects against (a) target order not firing on big winners and
    # (b) gain-then-reverse from positive to negative. Catches phantom
    # positions that the OCO race created with no protective target.
    if not dry_run:
        try:
            _close_high_gain_positions(client, account_id)
        except Exception as e:
            print(f"  [gain_tier_auto_close failed: {e}]")

    # ORPHAN CLEANUP: cancel two classes of stale orders:
    #   (a) Orphans — working orders on contracts where the position is gone
    #       (entry filled, stop hit, leaving target on the books — or vice
    #       versa). Without this, an orphan would re-open a fresh position
    #       on the wrong side if filled later.
    #   (b) Stale entry limits — entry limit orders older than 10 minutes
    #       that haven't filled. The signal that placed them is no longer
    #       valid; price moved on. User directive 2026-04-29: "some aren't
    #       even being filled" — these eat exchange-side resources and
    #       sometimes incur cancel/modify fees if they auto-expire.
    if not dry_run:
        try:
            broker_positions = client.get_positions(account_id)
            broker_orders = client.get_working_orders(account_id)
            # Build position-direction map per contract (1=long, 2=short)
            with_position = set()
            pos_dir_by_contract: dict[str, str] = {}
            for p in broker_positions:
                sz = int(p.get("size") or 0)
                if sz == 0:
                    continue
                cid = p.get("contractId")
                with_position.add(cid)
                pos_type = int(p.get("type") or 0)
                if pos_type == 1:
                    pos_dir_by_contract[cid] = "long"
                elif pos_type == 2:
                    pos_dir_by_contract[cid] = "short"
            cancelled = 0
            stale_cancelled = 0
            misdirected_cancelled = 0
            from datetime import datetime as _dt, timedelta as _td, timezone as _tz
            stale_cutoff = _dt.now(tz=_tz.utc) - _td(minutes=10)
            for o in broker_orders:
                contract = o.get("contractId")
                tag = str(o.get("customTag") or "")
                if not (tag.startswith("auto_") or tag.startswith("recovery_")):
                    continue
                oid = o.get("id") or o.get("orderId")
                # (a) orphan: no position on this contract
                is_orphan = contract not in with_position
                # (b) stale entry: type=2 (limit), no _stop / _target suffix
                is_stale_entry = False
                if (int(o.get("type") or 0) == 2
                        and not tag.endswith("_stop")
                        and not tag.endswith("_target")):
                    ts_str = o.get("creationTimestamp") or ""
                    try:
                        ts = _dt.fromisoformat(ts_str.replace("Z", "+00:00"))
                        if ts < stale_cutoff:
                            is_stale_entry = True
                    except Exception:
                        pass
                # (c) misdirected protective leg: a working _stop or _target
                # tagged for an entry whose intended-side does NOT match the
                # current position direction. This catches the OCO race where
                # one leg fills (closing the position), then the other leg
                # fires before the next scan and opens an UNWANTED opposite
                # position. Caught 2026-05-01: 6E short target hit, then
                # the still-working buy stop fired, opening an unintended
                # long. The stop-loss-attached-to-short was now
                # protecting nothing -- and worse, was a position-builder.
                is_misdirected = False
                if tag.endswith("_stop") or tag.endswith("_target"):
                    base_tag = tag
                    for suffix in ("_stop", "_target"):
                        if base_tag.endswith(suffix):
                            base_tag = base_tag[: -len(suffix)]
                            break
                    try:
                        row = db.connect().execute(
                            "SELECT side FROM orders WHERE client_order_id = ? LIMIT 1",
                            (base_tag,),
                        ).fetchone()
                    except Exception:
                        row = None
                    if row:
                        entry_side = (row[0] or "").lower()
                        expected_pos = "long" if entry_side == "buy" else "short"
                        actual_pos = pos_dir_by_contract.get(contract)
                        if actual_pos != expected_pos:
                            is_misdirected = True
                if not (is_orphan or is_stale_entry or is_misdirected):
                    continue
                try:
                    client.cancel_order(account_id, oid)
                    if is_misdirected:
                        misdirected_cancelled += 1
                        db.record_risk_event(
                            severity="breach", rule="bracket_oco_misdirected_leg",
                            agent="auto_trader",
                            detail={"contract": contract, "tag": tag,
                                    "expected_pos": expected_pos if row else None,
                                    "actual_pos": pos_dir_by_contract.get(contract)},
                        )
                    elif is_stale_entry:
                        stale_cancelled += 1
                    else:
                        cancelled += 1
                except Exception:
                    pass
            if cancelled or stale_cancelled or misdirected_cancelled:
                msg = []
                if cancelled:
                    msg.append(f"{cancelled} orphan(s)")
                if stale_cancelled:
                    msg.append(f"{stale_cancelled} stale entry/entries")
                if misdirected_cancelled:
                    msg.append(f"{misdirected_cancelled} misdirected protective leg(s)")
                print(f"  [cleanup: cancelled {' + '.join(msg)}]")

            # PROTECTIVE-STOP VERIFICATION (added 2026-05-05): for every
            # open position on the broker, confirm a working order tagged
            # _stop exists for that contract. If not, the bracket stop has
            # been cancelled (server-side at session boundary, or by our
            # own orphan/misdirected cleanup) and the position is naked.
            # The LOSS_TIER_HARD_CAP_USD floor in _close_high_gain_positions
            # is the actual rescue; this block surfaces the condition so we
            # can see how often it happens and chase the root cause.
            for contract_id, side in pos_dir_by_contract.items():
                has_stop = any(
                    str(o.get("contractId")) == contract_id
                    and str(o.get("customTag") or "").endswith("_stop")
                    for o in broker_orders
                )
                if has_stop:
                    continue
                # Avoid spamming: only log once per (contract, UTC day).
                today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
                already = db.connect().execute(
                    "SELECT 1 FROM risk_events "
                    "WHERE rule='protective_stop_missing' AND ts LIKE ? "
                    "AND detail LIKE ? LIMIT 1",
                    (f"{today}%", f"%{contract_id}%"),
                ).fetchone()
                if already:
                    continue
                db.record_risk_event(
                    severity="breach", rule="protective_stop_missing",
                    agent="auto_trader",
                    detail={"contract": contract_id, "side": side,
                            "note": ("Open position has no working _stop "
                                     "order — LOSS_TIER_HARD_CAP will "
                                     "force-flat at -$200 unrealized.")},
                )
                print(f"  [WARN: {contract_id} {side} has NO working stop — "
                      f"loss-cap is the only protection]")
        except Exception as e:
            print(f"  [cleanup failed: {e}]")

    # GUARD 0 (account-wide): max concurrent open positions.
    # Default 5 (Topstep $50K Combine cap). Autonomous mode tightens to 2
    # because today's incident showed 5 simultaneous bleed positions cost
    # $35-50 per stop-out cycle.
    MAX_CONCURRENT_POSITIONS = 5
    if autonomous and autonomous_rules.get("max_concurrent_positions"):
        MAX_CONCURRENT_POSITIONS = int(autonomous_rules["max_concurrent_positions"])
    open_positions = _count_open_positions(client, account_id)
    if open_positions >= MAX_CONCURRENT_POSITIONS:
        print(f"  GLOBAL SKIP — {open_positions} positions already open "
              f"(cap is {MAX_CONCURRENT_POSITIONS}"
              f"{', autonomous' if autonomous else ''}).")
        summary["skipped_concurrent_cap"] = summary.get("skipped_concurrent_cap", 0) + 1
        return summary

    # Pre-loop: per-strategy session shot count under autonomous mode
    autonomous_per_strategy_used: dict[str, int] = {}
    autonomous_per_strategy_cap = 1
    if autonomous and autonomous_rules.get("per_strategy_per_session_cap"):
        autonomous_per_strategy_cap = int(autonomous_rules["per_strategy_per_session_cap"])
    # Pre-load today's per-symbol trade counts once (avoid N+1 query)
    per_symbol_warn = int(cost_cfg.get("per_symbol_trade_count_warn", 3))
    per_symbol_block = int(cost_cfg.get("per_symbol_trade_count_block", 5))

    for symbol in universe:
        # GUARD 0.5: per-symbol burn rate. After N filled trades on this
        # symbol today, block. Catches the 30+ MES round-trips pattern.
        sym_count = _today_trade_count_for_symbol(symbol)
        if sym_count >= per_symbol_block:
            print(f"  {symbol:5s}  SKIP — {sym_count} trades on this symbol "
                  f"today ≥ block threshold {per_symbol_block}. Fee-sink protection.")
            db.record_risk_event(
                severity="block", rule="per_symbol_burn_block",
                agent="auto_trader",
                detail={"symbol": symbol, "count": sym_count,
                        "block_threshold": per_symbol_block},
            )
            summary["skipped_per_symbol_burn"] = summary.get("skipped_per_symbol_burn", 0) + 1
            continue
        elif sym_count >= per_symbol_warn:
            # Dedupe: emit at most once per (symbol, count) per UTC day.
            # Without this, the warn fires on every scan (every ~5 min)
            # for the rest of the day after the threshold is crossed —
            # 2026-05-06 we saw 325 warn rows on MCL alone. Each NEW count
            # value (3→4→5) is still a fresh signal worth logging.
            today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
            already = db.connect().execute(
                "SELECT 1 FROM risk_events "
                "WHERE rule='per_symbol_burn_warn' AND ts LIKE ? "
                "  AND detail LIKE ? LIMIT 1",
                (f"{today_utc}%",
                 f'%"symbol": "{symbol}", "count": {sym_count}%'),
            ).fetchone()
            if not already:
                db.record_risk_event(
                    severity="warn", rule="per_symbol_burn_warn",
                    agent="auto_trader",
                    detail={"symbol": symbol, "count": sym_count,
                            "warn_threshold": per_symbol_warn},
                )

        # GUARD 1: already have a position on this symbol → skip
        existing = _broker_position_for(client, account_id, symbol)
        if existing is not None:
            print(f"  {symbol:5s}  SKIP — already {existing['side']} "
                  f"{existing['size']} @ {existing['avg_price']}")
            summary["skipped_already_in_trade"] += 1
            continue

        # GUARD 2: same-symbol thesis fired in the last `cooldown_minutes` min.
        # Configurable via --cooldown-minutes (default 45 = option 2).
        # Hard floor of 15 in live mode (set in main(), not here).
        if cooldown_minutes > 0 and _recent_thesis_in_db(symbol, minutes=cooldown_minutes):
            print(f"  {symbol:5s}  SKIP — recent thesis ({cooldown_minutes}-min cooldown)")
            summary["skipped_recent_thesis"] += 1
            continue

        # NOTE: The 5m-vs-15m "direction conflict" pre-scan was removed
        # 2026-05-01 because it was using the FIRST matching strategy from a
        # roster of 18 on each timeframe and skipping the whole symbol if
        # those two coin-flips disagreed. Different strategies on different
        # timeframes disagree by design (mean-reversion vs trend), so this
        # filter rejected ~60% of the focus universe on every scan with no
        # empirical justification. Audit on 2026-05-01: zero trades placed
        # since the safety floor went in (4-30 + 5-1) was driven primarily
        # by this gate. The gate cascade below (EV, RR, min_reward, min_stop,
        # fee, plus the hook-layer 23 checks) provides safety without this
        # blanket pre-filter.

        # Try multiple timeframes (5m primary, 15m secondary).
        # IMPORTANT: only ONE entry per symbol per scan (any timeframe).
        symbol_placed_this_scan = False
        for tf_minutes in (5, 15):
            if symbol_placed_this_scan:
                break
            bars = fetch_bars(client, symbol, minutes=tf_minutes, lookback=120)
            if bars is None or len(bars) < 30:
                continue
            summary["scanned"] += 1

            # Try every strategy, first trigger wins
            for strat_fn, params, conviction, label in STRATEGY_ROSTER:
                # NOTE: The DEFAULT-DENY validation gate runs AFTER signal
                # generation (~line 2120) so unvalidated strategies still
                # produce signals → those become shadow trades for ongoing
                # validation accumulation. See `STRATEGY_SYMBOL_ALLOWLIST`
                # comment block for the policy.
                pass
                # AUTO-DEMOTE: if this strategy already had 5 consecutive
                # losers today, skip it for the rest of the session.
                # Bellafiore "Playbook" rule, applied per-strategy not per-book.
                if _strategy_is_demoted(label):
                    continue
                streak, _ = _strategy_recent_streak(label, window_hours=4)
                if streak >= 5:
                    db.record_risk_event(
                        severity="warn", rule="strategy_demoted_today",
                        agent="auto_trader",
                        detail={"strategy": label, "streak": streak,
                                "reason": "5 consecutive losers in last 4h"},
                    )
                    print(f"  [{label}] DEMOTED for the rest of the day "
                          f"({streak} consecutive losers in 4h)")
                    continue
                # AUTONOMOUS conviction floor: skip "low" conviction strategies
                # under autonomous mode. Today's bleed was almost entirely
                # low-conviction setups (vwap_reversion, support_resistance_bounce).
                if autonomous and autonomous_rules.get("min_conviction"):
                    floor = str(autonomous_rules["min_conviction"]).lower()
                    rank = {"low": 0, "med": 1, "high": 2, "validation": 1}
                    if rank.get(conviction, 0) < rank.get(floor, 1):
                        continue

                # AUTONOMOUS per-strategy session shot cap: each strategy
                # gets N entries per session. Default 1. Stops the
                # "narrow_range_break fired 30 times" pattern from today.
                if autonomous and autonomous_per_strategy_used.get(label, 0) >= autonomous_per_strategy_cap:
                    continue

                signal = find_latest_signal(bars, strat_fn, **params)
                if signal is None:
                    continue
                if signal["stop"] is None:
                    continue  # need a stop to trade

                # DEFAULT-DENY VALIDATION GATE (2026-05-05).
                # Source of truth: state/strategy_validation.json (rebuilt
                # daily by scripts/daily_strategy_validation.py). If the
                # state file is present, it overrides the static
                # STRATEGY_SYMBOL_ALLOWLIST / STRATEGY_CELL_ALLOWLIST in
                # this file. Falls back to static lists on first run.
                _dyn = _get_dynamic_allowlists()
                if _dyn is not None:
                    sym_allow_active, cell_allow_active = _dyn
                else:
                    sym_allow_active = STRATEGY_SYMBOL_ALLOWLIST
                    cell_allow_active = STRATEGY_CELL_ALLOWLIST

                allowed_for = sym_allow_active.get(label)
                symbol_ok = allowed_for is not None and symbol in allowed_for

                # Cell check uses the active source too
                _cells_for_label = cell_allow_active.get(label)
                if _cells_for_label is None:
                    cell_ok = True  # no restriction
                else:
                    from datetime import datetime as _dt
                    from zoneinfo import ZoneInfo as _Z
                    _now_et = _dt.now(tz=_Z("America/New_York"))
                    _sess_now = _session_bucket_et(_now_et.hour + _now_et.minute / 60.0)
                    _side_signal = str(signal.get("side", "")).lower()
                    cell_ok = any(
                        c["symbol"] == symbol and c["session"] == _sess_now
                        and c["side"] == _side_signal
                        for c in _cells_for_label
                    )

                if not (symbol_ok and cell_ok):
                    reason = ("symbol_not_validated" if not symbol_ok
                              else "cell_not_validated")
                    _record_shadow_for_unvalidated(
                        db, label, symbol, signal, conviction, reason)
                    continue

                # CELL ALLOWLIST: strategies in STRATEGY_CELL_ALLOWLIST only
                # fire when (symbol, session, side) matches a validated cell.
                if not _signal_passes_cell_allowlist(label, symbol, signal):
                    continue

                # R:R floor: start from conviction floor (2.0 for med),
                # autonomous tightens via override (2.5), urgency relaxes
                # back toward conviction floor (0.2 per level, never below
                # the conviction floor itself).
                rr_floor = CONVICTION_RR_FLOOR.get(conviction, 2.0)
                if autonomous and autonomous_rules.get("rr_floor_override"):
                    autonomous_rr = float(autonomous_rules["rr_floor_override"])
                    rr_floor = max(rr_floor,
                                   autonomous_rr - urgency_level * 0.2)
                if signal["target"]:
                    risk = abs(signal["price"] - signal["stop"])
                    reward = abs(signal["target"] - signal["price"])
                    rr = reward / risk if risk > 0 else 0
                    if rr < rr_floor:
                        continue

                tick = _tick_size_for(symbol)

                # MIN STOP DISTANCE: sector-aware. Index futures need 8+
                # ticks because 5-tick MES = $6.25 loss eaten by 1-2 sec
                # of intraday noise. Rates need 10+ for similar reasons.
                # Energies/metals tolerate 5.
                min_stop_ticks = _min_stop_ticks_for(symbol, strategy=label)
                stop_dist_ticks = abs(signal["price"] - signal["stop"]) / tick
                # Tolerate floating-point noise: a 5.0-tick stop computed as
                # 4.9999... should not be rejected against a 5-tick floor.
                # Caught 2026-05-01: 6E narrow_range_break stop at 4.99 ticks
                # was being rejected against the energies-sector min of 5.
                FP_TOLERANCE = 1e-3
                if stop_dist_ticks < min_stop_ticks - FP_TOLERANCE:
                    print(f"  {symbol} [{tf_minutes}m] {label} | "
                          f"SKIP - stop too tight ({stop_dist_ticks:.2f} ticks "
                          f"< sector min {min_stop_ticks})")
                    summary["skipped_stop_too_tight"] = (
                        summary.get("skipped_stop_too_tight", 0) + 1)
                    continue

                # MIN ABSOLUTE REWARD: target reward must be ≥ $30 in USD,
                # regardless of R:R. Tiny-reward trades are noise.
                syms = _load_yaml("symbols.yaml").get("symbols", {})
                tick_value = float(syms.get(symbol, {}).get("tick_value", 1.0))
                if signal.get("target") and signal.get("price"):
                    reward_usd = (abs(signal["target"] - signal["price"])
                                  / tick * tick_value)
                    min_reward = _min_reward_usd_for(symbol)
                    if reward_usd < min_reward:
                        print(f"  {symbol} [{tf_minutes}m] {label} | "
                              f"SKIP - reward ${reward_usd:.2f} "
                              f"< symbol min ${min_reward}")
                        summary["skipped_reward_too_small"] = (
                            summary.get("skipped_reward_too_small", 0) + 1)
                        continue

                # FEE-AWARE FILTER: skip if reward < 3× round-trip fee
                fee_ok, fee_reason = _fee_decision_pass(symbol, signal, tick)
                if not fee_ok:
                    print(f"  {symbol} [{tf_minutes}m] {label} | "
                          f"FEE-SKIP: {fee_reason}")
                    summary["skipped_fee_unfavorable"] = summary.get("skipped_fee_unfavorable", 0) + 1
                    continue

                # HIT-RATE-AWARE EV GATE: compute expected NET dollar profit
                # using observed hit rate (Bayesian-blended). If expected_net
                # < threshold, skip — no strategy fires unless its math is
                # positive in expectation. The 2026-04-29 incident bled
                # because individually-negative-EV trades fired at high
                # frequency. This catches that at the trigger level.
                if signal.get("target") and signal.get("price") and signal.get("stop"):
                    hit_rate, n_obs, hr_conf = _strategy_hit_rate(label)
                    risk_usd = (abs(signal["price"] - signal["stop"]) / tick) * tick_value
                    reward_usd = (abs(signal["target"] - signal["price"]) / tick) * tick_value
                    fee = _round_trip_fee_usd(symbol)
                    expected_net = (hit_rate * reward_usd
                                    - (1 - hit_rate) * risk_usd
                                    - fee)
                    min_expected_net = 5.0   # standard $5 NET per trade floor
                    if autonomous:
                        # Autonomous tightens to $10; urgency relaxes by $2
                        # per level, never below the standard $5 floor.
                        min_expected_net = max(5.0,
                                               10.0 - urgency_level * 2.0)
                    if expected_net < min_expected_net:
                        print(f"  {symbol} [{tf_minutes}m] {label} | "
                              f"EV-SKIP: expected_net ${expected_net:.2f} < "
                              f"${min_expected_net:.2f} (hit={hit_rate:.0%} "
                              f"n={n_obs} {hr_conf} reward=${reward_usd:.0f} "
                              f"risk=${risk_usd:.0f} fee=${fee:.2f})")
                        summary["skipped_negative_ev"] = (
                            summary.get("skipped_negative_ev", 0) + 1)
                        continue

                # Build order proposal
                order = {
                    "symbol": symbol, "side": "buy" if signal["side"] == "long" else "sell",
                    "qty": 1, "order_type": "market",
                    "stop_price": signal["stop"],
                    "strategy": label,
                    "conviction": conviction,
                    "horizon": "intraday",
                    "tf": f"{tf_minutes}m",
                }

                # Apply risk gate
                verdict = apply_risk_gate(order)
                summary["triggers"] += 1

                if verdict:
                    summary["blocked"] += 1
                    db.record_risk_event(
                        severity="block", rule=verdict["rule"],
                        agent="auto_trader",
                        detail={"symbol": symbol, "strategy": label,
                                "reason": verdict["reason"][:200]},
                    )
                    print(f"  {symbol} [{tf_minutes}m] {label} | "
                          f"BLOCKED by {verdict['rule']}: {verdict['reason'][:80]}")
                    break  # next symbol; don't try more strategies on this one

                # Cleared the gate -- record the thesis and place. Dry-run
                # skips the thesis write so it doesn't pollute the live
                # cooldown via _recent_thesis_in_db (caught 2026-05-01: a
                # dry-run diagnostic locked NG out of live trading for 45
                # min the same session).
                if not dry_run:
                    db.record_decision(
                        agent="auto_trader", kind="thesis", symbol=symbol,
                        summary=f"{label} {signal['side']} @ {signal['price']:.4f} "
                                f"stop={signal['stop']:.4f} target={signal['target']}",
                        rationale=(f"strategy={label} side={signal['side']} "
                                   f"entry={signal['price']} stop={signal['stop']} "
                                   f"target={signal['target']} conviction={conviction} "
                                   f"tf={tf_minutes}m rr_planned="
                                   f"{abs((signal['target'] or signal['price']) - signal['price'])/max(abs(signal['price']-signal['stop']),0.0001):.2f} "
                                   f"horizon=intraday reason={signal['reason']}"),
                        model="auto_trader",
                    )

                if dry_run:
                    print(f"  {symbol} [{tf_minutes}m] {label} | "
                          f"DRY RUN: would place {order['side']} qty=1 "
                          f"stop={signal['stop']}")
                    symbol_placed_this_scan = True
                    autonomous_per_strategy_used[label] = autonomous_per_strategy_used.get(label, 0) + 1
                else:
                    try:
                        result = place_bracket(client, symbol, signal, qty=1)
                        if result.get("status") == "submitted":
                            summary["placed"] += 1
                            symbol_placed_this_scan = True
                            autonomous_per_strategy_used[label] = autonomous_per_strategy_used.get(label, 0) + 1
                            print(f"  {symbol} [{tf_minutes}m] {label} | "
                                  f"PLACED {order['side']} qty=1 "
                                  f"broker_oid={result.get('broker_order_id')} "
                                  f"cid={result.get('client_order_id')}")
                        else:
                            summary["errors"] += 1
                            print(f"  {symbol} [{tf_minutes}m] {label} | "
                                  f"PLACE FAILED: {result.get('error')}")
                    except Exception as e:
                        summary["errors"] += 1
                        print(f"  {symbol} [{tf_minutes}m] {label} | "
                              f"PLACE EXCEPTION: {type(e).__name__}: {e}")
                        traceback.print_exc()
                break  # exit strategy loop after one trigger

    return summary


def _acquire_instance_lock(dry_run: bool) -> Path | None:
    """File-based lock to prevent concurrent auto_trader instances.

    Two parallel scans on the same broker account compound damage: each one
    independently passes its own cooldown check (different in-memory state)
    but together they fire 2x the orders. 2026-04-29 incident analysis
    couldn't rule this out.

    Lock file is left in place if the process crashes; we check whether the
    PID inside it is still alive and steal the lock if not.
    Dry runs are exempt — multiple dry runs in parallel are fine.
    """
    if dry_run:
        return None
    lock_path = Path("logs/auto_trader.pid")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    if lock_path.exists():
        try:
            existing = int(lock_path.read_text().strip())
        except Exception:
            existing = 0
        if existing > 0:
            try:
                # Cheap is-alive check: os.kill(pid, 0) raises if dead.
                # On Windows this works for processes we own.
                os.kill(existing, 0)
                print(f"REFUSING to start: another auto_trader is already "
                      f"running (PID {existing}). Either stop it first or "
                      f"delete {lock_path} if you're sure it's dead.",
                      file=sys.stderr)
                return None
            except (OSError, ProcessLookupError):
                # PID dead — steal the lock
                print(f"  [lock] previous instance PID {existing} is gone; "
                      f"taking over the lock.", file=sys.stderr)
    lock_path.write_text(str(os.getpid()))
    return lock_path


def _release_instance_lock(lock_path: Path | None) -> None:
    if lock_path is None:
        return
    try:
        # Only delete if we still own it
        if lock_path.exists() and int(lock_path.read_text().strip()) == os.getpid():
            lock_path.unlink()
    except Exception:
        pass


def main_loop(*, interval_minutes: int = 15, dry_run: bool = False,
              cooldown_minutes: int = 45) -> None:
    """Run scans on a loop until interrupted."""
    print(f"=== auto_trader: {interval_minutes}-minute cadence, "
          f"{cooldown_minutes}-min same-symbol cooldown, "
          f"{'DRY RUN' if dry_run else 'LIVE'} ===")
    while True:
        try:
            result = scan_once(dry_run=dry_run, cooldown_minutes=cooldown_minutes)
            print(f"  summary: {result}\n")
        except KeyboardInterrupt:
            print("\n=== interrupted, exiting ===")
            return
        except Exception as e:
            print(f"  scan_once raised: {type(e).__name__}: {e}")
            traceback.print_exc()
        time.sleep(interval_minutes * 60)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--once", action="store_true",
                   help="single scan and exit (debug)")
    p.add_argument("--dry-run", action="store_true",
                   help="find + log triggers but don't place orders")
    p.add_argument("--interval-minutes", type=int, default=15,
                   help="minutes between scans. Default 15 (slow + fee-aware). "
                        "Use 5 for aggressive, 30 for very conservative.")
    p.add_argument("--cooldown-minutes", type=int, default=45,
                   help="same-symbol thesis cooldown. Default 45 min. "
                        "Hard floor of 15 in live mode; 0 only allowed in "
                        "dry-run. Setting 0 in live mode caused the "
                        "2026-04-29 DLL breach (24 theses in one minute "
                        "during overnight thin tape).")
    args = p.parse_args()

    mode = os.environ.get("FUND_MODE", "paper").split("#", 1)[0].strip().lower()
    if mode != "live" and not args.dry_run:
        print(f"FUND_MODE={mode!r} — refusing to place real orders. "
              f"Either set FUND_MODE=live in .env or use --dry-run.",
              file=sys.stderr)
        return 2

    # Hard floor on cooldown in live mode. Past incident: --cooldown-minutes 0
    # in fund.ps1:start-debug allowed dozens of theses per minute, compounding
    # the 2026-04-29 loss. Dry-run can still go to 0 for debugging.
    MIN_LIVE_COOLDOWN = 15
    if not args.dry_run and args.cooldown_minutes < MIN_LIVE_COOLDOWN:
        print(f"--cooldown-minutes {args.cooldown_minutes} clamped to "
              f"{MIN_LIVE_COOLDOWN} (live-mode floor). Use --dry-run if "
              f"you need a tighter loop for testing.", file=sys.stderr)
        args.cooldown_minutes = MIN_LIVE_COOLDOWN

    lock = _acquire_instance_lock(args.dry_run)
    if lock is None and not args.dry_run:
        return 3   # another instance is running
    try:
        if args.once:
            result = scan_once(dry_run=args.dry_run,
                               cooldown_minutes=args.cooldown_minutes)
            print(f"\nfinal summary: {result}")
            return 0

        main_loop(interval_minutes=args.interval_minutes,
                  dry_run=args.dry_run,
                  cooldown_minutes=args.cooldown_minutes)
        return 0
    finally:
        _release_instance_lock(lock)


if __name__ == "__main__":
    raise SystemExit(main())
