"""Real-time loss alerter — push notifications when day P&L crosses thresholds.

Reads `DISCORD_WEBHOOK_URL` and/or `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`
from .env. If both are empty, this is a no-op (logs only).

Thresholds (configurable in risk_limits.yaml:loss_alerts):
  -$100 → soft warn (info)
  -$200 → loud (warn)
  -$400 → critical (urgent)
  canTrade=false → emergency

Each level fires AT MOST ONCE per UTC day. Dedupe via the risk_events table.

Wire into runtime/orchestrator.py:tick_workflow OR call directly from
scripts.auto_trader.scan_once after each snapshot.

Why this is the highest-leverage Phase-2 fix: today's incident bled for 5
hours unnoticed. A push alert at -$200 would have woken the user up.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx

from state.db import get_db


# Default thresholds — can be overridden in risk_limits.yaml:loss_alerts
DEFAULT_THRESHOLDS = [
    (-100, "info",      "soft"),
    (-200, "warn",      "LOUD"),
    (-400, "block",     "CRITICAL"),
]


def _format_message(level: str, day_pl: float, balance: float,
                    extra: str = "") -> str:
    """Slack/Discord/Telegram-friendly message."""
    icon = {
        "soft": "🟡",
        "LOUD": "🟠",
        "CRITICAL": "🔴",
        "EMERGENCY": "🚨",
    }.get(level, "ℹ️")
    msg = (f"{icon} **{level} ALERT** — Trading Fund\n"
           f"Day P&L: **${day_pl:+.2f}**\n"
           f"Balance: ${balance:.2f}\n"
           f"Time: {datetime.now(tz=timezone.utc).isoformat(timespec='seconds')}")
    if extra:
        msg += f"\n{extra}"
    return msg


def _post_discord(webhook_url: str, message: str) -> bool:
    """Fire a Discord webhook. Returns True on success."""
    try:
        r = httpx.post(webhook_url, json={"content": message}, timeout=10)
        return 200 <= r.status_code < 300
    except Exception as e:
        print(f"  [loss_alerter] discord post failed: {e}")
        return False


def _post_telegram(bot_token: str, chat_id: str, message: str) -> bool:
    """Fire a Telegram message via the bot API."""
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = httpx.post(url, json={"chat_id": chat_id, "text": message,
                                  "parse_mode": "Markdown"}, timeout=10)
        return 200 <= r.status_code < 300
    except Exception as e:
        print(f"  [loss_alerter] telegram post failed: {e}")
        return False


def _already_fired_today(level: str) -> bool:
    """Check risk_events for an alert at this level today."""
    db = get_db()
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    row = db.connect().execute(
        "SELECT 1 FROM risk_events "
        "WHERE rule = ? AND ts LIKE ? LIMIT 1",
        (f"loss_alert_{level.lower()}", f"{today}%"),
    ).fetchone()
    return row is not None


def _record_alert(level: str, detail: dict[str, Any]) -> None:
    """Mark this alert as fired so we don't spam."""
    get_db().record_risk_event(
        severity="warn", rule=f"loss_alert_{level.lower()}",
        agent="loss_alerter", detail=detail,
    )


def check_and_alert(*, balance: float, day_pl: float,
                    can_trade: bool = True) -> dict:
    """Evaluate thresholds and fire any new-this-session alerts.

    Returns a summary dict with what was fired (or skipped).
    """
    summary = {"fired": [], "skipped_already_fired": [], "skipped_no_webhook": False}

    discord_url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    has_webhook = bool(discord_url) or (bool(tg_token) and bool(tg_chat))

    # Emergency: canTrade=false (always fires, regardless of P&L)
    if not can_trade and not _already_fired_today("emergency"):
        msg = _format_message("EMERGENCY", day_pl, balance,
                              extra="Topstep flipped canTrade=false. Account locked.")
        if has_webhook:
            ok = (_post_discord(discord_url, msg) if discord_url else True) and \
                 (_post_telegram(tg_token, tg_chat, msg) if tg_token else True)
        else:
            print(f"  [loss_alerter NO WEBHOOK] {msg}".encode('ascii', 'replace').decode('ascii'))
            ok = True
        if ok:
            _record_alert("emergency", {"day_pl": day_pl, "balance": balance})
            summary["fired"].append("emergency")
        if not has_webhook:
            summary["skipped_no_webhook"] = True
        return summary

    # P&L-threshold alerts
    for threshold, severity, label in DEFAULT_THRESHOLDS:
        if day_pl > threshold:
            continue  # not yet at this level
        if _already_fired_today(label):
            summary["skipped_already_fired"].append(label)
            continue
        msg = _format_message(label, day_pl, balance)
        if has_webhook:
            ok = (_post_discord(discord_url, msg) if discord_url else True) and \
                 (_post_telegram(tg_token, tg_chat, msg) if tg_token else True)
        else:
            print(f"  [loss_alerter NO WEBHOOK] {msg}".encode('ascii', 'replace').decode('ascii'))
            ok = True
        if ok:
            _record_alert(label, {"day_pl": day_pl, "balance": balance,
                                   "threshold": threshold})
            summary["fired"].append(label)
    if not has_webhook:
        summary["skipped_no_webhook"] = True
    return summary


def main() -> int:
    """CLI entry — pull latest snapshot and check thresholds.
    Useful for testing: `python -m scripts.loss_alerter`.
    Real-time use: call from auto_trader.scan_once after each snapshot.
    """
    from dotenv import load_dotenv
    load_dotenv()
    snap = get_db().latest_account_snapshot()
    if not snap:
        print("No snapshot — nothing to evaluate.")
        return 1
    result = check_and_alert(
        balance=float(snap["balance_usd"]),
        day_pl=float(snap["realized_pl_day_usd"]) + float(snap["unrealized_pl_usd"]),
        can_trade=bool(snap.get("can_trade", 1)),
    )
    print(f"loss_alerter: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
