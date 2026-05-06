"""Trader liveness watchdog.

Runs every 5 minutes via Windows Task Scheduler (FundTraderWatchdog).
Detects a dead/stuck trader via DB heartbeat (account_snapshots.ts) and
auto-restarts via the existing FundAutoTraderDaily task.

Why DB heartbeat over a process check:
  A process check ("is python.exe with scripts.auto_trader running?")
  reports alive even when the trader is deadlocked, network-stuck, or
  silently stalled. The trader's snapshot pipeline writes a row every
  scan cycle (5 min cadence). If snapshots stop, the trader is
  effectively dead even if its PID is still listed.

Detection rule:
  Latest account_snapshots.ts > MAX_AGE_SEC ago → dead.

Recovery:
  1. Clear stale PID lock (logs/auto_trader.pid).
  2. Fire `schtasks /Run /TN FundAutoTraderDaily` to relaunch via the
     normal launcher path (preflight + spawn).
  3. Send Discord alert if DISCORD_WEBHOOK_URL is set.

Usage:
  python -m scripts.trader_watchdog          # quiet check
  python -m scripts.trader_watchdog --force  # force a restart even if alive
  python -m scripts.trader_watchdog --status # report status, no action
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "state" / "fund.db"
PID_FILE = PROJECT_ROOT / "logs" / "auto_trader.pid"
WATCHDOG_LOG = PROJECT_ROOT / "logs" / "watchdog.log"

# Heartbeat threshold: trader writes a snapshot every scan (5 min cadence).
# 2026-05-06: tightened from 12 min to 8 min after a 41-min undetected
# gap. With per-scan cadence of ~5 min, 8 min still allows one missed
# scan + buffer but catches hangs faster.
MAX_AGE_SEC = 8 * 60


def _log(msg: str) -> None:
    line = f"[{datetime.now(timezone.utc).isoformat()}] {msg}"
    print(line)
    try:
        WATCHDOG_LOG.parent.mkdir(parents=True, exist_ok=True)
        with WATCHDOG_LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass  # logging is best-effort


def _latest_snapshot_age_sec() -> float | None:
    """Return seconds since the most recent account_snapshots row, or None
    if the table is empty / DB missing."""
    if not DB_PATH.exists():
        return None
    try:
        c = sqlite3.connect(str(DB_PATH)).cursor()
        r = c.execute(
            "SELECT ts FROM account_snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
    except Exception as exc:
        _log(f"DB read failed: {exc}")
        return None
    if not r:
        return None
    ts_str = r[0]
    if ts_str.endswith("Z"):
        ts_str = ts_str[:-1] + "+00:00"
    ts = datetime.fromisoformat(ts_str)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - ts).total_seconds()


def _discord_alert(msg: str) -> None:
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "").strip()
    if not webhook:
        return
    try:
        import urllib.request
        import json
        body = json.dumps({"content": msg}).encode()
        req = urllib.request.Request(
            webhook, data=body,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=5).read()
    except Exception as exc:
        _log(f"discord alert failed: {exc}")


def _kill_stuck_launchers() -> int:
    """Kill stale powershell.exe processes that are running the trader
    launcher script. Returns count killed.

    Why this matters: the launcher's spawned visible window does
    `Read-Host 'Auto-trader exited. Press Enter to close this window'`
    after the trader exits. That keeps the powershell process alive
    indefinitely waiting for a key press. The FundAutoTraderDaily task
    is registered with MultipleInstances=IgnoreNew, so as long as that
    stuck launcher window is alive, schtasks /Run silently does nothing.
    Result: the watchdog 'fires' revival but no trader actually starts.
    Killing the stuck launchers first frees the task slot.
    """
    killed = 0
    try:
        # Use WMIC to find powershell processes whose command line references
        # the trader launcher or auto_trader module. WMIC is deprecated but
        # ships with Windows and works without admin for own-session procs.
        result = subprocess.run(
            ["wmic", "process", "where",
             "(name='powershell.exe' or name='python.exe')",
             "get", "ProcessId,CommandLine", "/format:csv"],
            capture_output=True, text=True, timeout=15,
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or "Node" in line.split(",")[0]:
                continue
            # csv columns: Node,CommandLine,ProcessId
            parts = line.split(",")
            if len(parts) < 3:
                continue
            cmdline = ",".join(parts[1:-1]).strip()
            try:
                pid = int(parts[-1].strip())
            except ValueError:
                continue
            # Match either the launcher script or the trader module
            if ("start-autotrader-daily" in cmdline.lower() or
                "scripts.auto_trader" in cmdline or
                "Fund Auto-Trader" in cmdline):
                try:
                    subprocess.run(
                        ["taskkill", "/PID", str(pid), "/F", "/T"],
                        capture_output=True, timeout=10,
                    )
                    _log(f"killed stuck launcher/trader PID {pid}")
                    killed += 1
                except Exception as exc:
                    _log(f"could not kill PID {pid}: {exc}")
    except Exception as exc:
        _log(f"stuck-launcher scan failed: {exc}")
    return killed


def _revive() -> bool:
    """Clean up stuck launchers, clear stale PID, fire the task."""
    # 1. Kill any stuck launcher PowerShell windows + dead trader pythons.
    #    Without this, the scheduled task's MultipleInstances=IgnoreNew
    #    policy silently rejects schtasks /Run because the prior instance
    #    is still considered 'running'.
    killed = _kill_stuck_launchers()
    if killed:
        _log(f"cleaned up {killed} stuck process(es) before revival")

    # 2. Clear stale PID lock so the new trader can acquire it.
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
            _log(f"removed stale PID lock {PID_FILE}")
    except Exception as exc:
        _log(f"could not remove PID lock: {exc}")

    # 3. Fire the launcher.
    # Empirically (2026-05-04 testing): schtasks /Run sometimes returns
    # success but produces no actual launcher process. Direct invocation
    # of the launcher script via PowerShell is more reliable. Use that as
    # the primary path; fall back to schtasks if the direct launch fails
    # for some reason.
    launcher = PROJECT_ROOT / "scripts" / "start-autotrader-daily.ps1"
    if launcher.exists():
        try:
            # CREATE_NEW_PROCESS_GROUP — child outlives this watchdog.
            # NOTE: do NOT use DETACHED_PROCESS — the launcher uses
            # Start-Process to spawn the visible trader window, and that
            # spawn fails silently inside a fully-detached process.
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            proc = subprocess.Popen(
                ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(launcher)],
                cwd=str(PROJECT_ROOT),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NEW_PROCESS_GROUP,
                close_fds=True,
            )
            _log(f"launcher spawned directly via Popen, PID {proc.pid}")
            return True
        except Exception as exc:
            _log(f"direct launcher Popen failed: {exc}; falling back to schtasks")

    # Fallback: schtasks /Run
    try:
        result = subprocess.run(
            ["schtasks", "/Run", "/TN", "FundAutoTraderDaily"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            _log(f"FundAutoTraderDaily fired (fallback): {result.stdout.strip()}")
            return True
        _log(f"schtasks /Run failed (rc={result.returncode}): "
             f"{result.stderr.strip() or result.stdout.strip()}")
        return False
    except Exception as exc:
        _log(f"schtasks invocation failed: {exc}")
        return False


def check_and_restart(force: bool = False) -> int:
    """Returns: 0 if alive, 1 if dead+restarted, 2 if dead+restart_failed."""
    age = _latest_snapshot_age_sec()
    if age is None:
        _log("no snapshots in DB — treating as dead")
        is_dead = True
    else:
        is_dead = age > MAX_AGE_SEC
        _log(f"latest snapshot age: {age:.0f}s "
             f"({'DEAD' if is_dead else 'alive'} threshold={MAX_AGE_SEC}s)")

    if not is_dead and not force:
        return 0

    reason = (f"snapshot {age:.0f}s old (>{MAX_AGE_SEC}s threshold)"
              if age else "no snapshot in DB")
    if force:
        reason = "manual --force flag"
    _log(f"REVIVING trader: {reason}")
    _discord_alert(
        f":rotating_light: Trader watchdog triggered restart\n"
        f"Reason: {reason}\n"
        f"Time: {datetime.now(timezone.utc).isoformat()}"
    )
    success = _revive()
    if success:
        _log("revival completed (FundAutoTraderDaily fired)")
        return 1
    _log("REVIVAL FAILED — trader remains dead")
    _discord_alert(
        ":x: Trader watchdog REVIVAL FAILED — manual intervention needed."
    )
    return 2


def status() -> int:
    age = _latest_snapshot_age_sec()
    if age is None:
        print("status: NO SNAPSHOTS (DB empty or missing)")
        return 1
    state = "ALIVE" if age <= MAX_AGE_SEC else "DEAD"
    print(f"status: {state}  (snapshot age: {age:.0f}s, threshold: {MAX_AGE_SEC}s)")
    return 0 if state == "ALIVE" else 1


def daemon_loop(interval_sec: int = 60) -> int:
    """Long-running mode: check every `interval_sec` and revive when dead.

    Provides redundancy to the Windows scheduled task. Useful when the
    scheduled task is unreliable (battery, sleep, missed firings) — this
    daemon is a continuously-running Python process that doesn't depend
    on Task Scheduler.

    Run via:
      python -m scripts.trader_watchdog --daemon

    Or with a custom interval:
      python -m scripts.trader_watchdog --daemon --interval 30
    """
    import time
    _log(f"daemon mode started (interval={interval_sec}s, max_age={MAX_AGE_SEC}s)")
    last_status_log = 0
    revive_count = 0
    while True:
        try:
            age = _latest_snapshot_age_sec()
            now = time.time()
            if age is None:
                if now - last_status_log > 600:
                    _log("daemon: no snapshots yet")
                    last_status_log = now
            elif age > MAX_AGE_SEC:
                _log(f"daemon: snapshot age {age:.0f}s > {MAX_AGE_SEC}s — REVIVING")
                if _revive():
                    revive_count += 1
                    _log(f"daemon: revival #{revive_count} completed")
                    _discord_alert(
                        f":rotating_light: Daemon-mode trader revival #{revive_count}\n"
                        f"Reason: snapshot {age:.0f}s old\n"
                        f"Time: {datetime.now(timezone.utc).isoformat()}"
                    )
                    # Give the new instance time to write its first snapshot
                    time.sleep(120)
                else:
                    _log("daemon: revival FAILED")
                    _discord_alert(
                        ":x: Daemon-mode trader revival FAILED — manual intervention needed."
                    )
                    time.sleep(300)  # Back off before retrying
            else:
                # Healthy — log status hourly
                if now - last_status_log > 3600:
                    _log(f"daemon: ALIVE (snapshot age {age:.0f}s)")
                    last_status_log = now
        except KeyboardInterrupt:
            _log("daemon: stopping (Ctrl+C)")
            return 0
        except Exception as e:
            _log(f"daemon: check error: {type(e).__name__}: {e}")
        time.sleep(interval_sec)


def main() -> int:
    p = argparse.ArgumentParser(prog="trader_watchdog")
    p.add_argument("--force", action="store_true",
                   help="Force a restart regardless of liveness")
    p.add_argument("--status", action="store_true",
                   help="Print status only; take no action")
    p.add_argument("--daemon", action="store_true",
                   help="Run continuously, checking every --interval seconds. "
                        "Redundant alive-check independent of Task Scheduler.")
    p.add_argument("--interval", type=int, default=60,
                   help="Daemon check interval in seconds (default 60)")
    args = p.parse_args()
    if args.status:
        return status()
    if args.daemon:
        return daemon_loop(interval_sec=args.interval)
    return check_and_restart(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
