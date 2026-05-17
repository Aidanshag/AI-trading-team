"""signal_validators — pure signal/snapshot validation helpers.

Extracted from scripts/live_trader.py on 2026-05-17 per the standing
trader-trim directive. All functions here are PURE: they take a signal
dict (and/or snapshot dict) and config, return a (bool, str) verdict.
No broker IO, no global state mutation, no DB writes.

Both the trader (last-mile safety gates) and the brain (pre-emission
sanity checks) can import these without circular dependencies.

Defaults match scripts/live_trader.py's module-level constants so
the trader's behaviour doesn't change when callers don't override.
Future config-driven tweaks can be done by passing through explicit
arguments rather than mutating module-level globals.

2026-05-17 enhancement (session-aware MIN_STOP_TICKS): closes the
"open encoding gap" flagged in CLAUDE.md Pattern B section. Volume
thresholds and stop distances are NOT yet session-aware everywhere;
this module's MIN_SIGNAL_R_TICKS_BY_SESSION dict starts that work.
Asian session gets a tighter floor (4 ticks vs the 6-tick RTH/London
default) because Asian-session bars typically have 30-50% smaller true
range — applying the RTH calibration to Asian rejects valid signals.
"""
from __future__ import annotations

from tools.trader_utils import _load_yaml, _tick_size, _tick_value


# Module-level defaults — kept identical to the trader's constants so
# behaviour is byte-for-byte equivalent unless callers override.
DEFAULT_MAX_SIGNAL_RISK_USD: float = 150.0
DEFAULT_MIN_SIGNAL_R_TICKS: int = 6

# Session-aware MIN_SIGNAL_R_TICKS overrides. Asian session has tighter
# true ranges, so the RTH 6-tick floor over-rejects valid signals.
# Default for any session NOT listed: DEFAULT_MIN_SIGNAL_R_TICKS (6).
MIN_SIGNAL_R_TICKS_BY_SESSION: dict[str, int] = {
    "Asian": 4,      # ~30-50% tighter ranges → 4-tick floor (Pattern B fix)
    "London": 6,     # RTH-equivalent volatility
    "RTH": 6,        # baseline
    "PostClose": 5,  # between Asian and RTH; some events linger
}


def min_r_ticks_for_session(session: str | None) -> int:
    """Return the session-aware MIN_SIGNAL_R_TICKS for a given session label.
    Defaults to DEFAULT_MIN_SIGNAL_R_TICKS when session is missing or unknown."""
    if not session:
        return DEFAULT_MIN_SIGNAL_R_TICKS
    return MIN_SIGNAL_R_TICKS_BY_SESSION.get(session, DEFAULT_MIN_SIGNAL_R_TICKS)


# ────────────────────────────────────────────────────────────────
# DLL — daily-loss-limit gates
# ────────────────────────────────────────────────────────────────

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


# ────────────────────────────────────────────────────────────────
# Per-signal risk + R-distance gates
# ────────────────────────────────────────────────────────────────

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
                                  max_risk_usd: float = DEFAULT_MAX_SIGNAL_RISK_USD,
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


def signal_passes_min_r_gate(sig: dict, symbol: str,
                              min_r_ticks: int | None = None,
                              session: str | None = None,
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

    2026-05-17: `session` arg picks the right floor from
    MIN_SIGNAL_R_TICKS_BY_SESSION (Asian=4, others=6). If both `session`
    and `min_r_ticks` are passed, `min_r_ticks` wins (explicit override).
    If neither is passed, defaults to DEFAULT_MIN_SIGNAL_R_TICKS.
    """
    if min_r_ticks is None:
        min_r_ticks = min_r_ticks_for_session(session)
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
