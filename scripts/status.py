"""Fund status — single-glance health report.

Run any time to see:
  - Current account state (balance, day P&L, canTrade)
  - Halt status
  - Latest snapshot age (is the writer alive?)
  - Today's trades + theses
  - Active positions
  - Recent risk events
  - Scheduled task status
  - Budget burn

Usage:  python -m scripts.status   |  fund status
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)


def _today_utc() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _color(s: str, code: str) -> str:
    return f"\033[{code}m{s}\033[0m"


def main() -> int:
    c = sqlite3.connect("state/fund.db")
    c.row_factory = sqlite3.Row
    risk = yaml.safe_load(Path("config/risk_limits.yaml").read_text(encoding="utf-8"))
    fund = yaml.safe_load(Path("config/fund.yaml").read_text(encoding="utf-8"))

    print()
    print("=" * 60)
    print(f"  FUND STATUS — {datetime.now(tz=timezone.utc).isoformat(timespec='seconds')}")
    print("=" * 60)

    # Snapshot freshness
    snap = c.execute("SELECT * FROM account_snapshots ORDER BY ts DESC LIMIT 1").fetchone()
    if snap:
        ts = datetime.fromisoformat(str(snap["ts"]).replace("Z", "+00:00"))
        age_min = (datetime.now(tz=timezone.utc) - ts).total_seconds() / 60
        age_color = "92" if age_min < 7 else ("93" if age_min < 30 else "91")
        print()
        print(f"  Balance:       ${snap['balance_usd']:>10,.2f}")
        print(f"  Day P&L:       ${snap['realized_pl_day_usd']:>+10,.2f}")
        print(f"  Trailing DD:   ${snap['trailing_dd_usd']:>10,.2f}")
        print(f"  canTrade:      {'YES' if snap['can_trade'] else _color('NO', '91')}")
        print(f"  Open ctrs:     {snap['open_contracts_total']}")
        print(f"  Last snapshot: {_color(f'{age_min:.1f} min ago', age_color)} "
              f"(writer {'alive' if age_min < 7 else 'STALE — investigate'})")
    else:
        print("  No snapshots yet.")

    # Halt status
    halt = (risk.get("hard_rules") or {}).get("trading_halt_until", "")
    halted_flag = (risk.get("hard_rules") or {}).get("trading_halted")
    print()
    print("HALT STATUS")
    print("-" * 60)
    print(f"  trading_halted (manual flag): {halted_flag}")
    if halt:
        try:
            t = datetime.fromisoformat(str(halt).replace("Z", "+00:00"))
            now = datetime.now(tz=timezone.utc)
            if t > now:
                delta_h = (t - now).total_seconds() / 3600
                print(f"  trading_halt_until: {_color(halt, '91')} (active, {delta_h:+.1f}h)")
            else:
                print(f"  trading_halt_until: {halt} (expired)")
        except Exception:
            print(f"  trading_halt_until: {halt} (UNPARSEABLE)")

    # Today's activity
    day = _today_utc()
    fills_today = c.execute(
        "SELECT COUNT(*) FROM orders "
        "WHERE ts_proposed LIKE ? AND agent='auto_trader' "
        "  AND client_order_id NOT LIKE '%_stop' "
        "  AND client_order_id NOT LIKE '%_target'",
        (f"{day}%",),
    ).fetchone()[0]
    theses_today = c.execute(
        "SELECT COUNT(*) FROM decisions WHERE agent='auto_trader' AND kind='thesis' AND ts LIKE ?",
        (f"{day}%",),
    ).fetchone()[0]
    print()
    print(f"TODAY ({day})")
    print("-" * 60)
    print(f"  Theses logged:    {theses_today}")
    print(f"  Order entries:    {fills_today}")

    # Risk events today by severity
    events = list(c.execute(
        "SELECT severity, rule, COUNT(*) AS n FROM risk_events "
        "WHERE ts LIKE ? GROUP BY severity, rule ORDER BY n DESC",
        (f"{day}%",),
    ))
    if events:
        print()
        print("RISK EVENTS TODAY")
        print("-" * 60)
        for ev in events:
            color = "91" if ev["severity"] == "block" else ("93" if ev["severity"] == "warn" else "0")
            print(f"  {_color(ev['severity'], color):20s} {ev['rule']:35s} {ev['n']:>3d}")

    # Mode + restrictions
    print()
    print("MODE")
    print("-" * 60)
    print(f"  current_phase:    {fund.get('current_phase', 'unset')}")
    print(f"  autonomous_mode:  {fund.get('autonomous_mode', False)}")
    if fund.get("autonomous_mode"):
        r = fund.get("autonomous_restrictions") or {}
        print(f"  RTH-only window:  {r.get('rth_start_et', '?')}–{r.get('rth_end_et', '?')} ET")
        print(f"  Internal DLL:     ${r.get('internal_dll_target_usd', '?')}")
        print(f"  Daily fee budget: ${r.get('daily_fee_budget_usd', '?')}")
        print(f"  Max concurrent:   {r.get('max_concurrent_positions', '?')} positions")
        print(f"  Max trades/day:   {r.get('max_trades_per_day', '?')}")

    # Auto_trader process
    print()
    print("PROCESSES")
    print("-" * 60)
    pid_file = Path("logs/auto_trader.pid")
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            try:
                os.kill(pid, 0)
                print(f"  auto_trader: {_color('RUNNING', '92')} (PID {pid})")
            except (OSError, ProcessLookupError):
                print(f"  auto_trader: {_color('STALE PID', '93')} ({pid} not alive)")
        except Exception:
            print(f"  auto_trader: pid file unparseable")
    else:
        print(f"  auto_trader: {_color('NOT RUNNING', '93')}")

    # Scheduled task (Windows only)
    print()
    print("SCHEDULED TASKS")
    print("-" * 60)
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command",
             "Get-ScheduledTask -TaskName FundAutoTraderDaily -ErrorAction SilentlyContinue | "
             "Select-Object -ExpandProperty State"],
            capture_output=True, text=True, timeout=10,
        )
        state = result.stdout.strip() or "not registered"
        print(f"  FundAutoTraderDaily: {state}")
    except Exception:
        print(f"  (could not query scheduled tasks)")

    # API spend today (if costs table populated)
    api_today = c.execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day = ?", (day,)
    ).fetchone()[0]
    print()
    print("API SPEND")
    print("-" * 60)
    print(f"  Today:            ${api_today:.2f}")
    cap = (fund.get("autonomy_guardrails") or {}).get("max_usd_per_day", 0)
    if cap > 0:
        used_pct = (api_today / cap) * 100 if cap > 0 else 0
        print(f"  Daily cap:        ${cap:.2f}  ({used_pct:.0f}% used)")

    print()
    print("=" * 60)
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
