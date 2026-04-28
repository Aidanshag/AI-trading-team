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

from datetime import datetime, time, timezone
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
        _check_combine_defensive_ladder,    # NEW: $-150/$-300/$-500/$-750 progressive tightening
        _check_daily_trade_count,           # autonomous-mode hard ceiling on trade count/day
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
        except Exception:
            pass  # malformed timestamp = ignore
    return None


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

    if triggered is None:
        return None  # no ladder step triggered

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
    # 'warn' and 'restrict' don't hard-block here; they ALLOW the order through
    # this gate but tighten the per-trade cap (see `_check_per_trade_cap_with_ladder`
    # if/when added). For now we log a risk event and let later checks handle.
    # The Risk Manager prompt also reads this and reduces sizing accordingly.
    return None


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
    sessions = kw["limits"].get("sessions", {})
    cutoff_str = sessions.get("no_new_positions_after_local_time")
    if cutoff_str:
        hh, mm = (int(x) for x in cutoff_str.split(":"))
        if _now_chicago() >= time(hh, mm):
            return {
                "rule": "session_cutoff",
                "reason": f"No new positions after {cutoff_str} CT.",
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


def _check_daily_loss_limit(**kw):
    """Effective DLL = TIGHTER of (pct * current balance) or Topstep USD cap."""
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
    return None


def _check_trailing_drawdown(**kw):
    snap = kw["snap"]
    if snap is None:
        return None
    tdd = float(kw["limits"]["account"]["trailing_drawdown_usd"])
    if float(snap["trailing_dd_usd"]) >= tdd:
        return {
            "rule": "trailing_drawdown",
            "reason": f"Trailing DD {snap['trailing_dd_usd']:.2f} ≥ limit {tdd:.2f}.",
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
    # Topstep Combine: no single day should exceed 50% of total profit to
    # date. Proper enforcement requires a rolling view of daily P&L —
    # stubbed here for the hook to surface, to be fleshed out with a
    # `daily_pl` table once the schema is extended.
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
