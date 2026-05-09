"""Equity broker MCP server — STUB, INTENTIONALLY IDLE.

The equities desk is not live. This module exposes *no tools at all* until a
broker is chosen and wired. The equity execution trader agent will have no
order-placement tools in its allowlist; any attempt to route an order
through the equities path will fail at the orchestrator, not here.

When you're ready to go live:

  1. Pick a broker (Alpaca recommended for paper; Tradier for options API;
     IBKR for full coverage).
  2. Implement the REST client against their paper endpoint.
  3. Add `place_order` / `cancel_order` / `get_positions` tools following
     the same shape as `tools/topstep.py`.
  4. Flip `trading:trading_enabled: true` in config/equities.yaml.
  5. Register this server in runtime/orchestrator.py alongside the others.
  6. Add the tool names to EXECUTION_ONLY_TOOLS.

Until then: this file's only job is to exist as a placeholder that makes
the broker-integration work obvious when the time comes.
"""

from __future__ import annotations

from claude_agent_sdk import create_sdk_mcp_server

# Empty tools list — intentional. Until we have a broker, there is no
# equity-order-placing capability anywhere in the process.
TOOLS: list = []

server = create_sdk_mcp_server(name="equity_broker", version="0.0.0-idle", tools=TOOLS)
