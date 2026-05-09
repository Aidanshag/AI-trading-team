"""PreToolUse risk hook — the hard gate on every order-placing tool call.

Returns a decision dict signalling either allow or block. When blocked, the
tool call never executes. Every verdict is logged to `risk_events`.

This module must be:
  - fast (sub-50ms typical; no network calls)
  - self-contained (reads config and SQLite state only)
  - conservative (on any ambiguity: BLOCK)

The rules enforced here are the SAME rules encoded in prompts and in the
Risk Manager agent. The hook is the fallback that catches anything the
soft layers miss.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

from state.db import get_db

# Tools that the hook gates. Everything else passes through.
ORDER_TOOLS = {
    "mcp__topstep__topstep_place_order",
    "mcp__topstep__topstep_flatten_all",
}

CONFIG_ROOT = Path("config")


def _load_yaml(name: str) -> dict[str, Any]:
    return yaml.safe_load((CONFIG_ROOT / name).read_text())


# --------------------------------------------------------------
# Core check helpers
# --------------------------------------------------------------
def _is_outright_short_future(order: dict[str, Any]) -> bool:
    """Outright short futures (no defined-risk structure) = naked."""
    return (
        order.get("side") == "sell"
        and order.get("structure_id") is None
        and _is_future(order.get("symbol", ""))
    )


def _is_future(symbol: str) -> bool:
    # Options symbols typically encode strike/expiry; futures do not.
    # A production implementation should use a proper symbol parser.
    return not any(c in symbol for c in ("C", "P")) or symbol.isalnum()


def _has_stop(order: dict[str, Any]) -> bool:
    return order.get("stop_price") is not None and order.get("stop_price") > 0


def _now_chicago() -> time:
    return datetime.now(tz=ZoneInfo("America/Chicago")).time()


# --------------------------------------------------------------
# The hook entry point
# --------------------------------------------------------------
async def risk_gate(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    """Claude Agent SDK PreToolUse hook.

    Returns:
      - {} to allow (no change)
      - {"hookSpecificOutput": {"hookEventName": "PreToolUse",
                                 "permissionDecision": "deny",
                                 "permissionDecisionReason": "..."}}
        to block.
    """
    tool_name: str = input_data.get("tool_name", "")
    if tool_name not in ORDER_TOOLS:
        return {}

    tool_input: dict[str, Any] = input_data.get("tool_input", {}) or {}
    agent_name = _extract_agent_name(context)

    limits = _load_yaml("risk_limits.yaml")
    topstep = _load_yaml("topstep.yaml")
    symbols = _load_yaml("symbols.yaml").get("symbols", {})

    db = get_db()
    snap = db.latest_account_snapshot()
    positions = db.current_positions()

    # Run checks in order of severity. First failure short-circuits.
    for check in (
        _check_kill_switch,
        _check_broker_can_trade,
        _check_thin_tape_regime,
        _check_autonomous_rth_window,
        _check_snapshot_freshness,
        _check_focus_universe,
        _check_strategy_blacklist,          # symbol+strategy blacklist (encoded lessons)
        _check_active_lessons,              # closes the learning loop at decision time
        _check_post_stop_cooldown,          # 15-min anti-tilt window after a stop-out
        _check_high_impact_blackout,        # event-window pre/post blackout
        _check_combine_defensive_ladder,    # $-150/$-300/$-500/$-750 progressive tightening
        _check_daily_target_lock,           # NEW: profit lock-in on the upside
        _check_daily_trade_count,
        _check_session_window,
        _check_no_naked_shorts,
        _check_defined_risk_structures,
        _check_stop_required,
        _check_daily_loss_limit,
        _check_trailing_drawdown,
        _check_per_symbol_limits,
        _check_sector_and_basket_limits,
        _check_consistency_rule,
        _check_options_structure_allowed,
    ):
        verdict = check(
            tool_name=tool_name,
            order=tool_input,
            agent=agent_name,
            limits=limits,
            topstep=topstep,
            symbols=symbols,
            snap=snap,
            positions=positions,
        )
        if verdict is not None:
            db.record_risk_event(
                severity="block",
                rule=verdict["rule"],
                agent=agent_name,
                detail={"reason": verdict["reason"], "order": tool_input},
            )
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"[{verdict['rule']}] {verdict['reason']}",
                }
            }

    # All checks passed.
    db.record_risk_event(
        severity="info",
        rule="risk_gate_pass",
        agent=agent_name,
        detail={"tool": tool_name, "order": tool_input},
    )
    return {}


def _extract_agent_name(context: Any) -> str:
    # SDK passes agent identity via context; fall back if unavailable.
    return getattr(context, "agent_name", None) or "unknown"


# --------------------------------------------------------------
# Individual checks. Each returns None (pass) or a block dict.
# --------------------------------------------------------------
def _check_kill_switch(**kw):
    hard = kw["limits"].get("hard_rules", {})
    # Manual permanent halt
    if hard.get("trading_halted"):
        return {"rule": "kill_switch", "reason": "Global kill switch is engaged."}
    # Auto-expiring halt — blocks trading until timestamp passes
    halt_until_str = hard.get("trading_halt_until")
    if halt_until_str:
        try:
            from datetime import datetime, timezone
            halt_until = datetime.fromisoformat(str(halt_until_str).replace("Z", "+00:00"))
            now = datetime.now(tz=timezone.utc)
            if now < halt_until:
                return {
                    "rule": "auto_halt",
                    "reason": f"Auto-halt active until {halt_until_str} (now: {now.isoformat()})",
                }
        except Exception as e:
            # Malformed timestamp on the kill-switch — fail CLOSED.
            # Better to block all trades and force human investigation than
            # to silently let orders through because the YAML had a typo.
            return {
                "rule": "kill_switch_malformed",
                "reason": (f"trading_halt_until is unparseable: {halt_until_str!r} "
                           f"({e}). Fix the value in config/risk_limits.yaml or "
                           f"set trading_halt_until to a past timestamp."),
            }
    return None


def _check_broker_can_trade(**kw):
    """Block when the broker has flipped the account to canTrade=false.

    Topstep can mark an account un-tradeable server-side (e.g., DLL hit at
    their layer, account paused, suspended). The orchestrator captures this
    flag into account_snapshots.can_trade. If we don't gate on it, the
    system keeps proposing orders that the broker rejects — wastes API
    spend and floods our error logs.

    Pass conditions:
      - No snapshot yet (cold start; let the kill_switch/halt logic handle)
      - Snapshot's can_trade is truthy
    """
    snap = kw.get("snap")
    if not snap:
        return None
    # SQLite stores bools as int; tolerate either. Default-permissive when
    # the column is absent (older snapshots predate the migration).
    can_trade = snap.get("can_trade", 1)
    if can_trade in (None, 1, True):
        return None
    return {
        "rule": "broker_can_trade_false",
        "reason": (
            "Broker reports canTrade=false on this account. "
            "Likely causes: DLL breach detected server-side, account "
            "paused/suspended, or post-loss cooldown. Check Topstep "
            "dashboard before resuming. Will auto-clear once the broker "
            "flips canTrade back to true and the next snapshot lands."
        ),
    }


def _check_thin_tape_regime(**kw):
    """Block all entries during the thin-tape window from regime_gates config.

    The 2026-04-29 incident bled $1,013 during 03:30-07:00 UTC because
    strategies fired in random-walk Asian-session tape. This block applies
    to BOTH agent-chain orders (via this hook) and auto_trader (via its
    own check). Source of truth: `risk_limits.yaml:regime_gates.thin_tape`.
    """
    cfg = (kw["limits"].get("regime_gates") or {}).get("thin_tape") or {}
    if not cfg.get("enabled"):
        return None
    try:
        sh, sm = (int(x) for x in str(cfg.get("start_et", "21:00")).split(":"))
        eh, em = (int(x) for x in str(cfg.get("end_et",   "04:00")).split(":"))
    except Exception:
        return None
    et_now = datetime.now(tz=ZoneInfo("America/New_York"))
    now_min = et_now.hour * 60 + et_now.minute
    s_min = sh * 60 + sm
    e_min = eh * 60 + em
    in_window = (s_min <= now_min < e_min) if s_min < e_min else (
        now_min >= s_min or now_min < e_min)
    if in_window:
        return {
            "rule": "thin_tape_regime",
            "reason": (
                f"{et_now.strftime('%H:%M ET')} is in thin-tape window "
                f"{cfg.get('start_et')}–{cfg.get('end_et')} ET. "
                f"{cfg.get('reason', 'Regime gate blocks new entries.')}"
            ),
        }
    return None


def _check_snapshot_freshness(**kw):
    """Refuse to trade with stale snapshot data when autonomous_mode is on.

    Today's #1 root cause was an empty snapshot table making every P&L-aware
    check return None. Even with the writer in place, a silent failure of the
    writer would reproduce the same blind state. This check fails CLOSED:
    no snapshot in the last N minutes → block.
    """
    try:
        import yaml
        from pathlib import Path
        fund_cfg = yaml.safe_load(Path("config/fund.yaml").read_text())
    except Exception:
        return None
    if not (fund_cfg or {}).get("autonomous_mode"):
        return None
    rules = (fund_cfg or {}).get("autonomous_restrictions") or {}
    max_age_min = int(rules.get("require_snapshot_within_minutes", 0))
    if max_age_min <= 0:
        return None
    snap = kw.get("snap")
    if not snap or not snap.get("ts"):
        return {
            "rule": "snapshot_freshness",
            "reason": (
                f"Autonomous mode requires a snapshot within "
                f"{max_age_min} minutes, but no snapshot found. "
                f"Snapshot writer (orchestrator.tick_workflow OR auto_trader) "
                f"is not running or is failing silently."
            ),
        }
    try:
        snap_ts = datetime.fromisoformat(str(snap["ts"]).replace("Z", "+00:00"))
        age_min = (datetime.now(tz=timezone.utc) - snap_ts).total_seconds() / 60
    except Exception:
        return {
            "rule": "snapshot_freshness",
            "reason": f"Snapshot ts {snap.get('ts')!r} is unparseable.",
        }
    if age_min > max_age_min:
        return {
            "rule": "snapshot_freshness",
            "reason": (
                f"Latest snapshot is {age_min:.1f} min old (>{max_age_min} "
                f"min limit under autonomous mode). Investigate writer health."
            ),
        }
    return None


def _check_autonomous_rth_window(**kw):
    """If autonomous_mode AND autonomous_restrictions.rth_only, block entries
    outside the configured RTH window.

    Lives in hooks/risk_gate.py so agent-chain orders can't bypass it. The
    auto_trader has its own equivalent check at the start of scan_once.
    """
    try:
        import yaml
        from pathlib import Path
        fund_cfg = yaml.safe_load(Path("config/fund.yaml").read_text())
    except Exception:
        return None
    if not (fund_cfg or {}).get("autonomous_mode"):
        return None
    rules = (fund_cfg or {}).get("autonomous_restrictions") or {}
    if not rules.get("rth_only"):
        return None
    try:
        sh, sm = (int(x) for x in str(rules.get("rth_start_et", "07:30")).split(":"))
        eh, em = (int(x) for x in str(rules.get("rth_end_et",   "14:30")).split(":"))
    except Exception:
        return None
    et_now = datetime.now(tz=ZoneInfo("America/New_York"))
    now_min = et_now.hour * 60 + et_now.minute
    if (sh*60+sm) <= now_min < (eh*60+em):
        return None
    return {
        "rule": "autonomous_rth_only",
        "reason": (
            f"Autonomous mode is on and {et_now.strftime('%H:%M ET')} is "
            f"outside the RTH window "
            f"{rules.get('rth_start_et')}–{rules.get('rth_end_et')} ET. "
            f"Either wait for RTH or flip autonomous_mode off in fund.yaml."
        ),
    }


def _check_combine_defensive_ladder(**kw):
    """Enforce the Combine defensive ladder from `risk_limits.yaml:combine_defense`.

    The ladder tightens as day P&L deteriorates:
      -$150 -> warn; sizing preferred at 40 bps
      -$300 -> restrict: no new entries unless closing risk; max 40 bps
      -$500 -> lockdown: no new entries of any kind (this is INTERNAL DLL target)
      -$750 -> emergency_flatten: market-flatten immediately, halt session

    User directive: agents should "essentially never hit" Topstep's $1000 DLL.
    This hook enforces the ladder *automatically* — not just by prompt-level
    discipline. Reads `combine_defense.ladder` for thresholds and actions.
    """
    snap = kw["snap"]
    limits = kw["limits"]
    ladder = (limits.get("combine_defense") or {}).get("ladder") or []
    if not snap or not ladder:
        return None

    # Day P&L = realized + unrealized
    day_pl = float(snap.get("realized_pl_day_usd", 0)) + float(snap.get("unrealized_pl_usd", 0))

    # Find the most-adverse step that's been triggered (lowest threshold P&L
    # has crossed). Ladder is descending: -150 -> -300 -> -500 -> -750.
    triggered = None
    for step in ladder:
        threshold = float(step.get("threshold_usd", 0))
        if day_pl <= threshold:
            triggered = step  # keep updating; we want the WORST step engaged

    if triggered is not None:
        action = (triggered.get("action") or "").lower()
        if action in ("lockdown", "emergency_flatten"):
            return {
                "rule": "defensive_ladder",
                "reason": (
                    f"Day P&L {day_pl:+.2f} triggered '{action}' at threshold "
                    f"{triggered.get('threshold_usd'):+}. New entries blocked. "
                    f"{triggered.get('description', '')}"
                ),
            }

    # Pre-trade projection: would worst-case loss push us into a hard step?
    worst = _proposed_worst_case_usd(kw["order"], kw["symbols"], kw["limits"], snap)
    if worst <= 0:
        return None
    projected = day_pl - worst
    for step in ladder:
        threshold = float(step.get("threshold_usd", 0))
        action = (step.get("action") or "").lower()
        if action not in ("lockdown", "emergency_flatten"):
            continue
        if projected <= threshold:
            return {
                "rule": "defensive_ladder_projected",
                "reason": (
                    f"Proposed worst-case ${worst:.2f} would push Day P&L to "
                    f"{projected:+.2f}, triggering '{action}' at threshold "
                    f"{threshold:+}. {step.get('description', '')}"
                ),
            }
    # 'warn' and 'restrict' don't hard-block here; they ALLOW the order through
    # this gate but tighten the per-trade cap (see `_check_per_trade_cap_with_ladder`
    # if/when added). For now we log a risk event and let later checks handle.
    # The Risk Manager prompt also reads this and reduces sizing accordingly.
    return None


def _check_focus_universe(**kw):
    """Block orders on symbols outside the active focus list.

    When `config/focus_universe.yaml:focus_period_active: true` AND
    `now < focus_period_expires`, only symbols in `allowed_symbols`
    (any sector) are tradeable. All others get blocked here.

    This is a hard gate — analysts can still RESEARCH non-focus
    symbols, but proposals on them die at execution.
    """
    try:
        focus = _load_yaml("focus_universe.yaml")
    except Exception:
        return None
    if not focus or not focus.get("focus_period_active"):
        return None

    # Check expiry
    expiry_str = focus.get("focus_period_expires")
    if expiry_str:
        from datetime import datetime, timezone
        try:
            expiry = datetime.fromisoformat(str(expiry_str).replace("Z", "+00:00"))
            if datetime.now(tz=timezone.utc) >= expiry:
                return None  # window expired
        except Exception:
            pass

    # Build allowlist across all sectors
    allowed: set[str] = set()
    for sector_syms in (focus.get("allowed_symbols") or {}).values():
        for s in (sector_syms or []):
            allowed.add(str(s).upper())
    if not allowed:
        return None  # nothing configured (effectively disabled)

    # Check the order's symbol
    order_sym = (kw["order"].get("symbol") or "").upper()
    if not order_sym:
        return None  # symbol-less orders bypass (handled elsewhere)
    # Tolerate Topstep contractId form like "CON.F.US.XX.M26"
    if "." in order_sym:
        # Extract the root token
        for part in order_sym.split("."):
            if part in allowed or _normalize_root(part) in allowed:
                return None
        return {
            "rule": "focus_universe",
            "reason": (f"Symbol {order_sym} not in active focus universe. "
                       f"Allowed: {sorted(allowed)}. "
                       f"To remove restriction, set focus_universe.yaml:"
                       f"focus_period_active=false."),
        }
    if order_sym in allowed:
        return None
    return {
        "rule": "focus_universe",
        "reason": (f"Symbol {order_sym} not in active focus universe. "
                   f"Allowed: {sorted(allowed)}. "
                   f"To extend, edit config/focus_universe.yaml."),
    }


def _normalize_root(token: str) -> str:
    """Map ProjectX contract roots back to our trading-symbol convention.
    E.g. 'TYA' → 'ZN' (10Y T-Note), 'EP' → 'ES', 'NGE' → 'NG'.

    These mappings are verified empirically from broker.get_positions()
    contract IDs. Missing entries cause silent matching failures in
    _broker_position_for, which is what produced the over-trading bug
    on 2026-04-29 (NGE positions weren't recognized as 'NG' positions).
    """
    map_to_our = {
        # Verified live on Topstep account 2026-04-29
        "TYA": "ZN", "FVA": "ZF", "EP": "ES", "ENQ": "NQ",
        "GCE": "GC", "CLE": "CL", "MCLE": "MCL", "HOE": "HO",
        "NGE": "NG",   # CRITICAL: was missing — added 2026-04-29
        "NQG": "QG", "NQM": "QM", "ZCE": "ZC", "CPE": "HG",
        "GLE": "LE", "GMET": "METK", "EU6": "6E", "BP6": "6B",
        "JY6": "6J", "DA6": "6A", "CA6": "6C", "MX6": "6M",
        "EEU": "E7", "RBE": "RB", "MNGE": "MNG",
    }
    return map_to_our.get(token.upper(), token.upper())


def _check_daily_trade_count(**kw):
    """Hard cap on number of order placements per UTC day under autonomous
    mode. Reads `account.max_trades_per_day` from risk_limits.yaml. Counts
    successful order placements via `risk_gate_pass` info events recorded
    in `risk_events` since UTC midnight today.

    Skipped when fund.yaml:autonomous_mode is False (supervised mode lets
    the Risk Manager judge).
    """
    # Gate only fires under autonomous mode. Lazy-load fund.yaml.
    try:
        fund = yaml.safe_load((CONFIG_ROOT / "fund.yaml").read_text())
    except Exception:
        return None
    if not (fund or {}).get("autonomous_mode", False):
        return None

    cap = (kw["limits"].get("account", {}) or {}).get("max_trades_per_day")
    if not cap or cap <= 0:
        return None

    # Count today's risk_gate_pass events (== orders that previously cleared)
    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    db = get_db()
    row = db.connect().execute(
        "SELECT COUNT(*) AS n FROM risk_events "
        "WHERE rule = 'risk_gate_pass' AND ts LIKE ?",
        (f"{today_utc}%",),
    ).fetchone()
    n = (row[0] if row else 0) or 0
    if n >= cap:
        return {
            "rule": "max_trades_per_day",
            "reason": (
                f"Daily trade cap reached ({n}/{cap}). Autonomous-mode hard "
                "ceiling. Resets at UTC midnight or by lifting "
                "fund.yaml:autonomous_mode."
            ),
        }
    return None


def _check_session_window(**kw):
    """Block only the actual Globex daily maintenance break.

    Globex trades Sun 17:00 CT → Fri 16:00 CT with a daily maintenance
    pause from 16:00–17:00 CT. The previous implementation read
    `no_new_positions_after_local_time: 15:55` and blocked EVERY hour
    past 15:55 — which killed all overnight trading. Bug fixed
    2026-04-29 per user "actually do trades" directive.

    New logic: cutoff time defines the START of a 65-min window that
    ends at 17:00 CT. Outside that window, trading is permitted.
    """
    sessions = kw["limits"].get("sessions", {})
    cutoff_str = sessions.get("no_new_positions_after_local_time")
    if not cutoff_str:
        return None
    hh, mm = (int(x) for x in cutoff_str.split(":"))
    cutoff = time(hh, mm)
    reopen = time(17, 0)   # Globex reopens at 17:00 CT
    now_ct = _now_chicago()
    # Block only the cutoff → reopen window (default 15:55 → 17:00)
    if cutoff <= now_ct < reopen:
        return {
            "rule": "session_cutoff",
            "reason": (f"No new positions during Globex maintenance window "
                       f"({cutoff_str} – 17:00 CT). Currently {now_ct.strftime('%H:%M')} CT."),
        }
    return None


def _check_no_naked_shorts(**kw):
    if not kw["limits"]["hard_rules"].get("no_naked_shorts"):
        return None
    order = kw["order"]
    if _is_outright_short_future(order):
        return {
            "rule": "naked_short_future",
            "reason": (
                "Outright short futures are not permitted. "
                "Use a defined-risk structure (spread, inter-commodity, or options cover)."
            ),
        }
    return None


def _check_defined_risk_structures(**kw):
    order = kw["order"]
    # If the order claims to be part of a structure, the structure must exist
    # in the DB and have a bounded max_loss_usd.
    sid = order.get("structure_id")
    if sid is None:
        return None
    row = get_db().connect().execute(
        "SELECT max_loss_usd FROM structures WHERE id = ?", (sid,)
    ).fetchone()
    if row is None:
        return {"rule": "unknown_structure", "reason": f"structure_id={sid} not found."}
    if row["max_loss_usd"] is None:
        return {
            "rule": "undefined_risk_structure",
            "reason": f"structure_id={sid} has no max_loss — would be undefined risk.",
        }
    return None


def _check_stop_required(**kw):
    order = kw["order"]
    if not kw["limits"]["hard_rules"].get("require_stop_on_every_trade"):
        return None
    # Stops not required when order is part of a defined-risk structure.
    if order.get("structure_id") is not None:
        return None
    if not _has_stop(order):
        return {
            "rule": "missing_stop",
            "reason": "Every outright order must include a stop price.",
        }
    return None


def _proposed_worst_case_usd(order: dict, symbols: dict, limits: dict,
                              snap: dict | None) -> float:
    """Conservative USD loss if this order's stop is hit.

    Resolution order:
      1. Defined-risk structure → structures.max_loss_usd (authoritative)
      2. limit_price + stop_price + symbols.yaml tick metadata
      3. Fallback: per_trade_risk_pct_of_equity × balance
      4. Last resort: 0 (lets the trade through; other checks must catch)

    Returned value is positive (USD at risk). Caller subtracts from day P&L.
    """
    sid = order.get("structure_id")
    if sid is not None:
        try:
            row = get_db().connect().execute(
                "SELECT max_loss_usd FROM structures WHERE id = ?", (sid,)
            ).fetchone()
            if row and row["max_loss_usd"] is not None:
                return abs(float(row["max_loss_usd"]))
        except Exception:
            pass

    sym = (order.get("symbol") or "").upper()
    meta = symbols.get(sym, {}) if symbols else {}
    tick_size = float(meta.get("tick_size") or 0)
    tick_value = float(meta.get("tick_value") or 0)
    stop = order.get("stop_price")
    entry = order.get("limit_price")
    qty = int(order.get("qty") or 0)
    if (tick_size > 0 and tick_value > 0 and stop is not None and entry is not None
            and qty > 0):
        try:
            points = abs(float(entry) - float(stop))
            return (points / tick_size) * tick_value * qty
        except Exception:
            pass

    # Fallback: per_trade_risk_pct_of_equity × balance
    if snap and snap.get("balance_usd"):
        try:
            pct = float(
                (limits.get("account") or {}).get("per_trade_risk_pct_of_equity", 0)
            )
            return float(snap["balance_usd"]) * pct
        except Exception:
            pass
    return 0.0


def _check_daily_loss_limit(**kw):
    """Effective DLL = TIGHTER of (pct * current balance) or Topstep USD cap.

    Now projects forward: if the proposed order's worst-case loss would push
    today's P&L past the DLL, BLOCK pre-trade. This catches the "we're at
    -$760 and a trade with $250 risk would push us to -$1010" case that
    state-only checks missed.
    """
    snap = kw["snap"]
    if snap is None:
        return None
    acct = kw["limits"]["account"]
    balance = float(snap["balance_usd"])
    pct_dll = float(acct.get("daily_loss_limit_pct", 0.02)) * balance
    usd_cap = float(acct.get("daily_loss_limit_usd", 0) or 0)
    effective_dll = min(pct_dll, usd_cap) if usd_cap > 0 else pct_dll
    realized = float(snap["realized_pl_day_usd"])
    unrealized = float(snap["unrealized_pl_usd"])
    day_pl = realized + unrealized
    if day_pl <= -effective_dll:
        return {
            "rule": "daily_loss_limit",
            "reason": (
                f"Day P&L {day_pl:+.2f} ≤ -{effective_dll:.2f} DLL "
                f"(2% of {balance:.2f} = {pct_dll:.2f}; Topstep cap {usd_cap:.2f})."
            ),
        }
    # Pre-trade projection: would the proposed worst case push us over?
    worst = _proposed_worst_case_usd(kw["order"], kw["symbols"], kw["limits"], snap)
    projected = day_pl - worst
    if projected <= -effective_dll:
        return {
            "rule": "daily_loss_limit_projected",
            "reason": (
                f"Proposed trade would push Day P&L to {projected:+.2f}, "
                f"breaching DLL of -{effective_dll:.2f} "
                f"(current {day_pl:+.2f}, worst-case loss ${worst:.2f})."
            ),
        }
    return None


def _check_trailing_drawdown(**kw):
    """TDD: block if current TDD breached, OR if proposed worst case would
    push trailing-DD past the limit."""
    snap = kw["snap"]
    if snap is None:
        return None
    tdd = float(kw["limits"]["account"]["trailing_drawdown_usd"])
    current_dd = float(snap["trailing_dd_usd"])
    if current_dd >= tdd:
        return {
            "rule": "trailing_drawdown",
            "reason": f"Trailing DD {current_dd:.2f} ≥ limit {tdd:.2f}.",
        }
    worst = _proposed_worst_case_usd(kw["order"], kw["symbols"], kw["limits"], snap)
    if (current_dd + worst) >= tdd:
        return {
            "rule": "trailing_drawdown_projected",
            "reason": (
                f"Proposed worst-case loss ${worst:.2f} on top of current TDD "
                f"${current_dd:.2f} would breach limit ${tdd:.2f}."
            ),
        }
    return None


def _check_per_symbol_limits(**kw):
    order = kw["order"]
    sym = order.get("symbol", "")
    per_sym = kw["limits"].get("per_symbol", {})
    rule = per_sym.get(sym, per_sym.get("default", {}))
    max_contracts = int(rule.get("max_contracts", 0) or 0)
    if max_contracts == 0:
        return None

    existing = sum(
        p["contracts"] for p in kw["positions"] if p["symbol"] == sym
    )
    proposed = int(order.get("qty", 0))
    if existing + proposed > max_contracts:
        return {
            "rule": "per_symbol_max_contracts",
            "reason": f"{sym}: {existing}+{proposed} > max {max_contracts}.",
        }
    return None


def _check_sector_and_basket_limits(**kw):
    order = kw["order"]
    sym = order.get("symbol", "")
    sym_meta = kw["symbols"].get(sym, {})
    sector = sym_meta.get("sector")
    sector_rule = kw["limits"].get("sector_limits", {}).get(sector, {})
    max_net = int(sector_rule.get("max_net_contracts", 0) or 0)
    if max_net == 0:
        return None
    # Net contracts in sector: longs - shorts.
    net = 0
    for p in kw["positions"]:
        meta = kw["symbols"].get(p["symbol"], {})
        if meta.get("sector") != sector:
            continue
        sign = 1 if p["side"] == "long" else -1
        net += sign * int(p["contracts"])
    proposed_sign = 1 if order.get("side") == "buy" else -1
    after = net + proposed_sign * int(order.get("qty", 0))
    if abs(after) > max_net:
        return {
            "rule": "sector_net_contracts",
            "reason": f"Sector {sector}: net {after} after fill > max {max_net}.",
        }
    return None


def _check_consistency_rule(**kw):
    """Topstep Combine 50%-consistency advisory.

    No single day should exceed 50% of total profit to date. Implemented
    as ADVISORY: emits a `warn`-severity risk_event when today's realized
    P&L would breach 50% of (history + today) total, but does not block.
    Risk Manager prompt-layer is expected to factor this into sizing.

    Rationale: the consistency rule applies at *payout* time, not pre-trade.
    Failure mode is "smaller payout / extended Combine", not "account blown",
    so a hard pre-trade block is the wrong tool. Promote to BLOCK after a
    Combine has actually been run through to payout.

    Pass conditions (no warn):
      - Net total profit ≤ 0 (rule does not bind)
      - Today's share ≤ 50% of net total
      - No historical rows yet (single-day Combine; warn would be noise)
    """
    snap = kw.get("snap")
    if not snap:
        return None
    today_realized = float(snap.get("realized_pl_day_usd") or 0.0)
    if today_realized <= 0:
        return None  # losing/flat day cannot breach the consistency cap

    db = get_db()
    today_utc = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    history_total = db.total_realized_to_date(exclude_day=today_utc)

    # No history → don't surface (too noisy on day 1 of a Combine)
    if history_total == 0 and not db.daily_pl_history(exclude_day=today_utc):
        return None

    grand_total = history_total + today_realized
    if grand_total <= 0:
        return None  # cap binds only when there's net profit to apportion

    cap_pct = float(
        (kw["limits"].get("account") or {}).get("consistency_cap_pct", 0.50)
    )
    today_share = today_realized / grand_total
    if today_share > cap_pct:
        # Advisory only — log warn-severity event so RM/CIO can see it,
        # but pass the order through. Returning None means no block.
        db.record_risk_event(
            severity="warn",
            rule="consistency_rule_advisory",
            agent=kw.get("agent"),
            detail={
                "today_realized_usd": round(today_realized, 2),
                "history_total_usd": round(history_total, 2),
                "grand_total_usd": round(grand_total, 2),
                "today_share_pct": round(today_share * 100, 2),
                "cap_pct": round(cap_pct * 100, 2),
                "note": ("Today's realized P&L exceeds Topstep consistency "
                         "cap. Risk Manager should reduce sizing or hold."),
            },
        )
    return None


def _check_options_structure_allowed(**kw):
    order = kw["order"]
    # For option-bearing orders, structure kind must be in the allowlist.
    # The execution trader sets `structure_kind` on the order for options.
    kind = order.get("structure_kind")
    if not kind:
        return None
    allowed = kw["limits"].get("options", {}).get("allowed_structures", [])
    if kind not in allowed:
        return {
            "rule": "options_structure_disallowed",
            "reason": f"Structure '{kind}' is not in the allowed list.",
        }
    return None


# ────────────────────────────────────────────────────────────────────
# NEW CHECKS (added 2026-04-29 per user "decrease mistakes" directive)
# ────────────────────────────────────────────────────────────────────

def _order_root(order: dict) -> str:
    """Extract trading root from order symbol or contract id."""
    sym = (order.get("symbol") or "").upper()
    if "." in sym:
        for part in sym.split("."):
            if part and part not in ("CON", "F", "US"):
                if len(part) <= 3 and part[-2:].isdigit():
                    continue
                return _normalize_root(part)
    return sym


def _order_strategy(order: dict) -> str | None:
    """Strategy name carried on the order (set by analyst proposal flow)."""
    return (order.get("strategy") or order.get("setup_name") or "").lower() or None


def _check_strategy_blacklist(**kw):
    """Block symbol+strategy combos in `risk_limits.yaml:strategy_blacklist`.

    These are encoded lessons promoted to RULE tier (n>=3 confirmations).
    Adding a row here is how the team operationalizes "we learned this
    pattern doesn't work" — e.g. ZN + opening_range_breakout after the
    2026-04-29 overnight loss.
    """
    blacklist = (kw["limits"].get("strategy_blacklist") or [])
    if not blacklist:
        return None
    sym = _order_root(kw["order"])
    strategy = _order_strategy(kw["order"])
    if not sym or not strategy:
        return None
    for entry in blacklist:
        if (str(entry.get("symbol", "")).upper() == sym
                and str(entry.get("strategy", "")).lower() == strategy):
            return {
                "rule": "strategy_blacklist",
                "reason": (f"{sym} + {strategy} is on the strategy blacklist. "
                           f"Reason: {entry.get('reason', 'no reason recorded')}. "
                           f"To override, remove the entry from "
                           f"config/risk_limits.yaml:strategy_blacklist."),
            }
    return None


def _check_active_lessons(**kw):
    """Closes the learning loop: scan vault/lessons/*.md for any RULE-tier
    lesson tagged with the current symbol that vetoes the proposal.

    A lesson file is considered a hard veto when it contains both:
      - `confidence: RULE` or `confidence: HARD` in its YAML front-matter
      - `applies_to_symbol: <SYM>` (or `applies_to_strategy: <STRAT>`)

    Lower tiers (ADVISORY/PATTERN) just emit an `info` risk_event for
    the Risk Manager to factor into sizing — they don't block.
    """
    from pathlib import Path
    lessons_dir = Path("vault/lessons")
    if not lessons_dir.exists():
        return None
    sym = _order_root(kw["order"])
    strategy = _order_strategy(kw["order"])
    if not sym:
        return None

    for lesson_file in lessons_dir.glob("*.md"):
        try:
            text = lesson_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Cheap front-matter parse — look for confidence + applies_to lines
        head = text[:2000].lower()
        confidence = None
        for tier in ("hard", "rule", "pattern", "advisory"):
            if f"confidence: {tier}" in head or f"confidence:{tier}" in head:
                confidence = tier
                break
        if confidence not in ("rule", "hard"):
            continue
        # Check applicability
        sym_match = (f"applies_to_symbol: {sym.lower()}" in head
                     or f"applies_to_symbol:{sym.lower()}" in head)
        strat_match = (strategy and
                       (f"applies_to_strategy: {strategy}" in head
                        or f"applies_to_strategy:{strategy}" in head))
        if not (sym_match or strat_match):
            continue
        return {
            "rule": "active_lesson_veto",
            "reason": (f"Lesson at {lesson_file} (confidence={confidence}) "
                       f"vetoes this trade. Read the file before proposing "
                       f"again. To override after review, downgrade the "
                       f"lesson's confidence tier."),
        }
    return None


def _check_post_stop_cooldown(**kw):
    """No new entries within `post_stop_cooldown_minutes` (default 15) of
    a stop-out. Anti-tilt rule — prevents revenge trading.

    Detection (typed signals only — no fragile LIKE matching):
      1. risk_events row with rule='stop_hit_observed' (preferred — emit one
         from the post-fill flow when a working stop order fills)
      2. decisions row with kind='stop_hit' (legacy fallback)

    To trigger this cooldown reliably, post-trade workers MUST call
    db.record_risk_event(severity='info', rule='stop_hit_observed', detail=...)
    when a stop is filled. Loose summary text no longer counts.
    """
    cfg = kw["limits"].get("anti_tilt", {})
    cooldown_min = int(cfg.get("post_stop_cooldown_minutes", 15))
    if cooldown_min <= 0:
        return None
    cutoff = (datetime.now(tz=timezone.utc) - timedelta(minutes=cooldown_min)
              ).isoformat(timespec="seconds")
    db = get_db()
    # Primary: typed risk_event
    row = db.connect().execute(
        "SELECT ts FROM risk_events "
        "WHERE rule = 'stop_hit_observed' AND ts >= ? "
        "ORDER BY id DESC LIMIT 1",
        (cutoff,),
    ).fetchone()
    if row:
        return {
            "rule": "post_stop_cooldown",
            "reason": (f"Last stop-out at {row[0]} — within {cooldown_min}-min "
                       f"cooldown window. Prevents tilt re-entry. Wait it out."),
        }
    # Legacy fallback: typed decisions kind (no LIKE match)
    row = db.connect().execute(
        "SELECT ts FROM decisions "
        "WHERE kind = 'stop_hit' AND ts >= ? "
        "ORDER BY id DESC LIMIT 1",
        (cutoff,),
    ).fetchone()
    if row:
        return {
            "rule": "post_stop_cooldown",
            "reason": (f"Last stop-out at {row[0]} — within {cooldown_min}-min "
                       f"cooldown window (legacy decisions kind). Wait it out."),
        }
    return None


def _check_high_impact_blackout(**kw):
    """Pre/post blackout around high-impact economic releases.

    Reads `risk_limits.yaml:sessions.high_impact_blackout_minutes` (default 5).
    Reads upcoming/recent events from `vault/economic_calendar/today.json` if
    present (written by `scripts/build_economic_calendar.py`).

    Freshness: file mtime older than 36h emits a warn risk_event (nightly
    build didn't run); the check still proceeds with whatever events exist.

    File format expected:
      [{"ts_utc": "2026-04-29T12:30:00Z", "impact": "high", "event": "CPI"}, ...]
    """
    cfg = kw["limits"].get("sessions", {})
    minutes = int(cfg.get("high_impact_blackout_minutes", 0))
    if minutes <= 0:
        return None
    from pathlib import Path
    cal_path = Path("vault/economic_calendar/today.json")
    if not cal_path.exists():
        return None
    from datetime import datetime, timedelta, timezone
    now = datetime.now(tz=timezone.utc)
    # Freshness check — only warn once per session (deduped via risk_events).
    try:
        mtime = datetime.fromtimestamp(cal_path.stat().st_mtime, tz=timezone.utc)
        age_h = (now - mtime).total_seconds() / 3600
        if age_h > 36:
            db = get_db()
            recent = db.connect().execute(
                "SELECT COUNT(*) FROM risk_events "
                "WHERE rule = 'economic_calendar_stale' "
                "AND ts >= ?",
                ((now - timedelta(hours=12)).isoformat(timespec="seconds"),),
            ).fetchone()[0]
            if recent == 0:
                db.record_risk_event(
                    severity="warn", rule="economic_calendar_stale",
                    agent=kw.get("agent"),
                    detail={"path": str(cal_path), "age_hours": round(age_h, 1),
                            "note": "Run scripts/build_economic_calendar.py."},
                )
    except Exception:
        pass
    try:
        import json
        events = json.loads(cal_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    today_utc = now.strftime("%Y-%m-%d")
    window = timedelta(minutes=minutes)
    for ev in (events or []):
        if str(ev.get("impact", "")).lower() != "high":
            continue
        ts_str = str(ev.get("ts_utc", ""))
        # Filter out stale events from prior days that didn't get cleaned up.
        if not ts_str.startswith(today_utc):
            continue
        try:
            ev_ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            continue
        if abs((now - ev_ts).total_seconds()) <= window.total_seconds():
            return {
                "rule": "high_impact_blackout",
                "reason": (f"High-impact event '{ev.get('event','unknown')}' at "
                           f"{ev['ts_utc']} is within ±{minutes} min of now. "
                           f"Wait for the tape to settle."),
            }
    return None


def _check_daily_target_lock(**kw):
    """Profit lock-in: tighten / pause as day P&L crosses target thresholds.

    Reads `risk_limits.yaml:combine_pacing`:
      daily_soft_target_usd: at +$X day P&L, raise R:R floor (logged, not blocked)
      daily_hard_target_usd: at +$Y day P&L, BLOCK new entries (manage book only)
      partial_giveback_pct:  at giveback >= Z% of peak day P&L, lockdown

    The Combine math: 50% consistency rule punishes asymmetric days. The
    rational play after a profitable morning is lock-it-in, not hunt more.
    """
    pacing = kw["limits"].get("combine_pacing", {})
    if not pacing:
        return None
    snap = kw.get("snap")
    if not snap:
        return None
    day_pl = float(snap.get("realized_pl_day_usd") or 0.0)

    hard = float(pacing.get("daily_hard_target_usd", 0) or 0)
    if hard > 0 and day_pl >= hard:
        return {
            "rule": "daily_target_lock_hard",
            "reason": (f"Day P&L ${day_pl:.2f} >= hard target ${hard:.2f}. "
                       f"No new entries — manage existing book only. "
                       f"Combine consistency rule discourages giving it back."),
        }
    # Giveback check — needs the day's intraday peak; defensive ladder
    # tracks this when track_intraday_peak is on. We approximate with the
    # max `realized_pl_day_usd` seen in account_snapshots today.
    pct = float(pacing.get("partial_giveback_pct", 0) or 0)
    if pct > 0:
        from datetime import datetime, timezone
        today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
        db = get_db()
        row = db.connect().execute(
            "SELECT MAX(realized_pl_day_usd) FROM account_snapshots WHERE ts LIKE ?",
            (f"{today}%",),
        ).fetchone()
        peak = float(row[0]) if row and row[0] is not None else 0.0
        if peak > 50 and day_pl < peak * (1 - pct):
            return {
                "rule": "daily_target_lock_giveback",
                "reason": (f"Day P&L ${day_pl:.2f} has given back >{pct:.0%} "
                           f"from peak ${peak:.2f}. Lockdown — protect what's left."),
            }
    return None
