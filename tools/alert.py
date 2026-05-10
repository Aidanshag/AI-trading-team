"""Discord alert sender for trader death/restart notifications.

Reads DISCORD_WEBHOOK_URL from environment (auto-loads .env if present).
Silently no-ops when the webhook is unset, so importing this module is
always safe regardless of configuration.

Usage:
    from tools.alert import send_alert
    send_alert("trader restarted at 06:30 ET", level="warn")

CLI:
    python -m tools.alert "test message"
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"

_LEVEL_PREFIX = {
    "info": ":information_source:",
    "warn": ":warning:",
    "crit": ":rotating_light:",
}


def _load_dotenv() -> None:
    """Lightweight .env reader. Avoids the python-dotenv dependency.
    Already-set env vars take precedence (so explicit env overrides .env)."""
    if not _ENV_FILE.exists():
        return
    try:
        for raw in _ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


def send_alert(message: str, level: str = "info") -> bool:
    """POST a message to the Discord webhook.

    Returns True on success, False if no webhook configured or send failed.
    Never raises — alert failures must not break the caller.
    """
    _load_dotenv()
    webhook = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        return False

    prefix = _LEVEL_PREFIX.get(level, "")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    content = f"{prefix} `{ts}` {message}"[:1900]

    body = json.dumps({"content": content, "username": "fund-alert"}).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "fund-alert/1.0"},
    )
    try:
        urllib.request.urlopen(req, timeout=10).read()
        return True
    except Exception:
        return False


def main() -> int:
    msg = " ".join(sys.argv[1:]) or "test alert"
    level = "info"
    # crude flag: --level=warn / --level=crit
    for i, a in enumerate(sys.argv):
        if a.startswith("--level="):
            level = a.split("=", 1)[1]
    ok = send_alert(msg, level=level)
    print(f"send_alert ok={ok} (webhook_set={bool(os.environ.get('DISCORD_WEBHOOK_URL'))})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
