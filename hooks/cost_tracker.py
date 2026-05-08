"""Stop hook — rolls up token usage per (day, agent, model) into state.costs.

Runs at the end of each agent wake-cycle (`Stop` event in the Agent SDK).
The orchestrator passes total tokens via context metadata.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from state.db import get_db

# Rough USD-per-million-token prices (illustrative; update from
# anthropic.com/pricing periodically).
PRICES = {
    "claude-haiku-4-5-20251001": {"in": 1.00, "out": 5.00, "cache_in": 0.10},
    "claude-sonnet-4-6":         {"in": 3.00, "out": 15.00, "cache_in": 0.30},
    "claude-opus-4-7":           {"in": 15.00, "out": 75.00, "cache_in": 1.50},
}


def _usd(model: str, t_in: int, t_out: int, t_cached: int) -> float:
    p = PRICES.get(model, {"in": 3.0, "out": 15.0, "cache_in": 0.3})
    return (
        (t_in - t_cached) * p["in"] / 1_000_000
        + t_cached * p["cache_in"] / 1_000_000
        + t_out * p["out"] / 1_000_000
    )


async def cost_tracker(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    agent = getattr(context, "agent_name", "unknown")
    model = getattr(context, "model", "unknown")
    meta = input_data.get("usage", {}) or {}
    t_in = int(meta.get("input_tokens", 0))
    t_out = int(meta.get("output_tokens", 0))
    t_cached = int(meta.get("cache_read_input_tokens", 0))
    if t_in == 0 and t_out == 0:
        return {}

    day = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    usd = _usd(model, t_in, t_out, t_cached)
    db = get_db()
    with db.tx() as c:
        c.execute(
            """INSERT INTO costs (day, agent, model, tokens_in, tokens_out, cached_in, usd_est)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(day, agent, model) DO UPDATE SET
                   tokens_in  = tokens_in  + excluded.tokens_in,
                   tokens_out = tokens_out + excluded.tokens_out,
                   cached_in  = cached_in  + excluded.cached_in,
                   usd_est    = usd_est    + excluded.usd_est""",
            (day, agent, model, t_in, t_out, t_cached, usd),
        )
    return {}
