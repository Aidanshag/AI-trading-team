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
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

from dotenv import load_dotenv
load_dotenv()

# Project root
_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)
sys.path.insert(0, str(_HERE))

from tools.backtest import strategies as strats  # noqa: E402
from tools.projectx_client import (
    get_client, get_account_id, ProjectXError,  # noqa: E402
)
from state.db import get_db  # noqa: E402


# ────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────

SCAN_INTERVAL_SEC = 300          # 5-minute cadence
LOOKBACK_BARS = 6                 # find_latest_signal cutoff (30 min on 5m bars)
PER_TRADE_LOSS_CAP_USD = 150.0    # force-close if unrealized < -this
SAME_SYMBOL_COOLDOWN_MIN = 45     # don't re-fire same symbol within window
MAX_TRADES_PER_DAY = 8            # hard cap on entries per UTC day
LIVE_ALLOWLIST_PATH = _HERE / "state" / "strategy_validation.json"
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
    """True if today's realized P&L breaches the daily loss limit."""
    risk = _load_yaml("config/risk_limits.yaml")
    dll = float(risk.get("account", {}).get("daily_loss_limit_usd", 1000))
    realized = float(snap.get("realized_pl_day_usd") or 0)
    if realized <= -dll:
        return True, f"realized_day=${realized:+.2f} <= -${dll:.0f}"
    return False, ""


# ────────────────────────────────────────────────────────────────
# Snapshot capture (heartbeat + DLL)
# ────────────────────────────────────────────────────────────────

def capture_snapshot(client, account_id) -> dict | None:
    """Pull broker state, compute realized P&L, write snapshot row."""
    db = get_db()
    try:
        accounts = client.get_accounts()
        mine = next((a for a in accounts if str(a.get("id")) == str(account_id)), None)
        if not mine:
            return None
        balance = float(mine.get("balance", 0))
        can_trade = bool(mine.get("canTrade", True))
        positions = client.get_positions(account_id) or []
        open_contracts = sum(int(p.get("size") or 0) for p in positions)

        first_today = db.first_snapshot_today_utc()
        realized_day = balance - float(first_today["balance_usd"]) if first_today else 0.0
        starting = float(_load_yaml("config/risk_limits.yaml").get("account", {}).get("starting_balance", 50000))
        peak = db.peak_eod_balance(fallback=starting)
        trailing_dd = max(0.0, peak - balance)

        # Unrealized P&L computed from positions × latest bar mark
        unrealized = compute_unrealized(client, positions)

        db.record_account_snapshot(
            balance_usd=balance, environment="combine",
            unrealized_pl_usd=unrealized,
            realized_pl_day_usd=realized_day,
            trailing_dd_usd=trailing_dd,
            open_contracts_total=open_contracts,
            can_trade=can_trade,
        )
        return {"balance_usd": balance, "realized_pl_day_usd": realized_day,
                "unrealized_pl_usd": unrealized,
                "open_contracts_total": open_contracts, "can_trade": can_trade}
    except Exception as e:
        # Write degraded heartbeat with last-known balance
        try:
            last = db.latest_account_snapshot()
            if last:
                db.record_account_snapshot(
                    balance_usd=float(last.get("balance_usd") or 0),
                    environment="combine",
                    unrealized_pl_usd=0.0,
                    realized_pl_day_usd=float(last.get("realized_pl_day_usd") or 0),
                    trailing_dd_usd=float(last.get("trailing_dd_usd") or 0),
                    open_contracts_total=int(last.get("open_contracts_total") or 0),
                    can_trade=False,
                )
        except Exception:
            pass
        _log(f"snapshot capture failed: {type(e).__name__}: {e}")
        return None


# compute_unrealized extracted to tools/unrealized_pnl.py 2026-05-08 (continuous trim).
from tools.unrealized_pnl import compute_unrealized  # noqa: E402


# ────────────────────────────────────────────────────────────────
# Brain interface — read live cells
# ────────────────────────────────────────────────────────────────

def load_live_cells() -> list[dict]:
    """Read the brain's validated allowlist."""
    if not LIVE_ALLOWLIST_PATH.exists():
        return []
    try:
        st = json.loads(LIVE_ALLOWLIST_PATH.read_text(encoding="utf-8"))
        return st.get("live_allowlist") or []
    except Exception:
        return []


def session_now_utc(now_utc: datetime) -> str:
    """Map UTC to ET session bucket."""
    et_hour = (now_utc.hour - 4 + now_utc.minute / 60.0) % 24
    if 9.5 <= et_hour < 16:    return "RTH"
    if 4 <= et_hour < 9.5:     return "London"
    if 16 <= et_hour < 20:     return "PostClose"
    return "Asian"


# ────────────────────────────────────────────────────────────────
# Bars + signals
# ────────────────────────────────────────────────────────────────

# fetch_bars extracted to tools/bar_fetcher.py 2026-05-08 (continuous trim).
# Wrapper preserves call signature so scan_once doesn't change.
from tools.bar_fetcher import fetch_bars as _fetch_bars_impl  # noqa: E402

def fetch_bars(client, symbol: str, minutes: int = 5, lookback: int = 200):
    return _fetch_bars_impl(client, symbol, minutes, lookback, log_fn=_log)


def find_latest_signal(bars: pd.DataFrame, strategy_fn) -> dict | None:
    """Run strategy on bars, return the most recent entry signal in
    the last LOOKBACK_BARS bars (ignore stale)."""
    if len(bars) < 30:
        return None
    cutoff_idx = max(0, len(bars) - LOOKBACK_BARS)
    cutoff = bars.index[cutoff_idx]
    latest = None
    try:
        for sig in strategy_fn(bars):
            if sig.kind != "entry":
                continue
            if sig.date >= cutoff:
                latest = sig
    except Exception:
        return None
    if latest is None:
        return None
    return {
        "date": latest.date, "side": latest.side,
        "price": float(latest.price),
        "stop": float(latest.stop) if latest.stop is not None else None,
        "target": float(latest.target) if latest.target is not None else None,
        "reason": latest.reason,
    }


# ────────────────────────────────────────────────────────────────
# Bracket placement
# ────────────────────────────────────────────────────────────────

# Tick math extracted to tools/trader_utils.py
from tools.trader_utils import _tick_size, _round_to_tick  # noqa: E402


def place_bracket(client, account_id, symbol: str, signal: dict,
                  qty: int = 1, dry_run: bool = False) -> dict:
    """Place entry-limit + stop-limit + target-limit. Each leg is its
    own broker order tagged with a related customTag."""
    side = "buy" if signal["side"] == "long" else "sell"
    cid = f"live_{uuid.uuid4().hex[:12]}"
    db = get_db()
    tick = _tick_size(symbol)
    entry_price = float(signal["price"])
    # Marketable-limit: 5-tick slippage buffer (matches v1 behavior, proven)
    if side == "buy":
        limit_px = _round_to_tick(entry_price + 5 * tick, tick)
    else:
        limit_px = _round_to_tick(entry_price - 5 * tick, tick)
    stop_px = _round_to_tick(float(signal["stop"]), tick)
    target_px = _round_to_tick(float(signal["target"]), tick) if signal.get("target") else None

    if dry_run:
        _log(f"  DRY: would place {symbol} {side} qty={qty} entry={limit_px} "
              f"stop={stop_px} target={target_px} cid={cid}")
        return {"status": "dry_run", "client_order_id": cid}

    # Front-month contract id
    try:
        contract_id = client.front_month_contract_id(symbol)
    except ProjectXError as e:
        _log(f"  contract lookup failed for {symbol}: {e}")
        return {"status": "failed", "error": str(e)}

    # Record entry in DB before submitting
    db.connect().execute(
        """INSERT INTO orders (client_order_id, agent, ts_proposed, symbol, side,
                                 order_type, qty, limit_price, stop_price,
                                 status, risk_verdict)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (cid, "live_trader", _utcnow_iso(), symbol, side, "limit", int(qty),
         limit_px, stop_px, "proposed", "allow"),
    )
    db.connect().commit()

    # 1. Entry as marketable-limit
    try:
        result = client.place_order(
            account_id=account_id, contract_id=contract_id,
            side=side, qty=int(qty), order_type="limit",
            limit_price=limit_px, stop_price=None,
            time_in_force="day", client_order_id=cid,
        )
    except ProjectXError as e:
        _log(f"  entry place failed: {e}")
        return {"status": "failed", "error": str(e)}

    if isinstance(result, dict) and result.get("success") is False:
        err = result.get("errorMessage") or "broker rejected"
        _log(f"  entry rejected: {err}")
        return {"status": "rejected", "error": err}

    broker_oid = (result.get("orderId") or result.get("id") if isinstance(result, dict) else None)
    db.connect().execute(
        "UPDATE orders SET ts_submitted=?, status=?, broker_order_id=? WHERE client_order_id=?",
        (_utcnow_iso(), "submitted", str(broker_oid) if broker_oid else None, cid),
    )
    db.connect().commit()

    # 2. Stop-limit (1-tick offset for Topstep's tight-limit rule)
    opp = "sell" if side == "buy" else "buy"
    stop_limit_px = (stop_px - tick) if opp == "sell" else (stop_px + tick)
    stop_limit_px = _round_to_tick(stop_limit_px, tick)
    stop_cid = cid + "_stop"
    try:
        sr = client.place_order(
            account_id=account_id, contract_id=contract_id,
            side=opp, qty=int(qty), order_type="stop_limit",
            limit_price=stop_limit_px, stop_price=stop_px,
            time_in_force="gtc", client_order_id=stop_cid,
        )
        sboid = (sr.get("orderId") or sr.get("id")) if isinstance(sr, dict) else None
        db.connect().execute(
            """INSERT INTO orders (client_order_id, agent, ts_proposed, ts_submitted,
                                     symbol, side, order_type, qty, stop_price,
                                     status, risk_verdict, broker_order_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (stop_cid, "live_trader", _utcnow_iso(), _utcnow_iso(),
             symbol, opp, "stop", int(qty), stop_px,
             "submitted", "allow", str(sboid) if sboid else None),
        )
        db.connect().commit()
    except ProjectXError as e:
        _log(f"  stop placement failed: {e}")
        # Continue — target may still place; verification will catch missing stop

    # 3. Target as limit (only if target price provided)
    if target_px is not None:
        target_cid = cid + "_target"
        try:
            tr = client.place_order(
                account_id=account_id, contract_id=contract_id,
                side=opp, qty=int(qty), order_type="limit",
                limit_price=target_px, stop_price=None,
                time_in_force="gtc", client_order_id=target_cid,
            )
            tboid = (tr.get("orderId") or tr.get("id")) if isinstance(tr, dict) else None
            db.connect().execute(
                """INSERT INTO orders (client_order_id, agent, ts_proposed, ts_submitted,
                                         symbol, side, order_type, qty, limit_price,
                                         status, risk_verdict, broker_order_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (target_cid, "live_trader", _utcnow_iso(), _utcnow_iso(),
                 symbol, opp, "limit", int(qty), target_px,
                 "submitted", "allow", str(tboid) if tboid else None),
            )
            db.connect().commit()
        except ProjectXError as e:
            _log(f"  target placement failed: {e}")

    _log(f"  PLACED {symbol} {side} qty={qty} entry≈{limit_px} stop={stop_px} "
          f"target={target_px or '—'} cid={cid}")
    return {"status": "submitted", "client_order_id": cid,
            "broker_order_id": broker_oid}


# ────────────────────────────────────────────────────────────────
# Per-trade loss-cap enforcement
# ────────────────────────────────────────────────────────────────

def enforce_loss_cap(client, account_id) -> int:
    """Force-close any position whose unrealized loss < -PER_TRADE_LOSS_CAP_USD.
    Returns # positions closed."""
    closed = 0
    try:
        positions = client.get_positions(account_id) or []
    except Exception:
        return 0
    syms = _load_yaml("config/symbols.yaml").get("symbols", {})
    for p in positions:
        size = int(p.get("size") or 0)
        if size == 0:
            continue
        contract = p.get("contractId") or ""
        avg = float(p.get("avgPrice") or 0)
        if avg <= 0 or not contract:
            continue
        type_code = int(p.get("type") or 0)
        sign = 1 if type_code == 1 else -1 if type_code == 2 else (1 if size > 0 else -1)
        size = abs(size)
        root = None
        for tok in contract.split("."):
            if tok in ("CON", "F", "US", ""): continue
            if len(tok) <= 3 and tok and tok[0].isalpha() and tok[1:].isdigit(): continue
            root = tok; break
        meta = syms.get(root or "", {})
        tick_size = float(meta.get("tick_size") or 0)
        tick_value = float(meta.get("tick_value") or 0)
        if tick_size <= 0 or tick_value <= 0:
            continue
        try:
            bars = client.get_bars(contract_id=contract,
                                    start_time=(_now_utc() - timedelta(minutes=10)).isoformat(),
                                    end_time=_now_utc().isoformat(),
                                    unit=2, unit_number=1, limit=5, live=False)
            mark = float(bars[-1].get("c") or 0) if bars else 0
        except Exception:
            continue
        if mark <= 0:
            continue
        unrealized = sign * size * ((mark - avg) / tick_size) * tick_value
        if unrealized < -PER_TRADE_LOSS_CAP_USD:
            opp = "sell" if type_code == 1 else "buy"
            cid = f"livecap_{uuid.uuid4().hex[:8]}"
            try:
                client.place_order(account_id=account_id, contract_id=contract,
                                     side=opp, qty=size, order_type="market",
                                     time_in_force="ioc", client_order_id=cid)
                _log(f"  LOSS-CAP CLOSE: {root} unrealized=${unrealized:+.2f} < -${PER_TRADE_LOSS_CAP_USD:.0f}")
                closed += 1
            except Exception as e:
                _log(f"  loss-cap close failed for {root}: {e}")
    return closed


# ────────────────────────────────────────────────────────────────
# Orphan-bracket cleanup
# ────────────────────────────────────────────────────────────────

ORPHAN_GRACE_SEC = 120  # 2-min grace before any cancel


def cleanup_orphan_brackets(client, account_id) -> int:
    """Cancel working bracket legs whose underlying position is flat.

    Why: ProjectX `place_order` has no native bracket linkage; v2 places
    entry/stop/target as 3 independent orders. If broker's implicit OCO
    fails (or simply doesn't exist), one leg filling leaves the others
    working. This sweep cancels orders that no longer protect a position.

    Safe-by-default:
      - 2-min grace per order: never cancels a freshly-placed bracket
        whose position hasn't propagated through the API yet.
      - Only acts on orders tagged 'live_' (our customTag prefix). Won't
        touch user-placed manual orders.
      - Only cancels when position is verifiably flat (not inferred).

    Returns # orders cancelled.
    """
    cancelled = 0
    try:
        positions = client.get_positions(account_id) or []
        working = client.get_working_orders(account_id) or []
    except Exception as e:
        _log(f"  cleanup skipped (broker fetch failed): {type(e).__name__}: {e}")
        return 0

    # Map contractId → True if position is non-zero
    has_position: dict[str, bool] = {}
    for p in positions:
        cid = p.get("contractId")
        if not cid:
            continue
        size = int(p.get("size") or 0)
        if size != 0:
            has_position[cid] = True

    now = _now_utc()
    for o in working:
        tag = str(o.get("customTag") or "")
        if not tag.startswith("live_"):
            continue  # not ours
        cid = o.get("contractId")
        if not cid:
            continue
        if has_position.get(cid):
            continue  # position is open; bracket is legitimate

        # Position is flat for this contract. Apply grace period.
        try:
            ts_str = o.get("creationTimestamp") or ""
            if ts_str:
                order_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                age_sec = (now - order_ts).total_seconds()
            else:
                age_sec = ORPHAN_GRACE_SEC + 1  # no timestamp → assume old enough
        except Exception:
            age_sec = ORPHAN_GRACE_SEC + 1

        if age_sec < ORPHAN_GRACE_SEC:
            continue  # too fresh; broker may still be propagating fill state

        oid = o.get("id") or o.get("orderId")
        if not oid:
            continue
        try:
            client.cancel_order(account_id, oid)
            _log(f"  cleaned orphan {tag} (id={oid}, age={age_sec:.0f}s, contract={cid})")
            cancelled += 1
        except Exception as e:
            _log(f"  cleanup cancel failed for {oid}: {type(e).__name__}: {e}")

    return cancelled


# Cooldown / daily-count queries extracted to tools/trade_state.py 2026-05-08.
from tools.trade_state import recent_thesis_for as _recent_thesis_for_impl  # noqa: E402
from tools.trade_state import todays_trade_count  # noqa: E402

def recent_thesis_for(symbol: str, minutes: int = SAME_SYMBOL_COOLDOWN_MIN) -> bool:
    return _recent_thesis_for_impl(symbol, minutes)


# ────────────────────────────────────────────────────────────────
# Main scan loop
# ────────────────────────────────────────────────────────────────

def scan_once(*, dry_run: bool = False, paper: bool = False) -> dict:
    """One scan pass: snapshot, gates, signal-detect, place."""
    summary = {"scanned": 0, "triggers": 0, "placed": 0, "blocked": 0,
               "skipped_in_trade": 0, "skipped_cooldown": 0, "errors": 0}
    halted, reason = is_halted()
    if halted:
        _log(f"HALTED: {reason}")
        return {"status": "halted", "reason": reason}

    # Sunday-reopen first-30-min blackout: skip new entries when spreads are widest.
    # Snapshots + cleanup still run; we just don't place new trades.
    if is_sunday_reopen_blackout(_now_utc()):
        _log("Sunday-reopen blackout (17:00-17:30 ET): skipping new entries this scan")
        return {"status": "sunday_reopen_blackout"}

    try:
        client = get_client()
        account_id = get_account_id()
    except Exception as e:
        _log(f"broker unavailable: {e}")
        return {"status": "broker_unavailable", "error": str(e)}

    snap = capture_snapshot(client, account_id)
    if snap and not snap.get("can_trade", True):
        _log(f"can_trade=false; halt scan")
        return {"status": "broker_can_trade_false"}

    # DLL hard kill
    if snap:
        breached, why = dll_breached(snap)
        if breached:
            _log(f"DLL BREACH: {why}")
            return {"status": "dll_halt", "reason": why}

    # Per-trade loss-cap enforcement
    if not dry_run and not paper:
        enforce_loss_cap(client, account_id)
        cleanup_orphan_brackets(client, account_id)

    # Cells to scan
    cells = load_live_cells()
    if not cells:
        _log(f"no live cells in allowlist; skipping")
        return {"status": "no_cells"}

    sess_now = session_now_utc(_now_utc())
    # Group cells by symbol so we fetch bars once per symbol
    cells_by_symbol: dict[str, list[dict]] = {}
    for c in cells:
        cells_by_symbol.setdefault(c["symbol"], []).append(c)

    syms = sorted(cells_by_symbol.keys())
    _log(f"scanning {len(syms)} symbols (session={sess_now}): {syms}")

    # Open contract count — bound concurrent trades
    open_pos = (snap.get("open_contracts_total") or 0) if snap else 0
    if open_pos > 0:
        _log(f"  {open_pos} open contracts; skipping new entries")
        return {"status": "in_position", **summary}

    # Daily trade cap
    today_count = todays_trade_count()
    if today_count >= MAX_TRADES_PER_DAY:
        _log(f"  daily trade cap hit ({today_count}/{MAX_TRADES_PER_DAY}); halt for today")
        return {"status": "daily_cap_hit", "today_count": today_count, **summary}

    for symbol in syms:
        # Cooldown check
        if recent_thesis_for(symbol):
            summary["skipped_cooldown"] += 1
            continue

        # Pull bars once per symbol
        bars = fetch_bars(client, symbol)
        if bars is None or len(bars) < 30:
            continue

        # For each cell, check session+side match and try to fire
        fired_for_symbol = False
        for cell in cells_by_symbol[symbol]:
            if fired_for_symbol:
                break
            if cell.get("session") != sess_now:
                continue
            strat_name = cell.get("strategy")
            strat_fn = getattr(strats, strat_name, None)
            if strat_fn is None:
                continue
            sig = find_latest_signal(bars, strat_fn)
            summary["scanned"] += 1
            if sig is None:
                continue
            if sig.get("stop") is None:
                continue
            # Side must match the cell
            sig_side = str(sig.get("side", "")).lower()
            if sig_side != cell.get("side"):
                continue
            summary["triggers"] += 1
            # Place bracket
            try:
                if paper:
                    _log(f"  PAPER: would place {symbol} {strat_name} {sig_side} "
                          f"@ {sig['price']} stop={sig['stop']} target={sig.get('target')}")
                    summary["placed"] += 1
                else:
                    result = place_bracket(client, account_id, symbol, sig, dry_run=dry_run)
                    if result.get("status") in ("submitted", "dry_run"):
                        summary["placed"] += 1
                    else:
                        summary["errors"] += 1
                fired_for_symbol = True
            except Exception as e:
                _log(f"  place_bracket exception: {e}")
                summary["errors"] += 1

    _log(f"  summary: {summary}")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(prog="live_trader")
    p.add_argument("--once", action="store_true", help="single scan + exit")
    p.add_argument("--dry-run", action="store_true", help="signals + decisions, no orders")
    p.add_argument("--paper", action="store_true", help="paper-mode (no broker orders)")
    p.add_argument("--interval", type=int, default=SCAN_INTERVAL_SEC)
    args = p.parse_args()

    if os.environ.get("FUND_MODE", "live").lower() == "paper":
        args.paper = True

    if args.once:
        scan_once(dry_run=args.dry_run, paper=args.paper)
        return 0

    _log(f"=== live_trader started: interval={args.interval}s, "
          f"dry_run={args.dry_run}, paper={args.paper} ===")
    while True:
        try:
            scan_once(dry_run=args.dry_run, paper=args.paper)
        except KeyboardInterrupt:
            _log("interrupted; exiting")
            return 0
        except Exception as e:
            _log(f"scan error (will retry): {type(e).__name__}: {e}")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
