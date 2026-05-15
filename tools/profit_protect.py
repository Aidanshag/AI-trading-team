"""Trailing-profit-lock + gain/loss hard-cap protection for open positions.

Extracted as a tool module (2026-05-11 evening) per the "trim the knife"
directive — the trader (`scripts/live_trader.py`) keeps only the call site;
all tier logic / high-water tracking / P&L math lives here.

WHY IT EXISTS:
Live execution today operates with `SKIP_TARGET_LEG=True` (workaround for
broker target-fill anomaly — see
vault/research/analysis/2026-05-11_broker_target_fill_anomaly.md). Without
target legs at the broker, profits can run unbounded UNTIL stop fires OR
something software-side closes the position. This module is that
something. The rule "never let a gain become a loss" is user-stated.

TIER SEMANTICS:
Each tier is `(peak_threshold_usd, floor_usd)`. Once a position's PEAK
unrealized P&L crosses `peak_threshold`, the floor is engaged: if current
unrealized DROPS to or below `floor`, market-close the position
immediately. Tiers are checked highest-first so the tightest active tier
wins.

  Default tiers (mirrored from `scripts/auto_trader.py` 2026-05-08):
    (400, 200)   # at +$400 peak, lock in +$200 minimum
    (250, 100)   # at +$250 peak, lock in +$100 minimum
    (150,  50)
    ( 80,  20)
    ( 30,   0)   # at +$30 peak, never let it become a loss

GAIN-SIDE HARD CAP (`GAIN_TIER_HARD_CAP_USD`):
Unconditional market-close when unrealized exceeds this. Stops a runaway
winner from reversing on overnight news/gaps. Default $400 (matches the
top trailing tier's threshold — at +$400 we'd rather take it now).

USAGE (from live_trader.py):
    from tools.profit_protect import check_and_close
    closed = check_and_close(client, account_id, log_fn=_log)
"""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Callable

# ── Configuration ──────────────────────────────────────────────

TRAILING_PROFIT_TIERS: tuple[tuple[float, float], ...] = (
    # (peak_threshold_usd, floor_usd) — order doesn't matter, decide()
    # picks the highest-active floor. Trades stack: as peak grows, tighter
    # higher-floor tiers progressively replace looser low-floor tiers.
    #
    # 2026-05-13 update: removed the (30, 0) tier — it was dominated by
    # (25, 12) so it never actually fired (at peak >=30, both tiers are
    # crossed and decide() picks max floor = 12). The "(30, 0) reverts
    # break-even" semantic was illusory after the 5/12 micro-tier add.
    # Also added graduated intermediate tiers between $25 and $80 peak
    # so a mid-size winner doesn't ride the (25, 12) floor for too long.
    #
    # --- micro tiers (lock small wins, don't clip runners)
    ( 15.0,     5.0),    # peak $15 → lock $5
    ( 25.0,    12.0),    # peak $25 → lock $12
    # --- mid-small tiers (added 2026-05-13 — bridge $25-$80 zone)
    ( 40.0,    18.0),    # peak $40 → lock $18 (45% lock)
    ( 55.0,    25.0),    # peak $55 → lock $25 (45% lock)
    ( 70.0,    32.0),    # peak $70 → lock $32 (46% lock)
    # --- mid tiers
    ( 80.0,    40.0),    # peak $80 → lock $40 (50% lock; was 20, raised
                          #   2026-05-13 to fit the graduated progression)
    (150.0,    50.0),
    (250.0,   100.0),
    (400.0,   200.0),
    # --- runner zone (allow big winners to breathe; tier added 2026-05-11
    # after the +$2,616 GC trade revealed the prior cap was clipping runners)
    (750.0,   400.0),
    (1500.0,  900.0),
    (2500.0, 1500.0),
    (5000.0, 3000.0),
    (10000.0, 6500.0),
)

# 2026-05-11: hard cap REMOVED (set to None) per user direction. The old
# $400 cap would have force-closed today's GC trade at $400 instead of
# letting it run to +$2,616. With expanded runner-zone tiers above,
# trailing-lock is sufficient protection without a fixed ceiling.
GAIN_TIER_HARD_CAP_USD: float | None = None
LOSS_TIER_HARD_CAP_USD: float = 150.0   # belt-and-suspenders for broker stop

# Per-position high-water mark (process-local; resets on trader restart).
# Key: "SYMBOL_SIDE". Value: peak unrealized $ seen this session.
_position_high_water: dict[str, float] = {}

# Per-position agent-veto state (process-local).
# `_position_consecutive_holds`: how many times the agent has held this position
# in a row. Resets on close or on a CLOSE decision.
# `_position_entry_ts_seen`: first time we saw this position in this process.
# Used as a proxy for entry_ts (we don't have the real fill time without an
# extra DB lookup). Resets on close.
_position_consecutive_holds: dict[str, int] = {}
_position_entry_ts_seen: dict[str, datetime] = {}


# ── Symbol parsing helpers ────────────────────────────────────

def _contract_to_symbol(contract_id: str) -> str | None:
    """Pick the symbol token out of a ProjectX contract id like
    'CON.F.US.GCE.M26'. Skip prefixes and month codes."""
    for tok in contract_id.split("."):
        if tok in ("CON", "F", "US", ""):
            continue
        if len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit():
            continue  # month code like 'M26'
        return tok
    return None


def _strip_exchange_suffix(sym: str) -> str:
    """Normalize 'GCE' → 'GC', 'NGE' → 'NG', etc. ProjectX uses 'E' suffix
    for some products."""
    if len(sym) > 2 and sym.endswith("E") and sym[:-1] in ("GC", "NG", "CL", "SI"):
        return sym[:-1]
    return sym


# ── Tick economics (kept lightweight; mirrors live_trader fallback) ─

def _resolve_tick_economics(symbol: str) -> tuple[float, float]:
    """Resolve (tick_size, tick_value) for a symbol with two layers:
      1. Hardcoded _TICK_ECONOMICS dict (fast path; explicitly curated).
      2. Fallback to config/symbols.yaml (canonical source — covers any
         symbol the brain might emit signals for).
    Returns (0.0, 0.0) only when BOTH layers fail."""
    ts, tv = _TICK_ECONOMICS.get(symbol, (0.0, 0.0))
    if ts > 0 and tv > 0:
        return ts, tv
    # Fallback: read from config/symbols.yaml
    try:
        from tools.trader_utils import _load_yaml
        syms = _load_yaml("config/symbols.yaml").get("symbols", {}) or {}
        meta = syms.get(symbol) or {}
        ts = float(meta.get("tick_size") or 0)
        tv = float(meta.get("tick_value") or 0)
        return ts, tv
    except Exception:
        return 0.0, 0.0


# 2026-05-15: Topstep contract-ID alias addition (Pattern A n=4 fix).
# Brain emits strategy signals using the canonical CME root (e.g. "6E");
# Topstep's contract IDs use platform-specific root tokens (e.g. "EU6").
# `_contract_to_symbol("CON.F.US.EU6.M26")` returns "EU6", which previously
# missed every entry in this table → profit-lock + loss-cap silently
# disabled (Pattern A: fail-silent default). The 2026-05-14 EU6 short held
# 2h14m completely unprotected as a result. Empirically-confirmed
# alias mapping is mirrored from `hooks/risk_gate._normalize_root`
# (which is verified live against the broker). When in doubt about an
# alias, consult that map first.
_TICK_ECONOMICS: dict[str, tuple[float, float]] = {
    # Rates
    "ZN": (0.015625, 15.625), "ZB": (0.03125, 31.25),
    "ZT": (0.0078125, 15.625), "ZF": (0.0078125, 7.8125),
    "UB": (0.03125, 31.25),
    # Rates — Topstep aliases (TYA=ZN, FVA=ZF; verified hooks/risk_gate)
    "TYA": (0.015625, 15.625), "FVA": (0.0078125, 7.8125),
    # Energies
    "NG": (0.001, 10.0), "MNG": (0.005, 1.25), "QG": (0.005, 12.50),
    "CL": (0.01, 10.0), "MCL": (0.01, 1.0),
    "RB": (0.0001, 4.20), "HO": (0.0001, 4.20),
    # Energies — Topstep aliases (already handled by _strip_exchange_suffix
    # for 2-char roots GCE/NGE/CLE/SIE; MCLE/MNGE/HOE/RBE pass through
    # unstripped and need explicit aliases). Verified hooks/risk_gate.
    "MCLE": (0.01, 1.0), "MNGE": (0.005, 1.25),
    "HOE": (0.0001, 4.20), "RBE": (0.0001, 4.20),
    # Metals — 2026-05-14 fix: MGC was missing, broke profit-lock for the
    # MGC short opened 2026-05-14 01:05 UTC.
    "GC": (0.10, 10.0), "MGC": (0.10, 1.0),
    "SI": (0.005, 25.0), "SIL": (0.005, 5.0),
    "HG": (0.0005, 12.5), "MHG": (0.0005, 1.25),
    "PL": (0.10, 5.0),
    # Equity index
    "ES": (0.25, 12.50), "MES": (0.25, 1.25),
    "NQ": (0.25, 5.00), "MNQ": (0.25, 0.50),
    "RTY": (0.10, 5.00), "M2K": (0.10, 0.50),
    "YM": (1.00, 5.00),  "MYM": (0.50, 0.50),
    "NKD": (5.00, 25.00),
    # Equity index — Topstep aliases (EP=ES, ENQ=NQ; verified hooks/risk_gate)
    "EP": (0.25, 12.50), "ENQ": (0.25, 5.00),
    # FX futures — Topstep contract IDs use EU6/BP6/etc instead of 6E/6B.
    # 2026-05-15: aliases added after EU6 short held 2h14m unprotected
    # (Pattern A n=4). Both forms point at the same tuple. Tick values
    # mirror config/symbols.yaml — note 6A/6C are $5/tick at the micro
    # FX (config/symbols.yaml) but the established figure here is $10;
    # leaving the existing $10 in place to preserve current behavior and
    # flagging the discrepancy as a separate audit item in the backlog.
    "6E": (0.00005, 6.25),  "EU6": (0.00005, 6.25),
    "6B": (0.0001, 6.25),   "BP6": (0.0001, 6.25),
    "6J": (0.0000005, 6.25), "JY6": (0.0000005, 6.25),
    "6A": (0.0001, 10.00),  "DA6": (0.0001, 10.00),
    "6C": (0.0001, 10.00),  "CA6": (0.0001, 10.00),
    "6M": (0.00001, 5.00),  "MX6": (0.00001, 5.00),
    "E7": (0.0001, 6.25),   "EEU": (0.0001, 6.25),
    # Grains / livestock (sector: ag)
    "ZC": (0.0025, 12.50), "ZS": (0.0025, 12.50),
    "ZW": (0.0025, 12.50), "ZL": (0.0001, 6.00), "ZM": (0.10, 10.0),
    "LE": (0.025, 10.0), "HE": (0.025, 10.0),
    # Grains/livestock — Topstep aliases (ZCE=ZC, GLE=LE; verified hooks/risk_gate)
    "ZCE": (0.0025, 12.50), "GLE": (0.025, 10.0),
    # Metals — Topstep alias (CPE=HG; verified hooks/risk_gate)
    "CPE": (0.0005, 12.5),
    # Other Topstep contract roots seen live (NQG=QG, NQM=QM, GMET=METK)
    "NQG": (0.005, 12.50), "NQM": (0.025, 12.50),
}


# ── Decision logic (pure) ─────────────────────────────────────

def decide(unrealized: float, prev_peak: float,
            tiers: tuple[tuple[float, float], ...] = TRAILING_PROFIT_TIERS,
            gain_cap: float | None = GAIN_TIER_HARD_CAP_USD,
            loss_cap: float = LOSS_TIER_HARD_CAP_USD,
            ) -> tuple[bool, str]:
    """Pure decision function — returns (should_close, reason).
    No broker IO; easy to unit-test.

    Closure rules (checked in order):
      1. Loss hard cap: unrealized <= -loss_cap → close (backstop)
      2. Gain hard cap: unrealized >= gain_cap → close (if cap is not None)
      3. Trailing tiers: among tiers whose peak_threshold the position
         has crossed, the TIGHTEST floor (highest floor) wins. Close iff
         current unrealized < that floor.
    """
    if gain_cap is not None and unrealized >= gain_cap:
        return True, f"hard_cap: unrealized ${unrealized:.2f} >= ${gain_cap:.0f}"
    if unrealized <= -loss_cap:
        return True, (f"loss_hard_cap: unrealized ${unrealized:.2f} "
                       f"<= -${loss_cap:.0f} (broker stop backstop)")
    # Among crossed tiers, pick the one with the highest floor (tightest
    # protection wins).
    active_floor: float | None = None
    active_peak: float | None = None
    for peak_threshold, floor in tiers:
        if prev_peak >= peak_threshold:
            if active_floor is None or floor > active_floor:
                active_floor = floor
                active_peak = peak_threshold
    if active_floor is not None and unrealized < active_floor:
        return True, (f"trailing_lock: peak ${prev_peak:.2f} crossed "
                       f"${active_peak:.0f}, current ${unrealized:.2f} "
                       f"fell below floor ${active_floor:.0f}")
    return False, ""


def _compute_active_floor(prev_peak: float,
                            tiers: tuple[tuple[float, float], ...] = TRAILING_PROFIT_TIERS,
                            ) -> float | None:
    """Return the tightest active floor given prev_peak (= highest floor
    among tiers whose peak_threshold has been crossed). Returns None if
    no tier crossed. Pure function — mirrors the inner logic of decide()."""
    active: float | None = None
    for peak_threshold, floor in tiers:
        if prev_peak >= peak_threshold:
            if active is None or floor > active:
                active = floor
    return active


# Per-position software take-profit target (in USD unrealized).
# 2026-05-14: strategies emit a target_price on every signal, but we
# don't place a broker target leg (5/11 anomaly: target limits auto-fill
# at market). Instead, bracket_placement registers the target value in
# USD here. check_and_close polls every 2-10s and force-closes when
# unrealized >= target_usd. Captures wins at the strategy's own
# prediction instead of waiting for the trailing-lock retrace.
_target_usd_by_contract: dict[str, float] = {}


def register_software_target(contract_id: str, target_usd: float) -> None:
    """Set the software take-profit target (USD unrealized) for a position.
    Called by tools.bracket_placement.place_bracket after entry fills.
    Zero or negative values are ignored."""
    if target_usd > 0:
        _target_usd_by_contract[contract_id] = float(target_usd)


def _clear_software_target(contract_id: str) -> None:
    _target_usd_by_contract.pop(contract_id, None)


# Track which contract → which floor we've already trailed to.
# Prevents repeated cancel+replace cycles on every poll for the same
# floor (the broker's working-orders endpoint can lag a few seconds
# between cancel and the next get_working_orders call).
_trailed_floor_by_contract: dict[str, float] = {}


def _trail_broker_stop_to_floor(client, account_id, position: dict,
                                  active_floor_usd: float,
                                  tick_size: float, tick_value: float,
                                  log: Callable[[str], None]) -> None:
    """Move the broker-side protective stop UP (closer to entry) to lock
    in `active_floor_usd` of profit. Never moves it the other direction.

    2026-05-14 rewrite: uses CANCEL + REPLACE instead of modify_order.
    Earlier modify_order calls were silently ineffective — the broker
    returned success but the stopPrice on the working order never
    changed. Cancel-and-replace forces a fresh order that the broker
    actually books. Verified by re-reading working orders after place.

    Process-local memoization (`_trailed_floor_by_contract`) prevents
    re-trailing the same contract to the same floor every poll —
    important because the broker's working orders endpoint can lag a
    few seconds between cancel and re-list.
    """
    contract_id = position.get("contractId")
    avg_price = float(position.get("averagePrice") or 0)
    if not contract_id or avg_price <= 0 or tick_size <= 0 or tick_value <= 0:
        return
    type_code = int(position.get("type") or 0)
    is_long = type_code == 1

    size = abs(int(position.get("size") or 1)) or 1
    dollars_per_point = (tick_value / tick_size) * size
    if dollars_per_point <= 0:
        return
    floor_points = active_floor_usd / dollars_per_point
    if is_long:
        desired_stop = avg_price + floor_points
    else:
        desired_stop = avg_price - floor_points
    desired_stop = round(desired_stop / tick_size) * tick_size

    # Skip if we've already trailed this contract to this floor (or tighter)
    last_trailed = _trailed_floor_by_contract.get(contract_id, -1.0)
    if last_trailed >= active_floor_usd:
        return

    # Find current working stop for this contract
    try:
        working = client.get_working_orders(account_id) or []
    except Exception as e:
        log(f"  trailing_stop: get_working_orders failed: {e}")
        return
    stop_orders = [o for o in working
                    if o.get("contractId") == contract_id
                    and str(o.get("customTag", "")).endswith("_stop")]
    if not stop_orders:
        log(f"  trailing_stop: no working stop found for {contract_id} "
             f"(position unprotected at broker — relying on software cap)")
        return
    stop_order = stop_orders[0]
    current_stop = float(stop_order.get("stopPrice") or 0)
    if current_stop <= 0:
        return

    # Only trail if the new stop is TIGHTER (closer to entry/lock in profit).
    if is_long and desired_stop <= current_stop:
        _trailed_floor_by_contract[contract_id] = active_floor_usd
        return
    if (not is_long) and desired_stop >= current_stop:
        _trailed_floor_by_contract[contract_id] = active_floor_usd
        return

    new_limit = (desired_stop - tick_size) if is_long else (desired_stop + tick_size)
    new_limit = round(new_limit / tick_size) * tick_size
    old_stop_oid = stop_order.get("id") or stop_order.get("orderId")
    old_stop_cid = str(stop_order.get("customTag") or "")
    if not old_stop_oid:
        return

    # === CANCEL + REPLACE pattern ===
    # 1. Cancel the old stop
    try:
        client.cancel_order(account_id, old_stop_oid)
    except Exception as e:
        log(f"  trailing_stop: cancel old stop {old_stop_oid} failed: {e}")
        return

    # 2. Place a new stop at the desired price (same side, same qty,
    #    new prices). Use a customTag suffix that STILL ENDS IN "_stop"
    #    so other code (cleanup_orphan_brackets, future trailing) recognizes it.
    # 2026-05-14 fix: previous formula appended "_trail{4hex}" AFTER "_stop"
    # which broke the endswith("_stop") filter — the next trail poll
    # couldn't find the replacement stop, thought position was unprotected.
    import uuid as _uuid
    base = old_stop_cid.rsplit("_stop", 1)[0]
    new_cid = f"{base}_t{_uuid.uuid4().hex[:6]}_stop"
    opp_side = "sell" if is_long else "buy"
    try:
        sr = client.place_order(
            account_id=account_id, contract_id=contract_id,
            side=opp_side, qty=int(size), order_type="stop_limit",
            limit_price=new_limit, stop_price=desired_stop,
            time_in_force="gtc", client_order_id=new_cid,
        )
        # Verify the broker actually accepted by checking response shape
        if isinstance(sr, dict) and sr.get("success") is False:
            err = sr.get("errorMessage") or "broker rejected"
            log(f"  CRITICAL trailing_stop: replace REJECTED for "
                 f"{contract_id} — {err}; position unprotected at broker")
            try:
                from tools.alert import send_alert as _alert
                _alert(
                    f"CRITICAL: trailing-stop replace REJECTED on {contract_id}. "
                    f"Old stop cancelled, new stop NOT placed. Broker reason: "
                    f"{err}. Position now ONLY protected by software cap.",
                    level="crit",
                )
            except Exception:
                pass
            return
        log(f"  TRAILING_STOP: {contract_id} cancel+replace "
             f"{current_stop} -> {desired_stop} (locks +${active_floor_usd:.0f})")
        _trailed_floor_by_contract[contract_id] = active_floor_usd
    except Exception as e:
        log(f"  CRITICAL trailing_stop: replace FAILED for {contract_id}: "
             f"{type(e).__name__}: {e}; position unprotected at broker")
        try:
            from tools.alert import send_alert as _alert
            _alert(
                f"CRITICAL: trailing-stop replace FAILED on {contract_id}. "
                f"Old stop cancelled, new stop placement raised: "
                f"{type(e).__name__}: {e}. Position now ONLY protected by software cap.",
                level="crit",
            )
        except Exception:
            pass


def reset_trailed_floor(contract_id: str) -> None:
    """Reset the process-local trail memo for a contract. Called when a
    position closes (by the same module) so the next entry starts fresh."""
    _trailed_floor_by_contract.pop(contract_id, None)


def _unrealized_usd(side: str, size: int, avg_price: float,
                     last_price: float, tick_size: float,
                     tick_value: float) -> float:
    if tick_size <= 0 or tick_value <= 0:
        # Pattern A defense: missing tick economics MUST NOT silently return 0
        # (would blind profit-lock to a real bleeding position). Raise so the
        # outer check_and_close logs the error and skips the position.
        raise ValueError(f"missing tick economics: tick_size={tick_size} "
                          f"tick_value={tick_value}")
    move = (last_price - avg_price) if side == "long" else (avg_price - last_price)
    ticks = move / tick_size
    return ticks * tick_value * abs(size)


# ── Agent-veto helpers ────────────────────────────────────────

_EXIT_REASONER_CONFIG_PATH = "config/exit_reasoner.yaml"


def _load_exit_reasoner_config() -> dict:
    """Return the feature-flag config. Disabled-everything on any error."""
    try:
        import yaml
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / _EXIT_REASONER_CONFIG_PATH
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception:
        return {"enabled": False}


def _is_agent_enabled_for_cell(symbol: str, side: str,
                                 strategy: str | None) -> bool:
    """True iff this (strategy, symbol, side) is routed through the agent."""
    cfg = _load_exit_reasoner_config()
    if not cfg.get("enabled"):
        return False
    cell_key = f"{strategy or '*'}/{symbol}/{side}"
    denied = cfg.get("denied_cells") or []
    for d in denied:
        if d == cell_key or d == "*":
            return False
    enabled_cells = cfg.get("enabled_cells") or []
    if "*" in enabled_cells:
        return True
    for c in enabled_cells:
        if c == cell_key:
            return True
        # Allow "*/SYMBOL/side" wildcard
        if "*" in c and _wildcard_match(c, cell_key):
            return True
    return False


def _wildcard_match(pattern: str, key: str) -> bool:
    """Simple wildcard match — '*' matches a whole segment."""
    p_parts = pattern.split("/")
    k_parts = key.split("/")
    if len(p_parts) != len(k_parts):
        return False
    return all(p == "*" or p == k for p, k in zip(p_parts, k_parts))


def _parse_trailing_lock_floor(reason: str) -> float | None:
    """Extract the `floor $X` value from decide()'s reason string. Returns
    None if not a trailing_lock reason or parse fails."""
    if "trailing_lock" not in reason:
        return None
    import re
    m = re.search(r"floor \$(-?\d+(?:\.\d+)?)", reason)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _bars_df_to_dicts(bars_df) -> list[dict]:
    """Convert the pandas DataFrame returned by fetch_bars to a list of
    dicts suitable for the agent prompt. Last 20 bars, oldest first."""
    if bars_df is None or len(bars_df) == 0:
        return []
    out = []
    tail = bars_df.tail(20)
    for ts, row in tail.iterrows():
        try:
            ts_iso = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
            out.append({
                "t": ts_iso,
                "o": float(row.get("Open") or row.get("open") or 0),
                "h": float(row.get("High") or row.get("high") or 0),
                "l": float(row.get("Low") or row.get("low") or 0),
                "c": float(row.get("Close") or row.get("close") or 0),
            })
        except Exception:
            continue
    return out


def _open_db_connection():
    """Open a connection to fund.db for agent_exit_vetoes logging."""
    try:
        import sqlite3
        from pathlib import Path
        path = Path(__file__).resolve().parent.parent / "state" / "fund.db"
        return sqlite3.connect(str(path), timeout=5.0)
    except Exception:
        return None


def _record_close_decision(symbol: str, side: str, size: int, contract_id: str,
                            unrealized: float, peak: float, reason: str,
                            kind: str = "close") -> None:
    """Write a `decisions` row when profit-lock fires a close via
    `close_position`. Provides an audit trail equivalent to the orders-table
    row that `place_order` used to produce — the native `close_position`
    endpoint doesn't create an order row in the same way.

    Fail-safe: any DB error is swallowed (the close itself already
    succeeded at the broker; logging failure must not raise)."""
    try:
        from state.db import get_db
        summary = (f"{symbol} {side} {size}ct flattened via close_position "
                    f"@ unrealized=${unrealized:+.2f}")
        rationale = (f"reason={reason} | peak=${peak:+.2f} | "
                      f"contract_id={contract_id}")
        get_db().record_decision(
            agent="profit_lock",
            kind=kind,
            summary=summary,
            rationale=rationale,
            symbol=symbol,
        )
    except Exception:
        # Never block close flow on audit-log failure
        pass


# ── Main entrypoint ───────────────────────────────────────────

def check_and_close(client, account_id, log_fn: Callable[[str], None] | None = None,
                     fetch_bars_fn: Callable | None = None,
                     strategy_lookup_fn: Callable | None = None) -> list[dict]:
    """For each open position, check trailing-profit-lock + hard caps. If a
    rule triggers, market-close the position at the broker.

    `client` must implement: get_positions, place_order.
    `fetch_bars_fn` optional: callable(client, symbol, minutes, lookback)
    returning a DataFrame with 'Close' column. If omitted, uses
    tools/bar_fetcher.fetch_bars.

    Returns list of closure records: [{symbol, side, size, unrealized, reason}].
    """
    log = log_fn if log_fn is not None else (lambda _msg: None)
    closed: list[dict] = []
    try:
        positions = client.get_positions(account_id) or []
    except Exception as e:
        log(f"  profit_protect: get_positions failed: {type(e).__name__}: {e}")
        return closed

    for p in positions:
        try:
            size = int(p.get("size") or 0)
            if size == 0:
                continue
            contract_id = str(p.get("contractId") or "")
            if not contract_id:
                continue
            avg_price = float(p.get("averagePrice") or 0)
            if avg_price <= 0:
                continue
            type_code = int(p.get("type") or 0)
            side = "long" if type_code == 1 else "short" if type_code == 2 else (
                "long" if size > 0 else "short")
            size = abs(size)
            raw_sym = _contract_to_symbol(contract_id) or ""
            symbol = _strip_exchange_suffix(raw_sym)
            if not symbol:
                continue
            tick_size, tick_value = _resolve_tick_economics(symbol)
            if tick_size <= 0 or tick_value <= 0:
                # CRITICAL: position is OPEN but we cannot compute unrealized.
                # Profit-lock + loss-cap are blind to this position. Fire a
                # Discord alert so the user knows immediately. This is the
                # exact failure shape that lost coverage of the MGC short
                # on 2026-05-14 — _TICK_ECONOMICS was missing MGC and the
                # silent skip meant only the broker stop protected it.
                log(f"  CRITICAL: no tick economics for {symbol} ({contract_id}); "
                     f"profit-lock + loss-cap BLIND to this position")
                try:
                    from tools.alert import send_alert as _alert
                    _alert(
                        f"CRITICAL: open position on {symbol} but no tick "
                        f"economics resolved. Profit-lock + loss-cap CANNOT "
                        f"fire. Only broker stop protecting. Add {symbol} to "
                        f"config/symbols.yaml or tools/profit_protect."
                        f"_TICK_ECONOMICS.",
                        level="crit",
                    )
                except Exception:
                    pass
                continue

            # Latest mark via 1-min bars (cheap; usually cached)
            if fetch_bars_fn is None:
                from tools.bar_fetcher import fetch_bars as _fb
                bars = _fb(client, symbol, 1, 5)
            else:
                bars = fetch_bars_fn(client, symbol, 1, 5)
            if bars is None or len(bars) == 0:
                continue
            last_close = float(bars["Close"].iloc[-1])

            unrealized = _unrealized_usd(side, size, avg_price, last_close,
                                          tick_size, tick_value)
            key = f"{symbol}_{side}"
            prev_peak = _position_high_water.get(key, 0.0)
            if unrealized > prev_peak:
                _position_high_water[key] = unrealized
                prev_peak = unrealized

            # ── SOFTWARE TAKE-PROFIT AT TARGET (2026-05-14) ──
            # Strategies emit a target_price on every signal. We don't
            # place a broker target leg due to the 5/11 auto-fill anomaly,
            # so honor it in software: when unrealized hits the target
            # value, close immediately via close_position (NOT
            # place_order market-IOC — that path is broken at the broker,
            # rejects with "limit price not set" because type=1 maps to
            # LIMIT not MARKET in Topstep's actual schema. 2026-05-14).
            target_usd = _target_usd_by_contract.get(contract_id)
            if target_usd is not None and unrealized >= target_usd:
                try:
                    result = client.close_position(account_id, contract_id)
                    if isinstance(result, dict) and result.get("success") is False:
                        err = result.get("errorMessage") or "broker rejected"
                        log(f"  target_hit close REJECTED for {contract_id}: {err}")
                        try:
                            from tools.alert import send_alert as _alert
                            _alert(
                                f"CRITICAL: target-hit close REJECTED for "
                                f"{symbol}: {err}. Position still OPEN.",
                                level="crit",
                            )
                        except Exception:
                            pass
                        continue
                    log(f"  TARGET_HIT: {symbol} {side} {size}ct "
                         f"unrealized=${unrealized:+.2f} target=${target_usd:.0f}")
                    try:
                        from tools.alert import send_alert as _alert
                        _alert(
                            f"🎯 TARGET_HIT {symbol} {side} {size}ct @ "
                            f"${unrealized:+.0f} (target ${target_usd:.0f})",
                            level="info",
                        )
                    except Exception:
                        pass
                    _position_high_water.pop(key, None)
                    _position_consecutive_holds.pop(key, None)
                    _position_entry_ts_seen.pop(key, None)
                    _clear_software_target(contract_id)
                    reset_trailed_floor(contract_id)
                    # Audit-trail row in decisions table (close_position
                    # doesn't produce an orders row the way place_order did).
                    _record_close_decision(
                        symbol=symbol, side=side, size=size,
                        contract_id=contract_id, unrealized=unrealized,
                        peak=prev_peak, reason="target_hit", kind="close",
                    )
                    closed.append({"symbol": symbol, "side": side,
                                    "size": size, "unrealized": unrealized,
                                    "peak": prev_peak, "reason": "target_hit"})
                    continue
                except Exception as e:
                    log(f"  target_hit close FAILED for {contract_id}: "
                         f"{type(e).__name__}: {e}")
                    # Fall through to trailing/loss-cap logic below

            should_close, reason = decide(unrealized, prev_peak)
            if not should_close:
                # Reset consecutive_holds when the rule no longer wants to close
                _position_consecutive_holds.pop(key, None)
                # 2026-05-14: trail the broker-side stop UP as peak grows.
                # The software profit-lock is bounded by polling latency
                # (peak $61 retraced past $25 floor → only caught at $12).
                # Putting the floor at the BROKER server-side means it
                # fires instantly on touch. _trail_broker_stop_to_floor
                # only ever TIGHTENS the stop (never loosens).
                active_floor = _compute_active_floor(prev_peak)
                if active_floor is not None and active_floor > 0:
                    _trail_broker_stop_to_floor(
                        client, account_id, p, active_floor,
                        tick_size, tick_value, log,
                    )
                continue

            # ── Agent veto layer (Phase 1b 2026-05-12) ──
            # ONLY trailing_lock reasons route through the agent. Loss caps,
            # gain caps, and any unknown reason remain mechanical.
            tier_floor = _parse_trailing_lock_floor(reason)
            strategy = None
            if strategy_lookup_fn is not None:
                try:
                    strategy = strategy_lookup_fn(symbol, side, contract_id)
                except Exception:
                    strategy = None

            if tier_floor is not None and _is_agent_enabled_for_cell(
                    symbol, side, strategy):
                # Mark / refresh entry-ts proxy
                if key not in _position_entry_ts_seen:
                    _position_entry_ts_seen[key] = datetime.now(tz=timezone.utc)

                cfg = _load_exit_reasoner_config()
                report_only = bool(cfg.get("report_only", True))

                try:
                    from tools.exit_reasoner import (
                        decide_exit_with_agent, TradeContext,
                    )
                    bar_dicts = _bars_df_to_dicts(bars)
                    ctx = TradeContext(
                        symbol=symbol, side=side, strategy=strategy,
                        contract_id=contract_id,
                        entry_price=avg_price,
                        entry_ts=_position_entry_ts_seen[key],
                        avg_fill_price=avg_price,
                        current_price=last_close,
                        peak_unrealized_usd=prev_peak,
                        current_unrealized_usd=unrealized,
                        tier_floor_usd=tier_floor,
                        risk_usd=0.0,        # not used in prompt-only flow
                        recent_bars=bar_dicts,
                        regime={},           # filled by caller if available
                        consecutive_holds=_position_consecutive_holds.get(key, 0),
                    )
                    db = _open_db_connection()
                    try:
                        decision = decide_exit_with_agent(
                            ctx, db_conn=db, log_fn=log, enabled=True,
                        )
                    finally:
                        if db is not None:
                            try: db.close()
                            except Exception: pass

                    if decision.action == "HOLD" and not report_only:
                        _position_consecutive_holds[key] = (
                            _position_consecutive_holds.get(key, 0) + 1
                        )
                        log(f"  AGENT_HOLD: {symbol} {side} peak=${prev_peak:.0f} "
                             f"cur=${unrealized:+.0f} -- {decision.reason} "
                             f"(holds={_position_consecutive_holds[key]})")
                        continue   # skip close this iteration
                    elif decision.action == "HOLD" and report_only:
                        log(f"  AGENT_HOLD (report-only, closing anyway): {symbol} "
                             f"{side} peak=${prev_peak:.0f} -- {decision.reason}")
                    # else: CLOSE or FALLBACK_CLOSE → proceed to market close
                    _position_consecutive_holds.pop(key, None)
                except Exception as e:
                    log(f"  exit_reasoner threw — falling back to rigid close: "
                         f"{type(e).__name__}: {e}")
                    # Fall through to mechanical close below

            # ── Mechanical close via native close_position endpoint ──
            # 2026-05-14: switched from place_order(market-IOC) which the
            # broker silently rejects with "limit price not set" (the
            # market-type code 1 is actually LIMIT in Topstep's schema).
            try:
                result = client.close_position(account_id, contract_id)
                if isinstance(result, dict) and result.get("success") is False:
                    err = result.get("errorMessage") or "broker rejected"
                    log(f"  PROFIT_LOCK_CLOSE REJECTED for {contract_id}: {err}")
                    try:
                        from tools.alert import send_alert as _alert
                        _alert(
                            f"CRITICAL: profit-lock close REJECTED for "
                            f"{symbol} at unrealized ${unrealized:+.0f}: {err}. "
                            f"Position still OPEN.",
                            level="crit",
                        )
                    except Exception:
                        pass
                    continue
                log(f"  PROFIT_LOCK_CLOSE: {symbol} {side} {size}ct "
                     f"unrealized=${unrealized:+.2f} peak=${prev_peak:+.2f} "
                     f"-- {reason}")
                # Discord alert — user wants visibility on every close
                try:
                    from tools.alert import send_alert as _alert
                    emoji = "✅" if unrealized > 0 else "❌"
                    _alert(
                        f"{emoji} PROFIT_LOCK_CLOSE {symbol} {side} {size}ct "
                        f"@ ${unrealized:+.0f} (peak ${prev_peak:+.0f}, "
                        f"give-back ${prev_peak - unrealized:.0f})",
                        level="info" if unrealized > 0 else "warn",
                    )
                except Exception:
                    pass
                _position_high_water.pop(key, None)
                _position_consecutive_holds.pop(key, None)
                _position_entry_ts_seen.pop(key, None)
                reset_trailed_floor(contract_id)
                # Audit-trail row in decisions table (close_position doesn't
                # produce an orders row the way the pre-2026-05-14 path did).
                _record_close_decision(
                    symbol=symbol, side=side, size=size,
                    contract_id=contract_id, unrealized=unrealized,
                    peak=prev_peak, reason=reason, kind="close",
                )
                closed.append({"symbol": symbol, "side": side, "size": size,
                                "unrealized": unrealized, "peak": prev_peak,
                                "reason": reason})
            except Exception as e:
                log(f"  profit_lock_close FAILED {symbol}: "
                     f"{type(e).__name__}: {e}")
        except Exception as e:
            log(f"  profit_protect inner error on {p.get('contractId','?')}: "
                 f"{type(e).__name__}: {e}")
            continue
    return closed
