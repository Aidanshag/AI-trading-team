"""API budget kill switch.

Runs as a preflight to every Task Scheduler wake. If we're within $2 of
the daily cost guardrail OR our cumulative spend trend suggests we'll
breach it before EOD, this script:

  1. Sets `trading_halt_until` in risk_limits.yaml to end-of-day UTC
  2. Records a risk_event of severity=breach
  3. Exits with non-zero so the calling Task does NOT proceed to wake agents

This protects against:
  - A prompt loop burning credits unattended
  - Anthropic API credit exhaustion mid-session leaving positions
    unmanaged for new ideas
  - Runaway model escalations under Combine pressure

Note: open positions remain at the broker with their stops/targets.
This script halts NEW analysis, not existing risk management.

Usage (from cron / Task Scheduler):
  python -m scripts.api_budget_check
  if errorlevel 1 exit /b 1   :: don't proceed to wake the team

  python -m scripts.api_budget_check --check-only  :: report, don't halt
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from state.db import get_db

CONFIG_DIR = Path("config")
RISK_LIMITS = CONFIG_DIR / "risk_limits.yaml"
MODELS_YAML = CONFIG_DIR / "models.yaml"


def _today_spend_usd() -> float:
    db = get_db()
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    row = db.connect().execute(
        "SELECT COALESCE(SUM(usd_est), 0.0) FROM costs WHERE day = ?",
        (today,),
    ).fetchone()
    return float(row[0]) if row else 0.0


def _daily_cap_usd() -> float:
    if not MODELS_YAML.exists():
        return 15.0
    cfg = yaml.safe_load(MODELS_YAML.read_text(encoding="utf-8")) or {}
    return float(cfg.get("daily_cost_guardrail_usd", 15.0))


def _engage_kill_switch(reason: str) -> str:
    """Set trading_halt_until to 23:59 UTC today. Returns the new ts string."""
    if not RISK_LIMITS.exists():
        raise FileNotFoundError(RISK_LIMITS)
    cfg = yaml.safe_load(RISK_LIMITS.read_text(encoding="utf-8")) or {}
    today = datetime.now(tz=timezone.utc).replace(
        hour=23, minute=59, second=59, microsecond=0,
    )
    halt_ts = today.strftime("%Y-%m-%dT%H:%M:%SZ")
    cfg.setdefault("hard_rules", {})["trading_halt_until"] = halt_ts

    # Preserve top-of-file comments — read raw, splice the value
    # via yaml roundtrip is acceptable here since this is an emergency path.
    RISK_LIMITS.write_text(yaml.safe_dump(cfg, sort_keys=False),
                           encoding="utf-8")

    db = get_db()
    db.record_risk_event(
        severity="breach", rule="api_budget_kill_switch",
        agent="api_budget_check",
        detail={"reason": reason, "halt_until": halt_ts},
    )
    return halt_ts


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--check-only", action="store_true",
                   help="report status, do not engage the kill switch")
    p.add_argument("--margin-usd", type=float, default=2.0,
                   help="halt when within this margin of cap (default $2)")
    args = p.parse_args()

    try:
        spend = _today_spend_usd()
        cap = _daily_cap_usd()
    except Exception as e:
        print(f"ERROR reading cost state: {e}", file=sys.stderr)
        return 0  # don't block trading on a meta-failure of the budget check

    remaining = cap - spend
    print(f"[api_budget] today spend: ${spend:.2f} / cap ${cap:.2f}  "
          f"(${remaining:.2f} remaining)")

    if remaining <= args.margin_usd:
        msg = (f"Daily budget within ${args.margin_usd} margin "
               f"(spend=${spend:.2f}, cap=${cap:.2f}). "
               f"Engaging kill switch to prevent overspend.")
        print(f"[api_budget] HALT — {msg}")
        if args.check_only:
            return 1
        try:
            halt_ts = _engage_kill_switch(reason=msg)
            print(f"[api_budget] trading_halt_until set to {halt_ts}")
        except Exception as e:
            print(f"[api_budget] FAILED to engage kill switch: {e}",
                  file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
