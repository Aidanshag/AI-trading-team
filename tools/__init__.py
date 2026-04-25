"""MCP tool servers exposed to the fund's agents.

Each module defines a `server` object (a `create_sdk_mcp_server` result) and
a list of tool callables. The orchestrator wires them into each agent's
ClaudeAgentOptions.
"""
