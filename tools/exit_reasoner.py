"""LLM-based exit veto layer over profit_protect's mechanical tier rules.

WHY:
The mechanical tier system in `tools/profit_protect.py` answers
"should this position close?" using only PEAK unrealized $ and CURRENT
unrealized $. It can't tell whether:
  * A small retrace is structural reversal or normal noise
  * The strategy is in its "developmental" wiggle phase
  * News/event timing changes the signal

This module wraps that decision in a reasoning layer. When the tier
rule wants to close, we ask Haiku to look at recent bar action plus
trade lifecycle and decide: CLOSE this now, or HOLD and let it
develop?

CONSTRAINTS (non-overridable, hard-coded):
  * Agent can ONLY override profit_lock-tier closes — NOT the broker
    stop, NOT the LOSS_TIER_HARD_CAP_USD ($150), NOT the hard-flatten
    clock, NOT the daily profit cap. These remain mechanical.
  * Max consecutive HOLD overrides per position: 3 (after that, force
    CLOSE — agent can't indefinitely delay)
  * Max time-in-trade an agent can hold: 30 min from entry (after that
    the mechanical tier wins — assume agent is wrong about a long
    runner if it's been 30 min and the tier is still triggering)
  * Network failure / API error → fall back to CLOSE (rule wins)

USAGE (called from profit_protect.check_and_close):
    decision = decide_exit_with_agent(trade_state, bars, tier_proposal)
    if decision.action == "CLOSE":
        # proceed with market close as planned
    elif decision.action == "HOLD":
        # log the veto, skip close this iteration, re-evaluate next scan

Built 2026-05-12 per user direction toward reasoning-over-rules exits.
"""
from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

# Model and prompt constants
AGENT_MODEL = "claude-haiku-4-5-20251001"
MAX_OUTPUT_TOKENS = 400
TIMEOUT_SECONDS = 8.0

# Hard limits on agent authority
MAX_CONSECUTIVE_HOLDS = 3
MAX_AGENT_HOLD_DURATION_SECONDS = 30 * 60   # 30 minutes from trade entry
MIN_PEAK_USD_TO_INVOKE_AGENT = 15.0          # if peak < $15, just use the rule
# Above this peak, mechanical tiers stay in charge regardless of agent.
# This is the "user-requested upper-tier mechanical backstop" — big runners
# stay protected by the runner-zone trailing tiers ((750, 400) → (10000, 6500))
# even if the agent malfunctions.
MAX_PEAK_USD_FOR_AGENT = 750.0

# Circuit breaker: if more than CIRCUIT_BREAKER_THRESHOLD API failures
# occur within CIRCUIT_BREAKER_WINDOW_SECONDS, auto-disable the agent for
# CIRCUIT_BREAKER_COOLDOWN_SECONDS. The simulator/trader falls back to
# pure mechanical tiers during the cooldown.
CIRCUIT_BREAKER_THRESHOLD = 3
CIRCUIT_BREAKER_WINDOW_SECONDS = 5 * 60
CIRCUIT_BREAKER_COOLDOWN_SECONDS = 30 * 60

# Process-local circuit breaker state. Resets on trader restart.
_recent_failure_timestamps: list[float] = []
_breaker_tripped_at: Optional[float] = None


@dataclass
class TradeContext:
    """Everything the agent needs to reason about an exit."""
    symbol: str
    side: str                  # long | short
    strategy: str | None
    contract_id: str | None
    entry_price: float
    entry_ts: datetime
    avg_fill_price: float
    current_price: float
    peak_unrealized_usd: float
    current_unrealized_usd: float
    tier_floor_usd: float       # the floor the tier rule wants to close at
    risk_usd: float
    recent_bars: list[dict]     # latest ~20 1-min bars, oldest first
    regime: dict                # output of current_regime() — vol, trend, news_proximity
    consecutive_holds: int = 0  # how many times agent has already held this position


@dataclass
class ExitDecision:
    """Agent's answer (or fallback if API unreachable)."""
    action: str                 # CLOSE | HOLD | FALLBACK_CLOSE
    reason: str
    confidence: str = "low"     # low | medium | high
    agent_model: str | None = None
    response_ms: int | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


def _format_bars_for_prompt(bars: list[dict], max_bars: int = 20) -> str:
    """One bar per line: ts O/H/L/C."""
    lines = []
    for b in bars[-max_bars:]:
        ts = b.get("t") or b.get("ts") or b.get("time") or "?"
        if hasattr(ts, "isoformat"):
            ts = ts.isoformat(timespec="minutes")
        elif isinstance(ts, str) and len(ts) > 16:
            ts = ts[:16]
        o = b.get("o") or b.get("open")
        h = b.get("h") or b.get("high")
        l = b.get("l") or b.get("low")
        c = b.get("c") or b.get("close")
        lines.append(f"  {ts}  O={o}  H={h}  L={l}  C={c}")
    return "\n".join(lines)


def _build_prompt(ctx: TradeContext) -> str:
    seconds_in_trade = int((datetime.now(tz=timezone.utc) - ctx.entry_ts)
                            .total_seconds())
    minutes_in_trade = seconds_in_trade // 60
    peak_to_current_drop = ctx.peak_unrealized_usd - ctx.current_unrealized_usd

    regime_str = (
        f"vol_regime={ctx.regime.get('vol_regime', '?')}, "
        f"trend_regime={ctx.regime.get('trend_regime', '?')}, "
        f"news_proximity={ctx.regime.get('news_proximity', '?')}"
    )

    return f"""You are an experienced futures trader managing an open position.
The mechanical trailing-profit-lock wants to close this trade RIGHT NOW.
Your job: decide whether to follow that or HOLD and let the trade develop.

POSITION
  Symbol:        {ctx.symbol}
  Side:          {ctx.side}
  Strategy:      {ctx.strategy or 'unknown'}
  Entry:         ${ctx.avg_fill_price} ({minutes_in_trade}min ago)
  Current price: ${ctx.current_price}

P&L
  Peak unrealized:    ${ctx.peak_unrealized_usd:+.2f}
  Current unrealized: ${ctx.current_unrealized_usd:+.2f}
  Drop from peak:     ${peak_to_current_drop:+.2f}
  Tier wants to close at floor: ${ctx.tier_floor_usd:+.2f}
  Risk on the trade (1R): ${ctx.risk_usd:.2f}

REGIME
  {regime_str}

RECENT BARS (1-min, oldest first):
{_format_bars_for_prompt(ctx.recent_bars)}

STATE
  Consecutive HOLDs so far on this position: {ctx.consecutive_holds} (max 3)

YOUR JOB
The mechanical rule says "close at the floor — protect the gain." But mechanical
rules don't see the trade's character. Look at the recent bars and ask:
  * Is the retrace a structural reversal (lower-highs, volume capitulation,
    range breakdown)? → CLOSE is right.
  * Is the retrace normal noise (consolidation, wick at support, normal pullback
    in trend)? → HOLD lets the trade reach its actual target.
  * If unsure, defer to the rule — CLOSE.

You are the LAST line of defense for letting a real winner run, but you must
NEVER hold a trade that's structurally reversing. Bias toward CLOSE if the bars
look weak or if you can't see a clear "this is normal noise" signature.

Respond in EXACTLY this format (3 lines, no other text):
DECISION: CLOSE|HOLD
CONFIDENCE: low|medium|high
REASON: <one sentence, max 200 chars>
"""


def _parse_agent_response(text: str) -> tuple[str, str, str]:
    """Returns (decision, confidence, reason). Defaults to CLOSE on parse fail."""
    decision = "CLOSE"
    confidence = "low"
    reason = ""
    for line in text.strip().splitlines():
        line = line.strip()
        if line.upper().startswith("DECISION:"):
            val = line.split(":", 1)[1].strip().upper()
            if val in ("CLOSE", "HOLD"):
                decision = val
        elif line.upper().startswith("CONFIDENCE:"):
            val = line.split(":", 1)[1].strip().lower()
            if val in ("low", "medium", "high"):
                confidence = val
        elif line.upper().startswith("REASON:"):
            reason = line.split(":", 1)[1].strip()[:200]
    if not reason:
        reason = "agent_parse_no_reason"
    return decision, confidence, reason


def _call_agent(prompt: str) -> tuple[str, dict]:
    """Call Anthropic API. Returns (decision_text, meta). Raises on failure."""
    import anthropic
    client = anthropic.Anthropic(timeout=TIMEOUT_SECONDS)
    t0 = time.time()
    resp = client.messages.create(
        model=AGENT_MODEL,
        max_tokens=MAX_OUTPUT_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )
    elapsed_ms = int((time.time() - t0) * 1000)
    text = "".join(b.text for b in resp.content if hasattr(b, "text"))
    meta = {
        "elapsed_ms": elapsed_ms,
        "input_tokens": resp.usage.input_tokens if resp.usage else None,
        "output_tokens": resp.usage.output_tokens if resp.usage else None,
        "model": AGENT_MODEL,
    }
    return text, meta


def _log_veto(con: sqlite3.Connection, ctx: TradeContext,
               decision: ExitDecision) -> int:
    """Insert agent_exit_vetoes row. Returns the row id."""
    cur = con.cursor()
    cur.execute(
        """INSERT INTO agent_exit_vetoes
           (ts, contract_id, symbol, side, strategy,
            tier_floor_usd, peak_unrealized_usd, current_unrealized_usd,
            time_in_trade_seconds, consecutive_holds,
            decision, confidence, reason,
            agent_model, agent_response_ms,
            prompt_tokens, completion_tokens)
           VALUES (?,?,?,?,?, ?,?,?, ?,?, ?,?,?, ?,?, ?,?)""",
        (
            datetime.now(tz=timezone.utc).isoformat(),
            ctx.contract_id, ctx.symbol, ctx.side, ctx.strategy,
            ctx.tier_floor_usd, ctx.peak_unrealized_usd, ctx.current_unrealized_usd,
            int((datetime.now(tz=timezone.utc) - ctx.entry_ts).total_seconds()),
            ctx.consecutive_holds,
            decision.action, decision.confidence, decision.reason,
            decision.agent_model, decision.response_ms,
            decision.prompt_tokens, decision.completion_tokens,
        ),
    )
    con.commit()
    return cur.lastrowid


def _circuit_breaker_is_open(log_fn: Callable[[str], None] | None = None) -> bool:
    """Check / advance the circuit breaker state.

    Returns True if the breaker is currently open (agent should be
    bypassed). The breaker trips when CIRCUIT_BREAKER_THRESHOLD failures
    happen within CIRCUIT_BREAKER_WINDOW_SECONDS, and re-closes after
    CIRCUIT_BREAKER_COOLDOWN_SECONDS.
    """
    global _breaker_tripped_at
    now = time.time()
    log = log_fn if log_fn is not None else (lambda _msg: None)

    if _breaker_tripped_at is not None:
        if now - _breaker_tripped_at < CIRCUIT_BREAKER_COOLDOWN_SECONDS:
            return True
        # Cooldown elapsed → close the breaker, clear failures
        _breaker_tripped_at = None
        _recent_failure_timestamps.clear()
        log("  exit_reasoner: circuit breaker closed after cooldown")
    return False


def _record_failure(log_fn: Callable[[str], None] | None = None) -> None:
    """Record an API failure. Trips the breaker if threshold exceeded."""
    global _breaker_tripped_at
    now = time.time()
    log = log_fn if log_fn is not None else (lambda _msg: None)
    _recent_failure_timestamps.append(now)
    # Prune failures outside the window
    cutoff = now - CIRCUIT_BREAKER_WINDOW_SECONDS
    _recent_failure_timestamps[:] = [t for t in _recent_failure_timestamps
                                       if t >= cutoff]
    if (_breaker_tripped_at is None
            and len(_recent_failure_timestamps) >= CIRCUIT_BREAKER_THRESHOLD):
        _breaker_tripped_at = now
        log(f"  exit_reasoner: CIRCUIT BREAKER TRIPPED — {len(_recent_failure_timestamps)} "
             f"failures in {CIRCUIT_BREAKER_WINDOW_SECONDS}s. Bypassing agent "
             f"for {CIRCUIT_BREAKER_COOLDOWN_SECONDS}s.")


def decide_exit_with_agent(
    ctx: TradeContext,
    *,
    db_conn: Optional[sqlite3.Connection] = None,
    log_fn: Callable[[str], None] | None = None,
    enabled: bool = True,
) -> ExitDecision:
    """Main entry point. Returns ExitDecision the trader should act on.

    Args:
        ctx: the trade context the rule wants to close
        db_conn: optional DB connection for logging the veto
        log_fn: optional logger for free-form messages
        enabled: feature flag; False = always return CLOSE (use the rule)

    Returns:
        ExitDecision(action=CLOSE|HOLD|FALLBACK_CLOSE, ...)
    """
    log = log_fn if log_fn is not None else (lambda _msg: None)

    if not enabled:
        d = ExitDecision(action="CLOSE", reason="agent_disabled_by_flag")
        if db_conn is not None:
            _log_veto(db_conn, ctx, d)
        return d

    # ── Circuit breaker (emergency backup #1) ──
    if _circuit_breaker_is_open(log):
        d = ExitDecision(action="CLOSE",
                          reason="circuit_breaker_open_from_recent_api_failures")
        if db_conn is not None:
            _log_veto(db_conn, ctx, d)
        return d

    # ── Authority guards (never reach the model) ──
    if ctx.consecutive_holds >= MAX_CONSECUTIVE_HOLDS:
        d = ExitDecision(action="CLOSE",
                          reason=f"max_consecutive_holds_reached({MAX_CONSECUTIVE_HOLDS})")
        if db_conn is not None: _log_veto(db_conn, ctx, d)
        return d

    seconds_in_trade = (datetime.now(tz=timezone.utc) - ctx.entry_ts).total_seconds()
    if seconds_in_trade >= MAX_AGENT_HOLD_DURATION_SECONDS:
        d = ExitDecision(action="CLOSE",
                          reason=f"time_in_trade_{int(seconds_in_trade)}s_exceeds_agent_authority")
        if db_conn is not None: _log_veto(db_conn, ctx, d)
        return d

    if ctx.peak_unrealized_usd < MIN_PEAK_USD_TO_INVOKE_AGENT:
        d = ExitDecision(action="CLOSE",
                          reason=f"peak_{ctx.peak_unrealized_usd:.0f}_below_agent_threshold")
        if db_conn is not None: _log_veto(db_conn, ctx, d)
        return d

    if ctx.peak_unrealized_usd > MAX_PEAK_USD_FOR_AGENT:
        d = ExitDecision(action="CLOSE",
                          reason=f"peak_{ctx.peak_unrealized_usd:.0f}_above_runner_tier_authority")
        if db_conn is not None: _log_veto(db_conn, ctx, d)
        return d

    # ── Call the agent ──
    prompt = _build_prompt(ctx)
    try:
        text, meta = _call_agent(prompt)
    except Exception as e:
        log(f"  exit_reasoner: API call failed → fallback close: {type(e).__name__}: {e}")
        _record_failure(log)   # may trip the circuit breaker
        d = ExitDecision(action="FALLBACK_CLOSE",
                          reason=f"api_error:{type(e).__name__}",
                          agent_model=AGENT_MODEL)
        if db_conn is not None: _log_veto(db_conn, ctx, d)
        return d

    decision, confidence, reason = _parse_agent_response(text)
    d = ExitDecision(
        action=decision, reason=reason, confidence=confidence,
        agent_model=meta["model"],
        response_ms=meta["elapsed_ms"],
        prompt_tokens=meta["input_tokens"],
        completion_tokens=meta["output_tokens"],
    )
    log(f"  exit_reasoner: {ctx.symbol} {ctx.side} peak=${ctx.peak_unrealized_usd:.0f} "
        f"cur=${ctx.current_unrealized_usd:+.0f} → {decision} ({confidence}): {reason}")
    if db_conn is not None:
        _log_veto(db_conn, ctx, d)
    return d
