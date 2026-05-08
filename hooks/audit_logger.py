"""PostToolUse audit logger — appends a line to logs/audit.jsonl for every
tool call (order, read, or otherwise). Complements the SQL decision log with
a raw firehose for later forensic replay.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LOG_PATH = Path("logs/audit.jsonl")


async def audit_logger(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: Any,
) -> dict[str, Any]:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "tool_use_id": tool_use_id,
        "tool_name": input_data.get("tool_name"),
        "tool_input": input_data.get("tool_input"),
        "tool_response": input_data.get("tool_response"),
        "agent": getattr(context, "agent_name", None),
    }
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")
    return {}
