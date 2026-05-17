"""Sentinel — continuous autonomous anomaly watcher.

Built 2026-05-15 per user direct quote 2026-05-14: "nothing improves
unless I directly work on it." Multiple bugs in the prior week (tests
writing mock orders to production DB, MGC missing from _TICK_ECONOMICS,
profit-lock $49 slippage from polling latency) all went undetected
until the user manually flagged them. Watchdog covers PROCESS death
and Discord covers some EVENTS, but nothing watches BEHAVIOR — the
gap that lets silent bugs ride.

Runs every ~10 min (via FundSentinel scheduled task — register at
deploy time). Each check returns a list of findings; main() aggregates,
posts critical/warn findings to Discord, and writes a daily report.

Checks (each a pure function over DB / broker state):
  1. check_mock_orders_in_db       — tests polluting production
  2. check_open_position_economics — profit-lock blindness
  3. check_close_slippage_vs_floor — broker latency / polling miss
  4. check_orphan_working_orders   — cleanup_orphan_brackets gap
  5. check_brain_vs_trader_rate    — signal-pipeline health
  6. check_duplicate_trader_procs  — race-cause for double-firing

Usage:
    python -m tools.sentinel            # one shot, post to Discord
    python -m tools.sentinel --dry      # check + print, no Discord
    python -m tools.sentinel --report   # also write daily MD report

Exit code 0 if no critical findings, 1 if any.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _PROJECT_ROOT / "state" / "fund.db"
_REPORT_DIR = _PROJECT_ROOT / "vault" / "_meta"


@dataclass
class Finding:
    """Single anomaly report."""
    check_name: str
    severity: str          # 'crit' | 'warn' | 'info'
    summary: str           # one-line for Discord
    detail: dict[str, Any] = field(default_factory=dict)


# ── Check 1: mock_* order IDs in production DB ────────────────────

def check_mock_orders_in_db(conn: sqlite3.Connection) -> list[Finding]:
    """Tests using a StubBroker mint client_order_ids like 'mock_1'
    and place_order ids like 'mock_1'. If those land in production
    state/fund.db, the test environment leaked into production state.
    Hit 2026-05-15: 24 mock orders found mid-session.
    """
    findings: list[Finding] = []
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT COUNT(*), MIN(ts_proposed), MAX(ts_proposed) FROM orders "
        "WHERE broker_order_id LIKE 'mock_%' OR client_order_id LIKE 'mock_%'"
    ).fetchone()
    n, ts_min, ts_max = rows
    if n and n > 0:
        findings.append(Finding(
            check_name="mock_orders_in_db",
            severity="crit",
            summary=f"{n} mock_* orders in production DB "
                     f"(range {ts_min} → {ts_max}). Tests are polluting state.",
            detail={"count": int(n), "first_ts": ts_min, "last_ts": ts_max},
        ))
    return findings


# ── Check 2: every open position has tick economics ────────────────

def check_open_position_economics(conn: sqlite3.Connection,
                                     get_positions=None) -> list[Finding]:
    """If `_resolve_tick_economics` returns (0,0) for any open position,
    profit-lock + loss-cap are BLIND to that position — only broker stop
    protects. The 2026-05-14 EU6 incident is the canonical example.

    `get_positions` is injectable for tests. In production we use the
    real ProjectX client.
    """
    findings: list[Finding] = []
    if get_positions is None:
        try:
            from tools.projectx_client import ProjectXClient, get_account_id
            client = ProjectXClient()
            client.authenticate()
            positions = client.get_positions(get_account_id()) or []
        except Exception as e:
            findings.append(Finding(
                check_name="open_position_economics",
                severity="warn",
                summary=f"could not fetch positions: {type(e).__name__}: {e}",
            ))
            return findings
    else:
        positions = get_positions()

    from tools.profit_protect import _contract_to_symbol, _resolve_tick_economics
    for p in positions:
        contract_id = p.get("contractId", "")
        size = int(p.get("size", 0) or 0)
        if size == 0:
            continue
        sym = _contract_to_symbol(contract_id) or ""
        ts, tv = _resolve_tick_economics(sym) if sym else (0.0, 0.0)
        if ts <= 0 or tv <= 0:
            findings.append(Finding(
                check_name="open_position_economics",
                severity="crit",
                summary=f"open {contract_id} ({sym}) has NO tick economics "
                         f"— profit-lock + loss-cap BLIND.",
                detail={"contract_id": contract_id, "symbol": sym,
                          "size": size, "tick_size": ts, "tick_value": tv},
            ))
    return findings


# ── Check 3: close slippage vs the floor that should have fired ────

def check_close_slippage_vs_floor(conn: sqlite3.Connection,
                                     hours: int = 24) -> list[Finding]:
    """For each closed trade today: if the profit-lock floor should
    have fired (peak crossed a tier threshold), but realized P&L
    is >SLIPPAGE_THRESHOLD_USD below the floor, flag it. Indicates
    broker latency or polling-miss between peak and close.

    Skips trades with no recorded peak (loss-cap closes, stop-outs).
    """
    SLIPPAGE_THRESHOLD_USD = 10.0
    findings: list[Finding] = []
    cur = conn.cursor()
    # decisions table has the audit row: kind='close', reason includes
    # 'trailing_lock' / 'target_hit' / etc. Peak + realized comparison
    # comes from there.
    #
    # 2026-05-17 false-positive guard: cross-reference with orders.status
    # = 'filled'. Counterfactual replays (scripts/replay_exits.py) and
    # test harnesses write rows to `decisions` with agent='profit_lock'
    # but DO NOT create corresponding broker fills. Without this guard
    # the same 6 synthetic close decisions today produced 20+ false
    # Discord alarms across 5/15 + 5/17. The fix: require at least one
    # `orders` row with status='filled' for the same symbol within ±10
    # minutes of the decision ts. Real closes always pair with a fill;
    # replays don't.
    cutoff_iso = (datetime.now(tz=timezone.utc) - timedelta(hours=hours)).isoformat()
    try:
        rows = cur.execute(
            "SELECT ts, agent, kind, symbol, rationale FROM decisions "
            "WHERE ts >= ? AND kind = 'close' AND agent = 'profit_lock'",
            (cutoff_iso,),
        ).fetchall()
    except sqlite3.Error:
        return findings
    for r in rows:
        # Parse "peak=$X.XX realized=$Y.YY reason=..." from rationale
        # (the schema written by _record_close_decision)
        ts, agent, kind, symbol, rationale = r
        if not rationale:
            continue
        # ── False-positive guard: cross-reference with orders.status ──
        try:
            ts_dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            window_start = (ts_dt - timedelta(minutes=10)).isoformat()
            window_end = (ts_dt + timedelta(minutes=10)).isoformat()
            fill_count = cur.execute(
                "SELECT COUNT(*) FROM orders "
                "WHERE symbol = ? AND status = 'filled' "
                "AND ts_filled >= ? AND ts_filled <= ?",
                (symbol, window_start, window_end),
            ).fetchone()
            if not fill_count or fill_count[0] == 0:
                # Synthetic / replay row — skip it. Real-money closes
                # always have a matching filled order in the same window.
                continue
        except Exception:
            # If we can't parse ts or look up fills, fail OPEN (alert) so
            # we don't accidentally mask a real bug behind a parse error.
            pass
        try:
            peak = realized = None
            for token in rationale.split():
                if token.startswith("peak="):
                    peak = float(token[5:].lstrip("$").rstrip(","))
                elif token.startswith("unrealized=") or token.startswith("realized="):
                    realized = float(token.split("=", 1)[1].lstrip("$").rstrip(","))
            if peak is None or realized is None or peak <= 0:
                continue
            from tools.profit_protect import _compute_active_floor
            floor = _compute_active_floor(peak)
            if floor is None:
                continue
            slippage = floor - realized
            if slippage > SLIPPAGE_THRESHOLD_USD:
                findings.append(Finding(
                    check_name="close_slippage_vs_floor",
                    severity="warn",
                    summary=f"{symbol} closed at ${realized:.0f} but floor "
                             f"was ${floor:.0f} (peak ${peak:.0f}) — "
                             f"${slippage:.0f} slippage past floor.",
                    detail={"symbol": symbol, "peak": peak,
                              "realized": realized, "floor": floor,
                              "slippage_usd": slippage, "ts": ts},
                ))
        except Exception:
            continue
    return findings


# ── Check 4: working orders with no matching open position ─────────

def check_orphan_working_orders(get_positions=None,
                                  get_working_orders=None) -> list[Finding]:
    """A 'live_<cid>_stop' working order with no corresponding open
    position on the same contract = orphan. The 5/1 + 5/10 incidents
    cost real money when orphan stops fired alone. cleanup_orphan_brackets
    sweeps them, but verifying here closes the gap if that sweep ever
    silently breaks.
    """
    findings: list[Finding] = []
    if get_positions is None or get_working_orders is None:
        try:
            from tools.projectx_client import ProjectXClient, get_account_id
            client = ProjectXClient()
            client.authenticate()
            acct = get_account_id()
            positions = client.get_positions(acct) or []
            working = client.get_working_orders(acct) or []
        except Exception as e:
            findings.append(Finding(
                check_name="orphan_working_orders",
                severity="warn",
                summary=f"could not fetch orders/positions: "
                         f"{type(e).__name__}: {e}",
            ))
            return findings
    else:
        positions = get_positions()
        working = get_working_orders()

    open_contracts = {p.get("contractId") for p in positions
                       if int(p.get("size", 0) or 0) != 0}
    for o in working:
        cid = o.get("contractId")
        tag = str(o.get("customTag") or "")
        # Only check our own protective stops (tagged live_<x>_stop)
        if not (tag.startswith("live_") and tag.endswith("_stop")):
            continue
        if cid not in open_contracts:
            findings.append(Finding(
                check_name="orphan_working_orders",
                severity="crit",
                summary=f"orphan stop {tag} on {cid} — no open position. "
                         f"Could fire alone and open unintended position.",
                detail={"contract_id": cid, "custom_tag": tag,
                          "type": o.get("type"), "stop_price": o.get("stopPrice")},
            ))
    return findings


# ── Check 5: brain emit rate vs trader scan rate ───────────────────

def check_brain_vs_trader_rate(conn: sqlite3.Connection,
                                 minutes: int = 60) -> list[Finding]:
    """Brain emits signals to state/pending_signals.json every ~60s;
    trader consumes them every ~300s. Over `minutes` minutes:
      expected_emissions = minutes
      expected_consumed_floor = minutes / 5 - 1
    If consumed << emitted, the trader scan loop is stuck.
    Reads recent orders count as the proxy for "consumed by trader."

    NOTE: This check has high false-positive risk during regime gates
    (most signals get blocked, no orders produced). For now, only
    fires CRIT if zero orders were proposed in the window AND brain
    log shows non-zero emits. Manual investigation.
    """
    findings: list[Finding] = []
    cutoff = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes)
    cur = conn.cursor()
    n_orders = cur.execute(
        "SELECT COUNT(*) FROM orders WHERE ts_proposed >= ?",
        (cutoff.isoformat(),),
    ).fetchone()[0]
    # Brain log check — count "brain: emitted" lines in the last `minutes`
    n_emissions = 0
    log_path = _PROJECT_ROOT / "logs" / "brain_v4.log"
    if log_path.exists():
        try:
            with log_path.open("r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    if "brain: emitted" not in line:
                        continue
                    try:
                        ts_str = line.split("]", 1)[0].strip("[ ")
                        ts = datetime.fromisoformat(ts_str.replace(" UTC", "+00:00"))
                    except Exception:
                        continue
                    if ts >= cutoff:
                        n_emissions += 1
        except Exception:
            return findings
    # Only flag if brain is producing signals but trader is producing zero
    # orders (proposed OR cancelled). 0 emissions = normal idle, not a bug.
    if n_emissions >= 5 and n_orders == 0:
        # Check if a known benign cause is in the trader stdout log:
        # daily trade cap, halted, snapshot stale, etc. If so, skip the
        # warning — trader is correctly blocking everything by design.
        benign_reason = None
        trader_log = _PROJECT_ROOT / "logs" / "livetrader_morning_stdout.log"
        if trader_log.exists():
            try:
                tail = trader_log.read_text(encoding="utf-8",
                                              errors="replace").splitlines()[-50:]
                for line in tail:
                    for marker in ("daily trade cap hit",
                                     "halt active",
                                     "thin-tape regime block",
                                     "outside autonomous RTH window",
                                     "snapshot stale",
                                     "skipped (recent thesis)",
                                     "skipped (cooldown)",
                                     "queue: no pending signals"):
                        if marker in line:
                            benign_reason = marker
                            break
                    if benign_reason:
                        break
            except Exception:
                pass
        if benign_reason:
            return findings  # known-benign, no warning
        findings.append(Finding(
            check_name="brain_vs_trader_rate",
            severity="warn",
            summary=f"brain emitted {n_emissions} signals in last {minutes}min "
                     f"but trader produced 0 orders. Not in daily-cap / halt / "
                     f"regime-block / window state — scan loop may be stuck.",
            detail={"n_emissions": n_emissions, "n_orders": n_orders,
                      "window_minutes": minutes},
        ))
    return findings


# ── Check 6: duplicate live_trader processes ───────────────────────

def check_duplicate_trader_procs(ps_command_runner=None) -> list[Finding]:
    """More than one `scripts.live_trader` python process = race risk.
    Two traders see the same signal and try to fill twice, OR one
    trader's stop-replace happens after the other's, OR conflicting
    state in the same DB. 2026-05-15 saw this once after a kill/restart
    that left a zombie process.
    """
    findings: list[Finding] = []
    if ps_command_runner is None:
        try:
            # Windows: wmic command line for python.exe processes
            out = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
                  "| Where-Object { $_.CommandLine -like '*scripts.live_trader*' } "
                  "| Select-Object -ExpandProperty ProcessId"],
                capture_output=True, text=True, timeout=10,
            )
            pids = [int(p.strip()) for p in out.stdout.splitlines() if p.strip().isdigit()]
        except Exception:
            return findings
    else:
        pids = ps_command_runner()
    # Windows Python often spawns a parent + child for Start-Process I/O;
    # tolerate up to 2 PIDs as the "single instance" case.
    if len(pids) > 2:
        findings.append(Finding(
            check_name="duplicate_trader_procs",
            severity="crit",
            summary=f"{len(pids)} live_trader python processes running "
                     f"(PIDs {pids}). Expected 1-2. Race risk on signals "
                     f"+ orders. Kill duplicates immediately.",
            detail={"pids": pids, "count": len(pids)},
        ))
    return findings


# ── Aggregation + report ──────────────────────────────────────────

def check_peak_capture_weekly(conn: sqlite3.Connection,
                                 days: int = 7) -> list[Finding]:
    """Aggregate peak_pct_captured across profit_lock closes in the last
    `days` days. Warns if avg <30% (exit rules not delivering) or if
    trending DOWN week-over-week.

    Measures whether the exit rebuild (percent-of-peak, reversal,
    time-decay) actually captures peak P&L in production. The
    counterfactual replay (2026-05-15) suggested calibrated rules
    should hit 25-35% capture; this confirms it live.

    Skips trades with negative peak (peak_pct_captured=n/a).
    """
    findings: list[Finding] = []
    cutoff_iso = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
    try:
        rows = conn.cursor().execute(
            "SELECT ts, symbol, rationale FROM decisions "
            "WHERE ts >= ? AND kind = 'close' AND agent = 'profit_lock'",
            (cutoff_iso,),
        ).fetchall()
    except sqlite3.Error:
        return findings

    captures: list[float] = []
    for ts, symbol, rationale in rows:
        if not rationale:
            continue
        # rationale format includes "peak_pct_captured=0.376"
        for token in rationale.split("|"):
            token = token.strip()
            if token.startswith("peak_pct_captured="):
                val = token.split("=", 1)[1].strip()
                if val == "n/a":
                    continue
                try:
                    captures.append(float(val))
                except ValueError:
                    pass
                break
    if not captures:
        return findings  # no measurable trades this window

    avg_capture = sum(captures) / len(captures)
    n = len(captures)
    capture_pct = avg_capture * 100

    if avg_capture < 0.30:
        findings.append(Finding(
            check_name="peak_capture_weekly",
            severity="warn",
            summary=(f"weekly peak capture {capture_pct:.0f}% over n={n} closes "
                     f"— below 30% threshold. Exit rules may need tuning OR "
                     f"signal stops are firing before peak develops."),
            detail={"days": days, "n_closes": n, "avg_capture": avg_capture,
                     "target_pct": 30},
        ))
    else:
        # Info-level: track healthy capture for the daily report
        findings.append(Finding(
            check_name="peak_capture_weekly",
            severity="info",
            summary=(f"weekly peak capture {capture_pct:.0f}% over n={n} closes "
                     f"(healthy ≥ 30%)."),
            detail={"days": days, "n_closes": n, "avg_capture": avg_capture},
        ))
    return findings


def check_tick_stream_stale() -> list[Finding]:
    """If the trader has open positions but the tick_stream cache is
    stale or empty, profit-lock decisions are being made on bar-polled
    data instead of sub-second ticks — defeats the whole point of
    the tick stream.

    Sentinel doesn't have access to the trader's in-process tick cache
    (different process). So this check is best-effort: it logs the
    last-event timestamp from the most recent sentinel report if any,
    and warns if it hasn't seen evidence of recent tick activity. The
    real check happens via the trader log line "tick_stream started"
    and any subsequent "tick_stream stale" log entry.

    For now, mark as low-severity — the bar-fetcher fallback is
    fail-safe so this isn't a hard outage.
    """
    findings: list[Finding] = []
    # Look at the trader's stdout log for tick_stream lifecycle markers
    trader_log = _PROJECT_ROOT / "logs" / "livetrader_morning_stdout.log"
    if not trader_log.exists():
        return findings
    try:
        tail = trader_log.read_text(encoding="utf-8",
                                       errors="replace").splitlines()[-200:]
    except Exception:
        return findings
    started = any("tick_stream started" in l for l in tail)
    failed = any("tick_stream init failed" in l for l in tail)
    if failed and not started:
        findings.append(Finding(
            check_name="tick_stream_stale",
            severity="warn",
            summary="tick_stream init failed in trader; profit_protect "
                     "falling back to 1-min bar polling. WebSocket connection "
                     "may be blocked or signalrcore not installed.",
        ))
    return findings


def run_all_checks() -> list[Finding]:
    """Open the DB, run every check, return aggregated findings."""
    findings: list[Finding] = []
    if not _DB_PATH.exists():
        findings.append(Finding(
            check_name="setup",
            severity="crit",
            summary=f"DB not found at {_DB_PATH}; sentinel cannot run.",
        ))
        return findings
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        findings.extend(check_mock_orders_in_db(conn))
        findings.extend(check_open_position_economics(conn))
        findings.extend(check_close_slippage_vs_floor(conn))
        findings.extend(check_orphan_working_orders())
        findings.extend(check_brain_vs_trader_rate(conn))
        findings.extend(check_duplicate_trader_procs())
        findings.extend(check_tick_stream_stale())
        findings.extend(check_peak_capture_weekly(conn))
    finally:
        conn.close()
    return findings


def _post_to_discord(findings: list[Finding]) -> None:
    if not findings:
        return
    try:
        from tools.alert import send_alert
    except Exception:
        return
    for f in findings:
        prefix = {"crit": "🚨", "warn": "⚠️", "info": "ℹ️"}.get(f.severity, "")
        send_alert(f"{prefix} sentinel/{f.check_name}: {f.summary}",
                    level=f.severity if f.severity in ("info", "warn", "crit") else "info")


def _write_report(findings: list[Finding]) -> Path:
    today = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")
    path = _REPORT_DIR / f"sentinel_{today}.md"
    _REPORT_DIR.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        ts = datetime.now(tz=timezone.utc).isoformat()
        f.write(f"\n## {ts}\n\n")
        if not findings:
            f.write("All checks passed.\n")
        for finding in findings:
            f.write(f"- **[{finding.severity}]** `{finding.check_name}`: {finding.summary}\n")
            if finding.detail:
                f.write(f"  - detail: {finding.detail}\n")
    return path


def _load_dotenv() -> None:
    """Lightweight .env reader so `python -m tools.sentinel` works
    standalone (without depending on python-dotenv install)."""
    env_file = _PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    try:
        for raw in env_file.read_text(encoding="utf-8", errors="replace").splitlines():
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run sentinel anomaly checks.")
    parser.add_argument("--dry", action="store_true",
                          help="print findings; do not post to Discord")
    parser.add_argument("--report", action="store_true",
                          help="append findings to vault/_meta/sentinel_YYYY-MM-DD.md")
    args = parser.parse_args(argv)

    _load_dotenv()
    findings = run_all_checks()

    # 2026-05-17 fix: force utf-8 stdout on Windows so Unicode in summaries
    # (≥, ←, →, etc.) doesn't crash the sentinel before findings are reported.
    try:
        import sys as _sys
        if hasattr(_sys.stdout, "reconfigure"):
            _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    print(f"sentinel: {len(findings)} finding(s)")
    for f in findings:
        try:
            print(f"  [{f.severity}] {f.check_name}: {f.summary}")
        except UnicodeEncodeError:
            # Fallback: ASCII-only render so we never silently drop findings
            ascii_summary = f.summary.encode("ascii", "replace").decode("ascii")
            print(f"  [{f.severity}] {f.check_name}: {ascii_summary}")

    if not args.dry:
        _post_to_discord(findings)
    if args.report:
        path = _write_report(findings)
        print(f"sentinel: report appended to {path}")

    # Exit code 1 if any critical findings (so scheduled task can flag)
    if any(f.severity == "crit" for f in findings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
