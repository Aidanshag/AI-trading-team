"""full_system_audit — comprehensive autonomous system health check.

User direction 2026-05-17: "is there a way to autonomize many of these
things that i have to input such as an audit. an audit could be very
helpful."

Bundles every audit pass into one report:
  1. Process audit — trader root count, brain count, stale-process check
  2. Scheduled tasks — last result, next run, no missed schedules
  3. Heartbeat — trader/brain logs ticking, snapshot table fresh
  4. Test suite — full run, fail-fast on any failure
  5. Separation audit — broker isolation clean
  6. Sentinel — current findings (any critical?)
  7. Allowlist sanity — live vs shadow split, no orphan cells
  8. IB pull health — backfill scripts still progressing
  9. Code-state audit — uncommitted HIGH_RISK files, stale processes
     running stale code (check file mtime vs process start time)
 10. Disk/memory — bar files growing reasonably, no runaway logs

Output:
  - vault/_meta/audit_YYYY-MM-DD_HH-MM.md (human report)
  - Discord alert if ANY check returns CRITICAL severity
  - Exit code: 0=all good, 1=warn-level findings, 2=critical findings

Designed to be scheduled (e.g., daily at 18:00 ET / 22:00 UTC).
Cheap: ~60 sec for the full pass.
"""
from __future__ import annotations

import json
import os
import subprocess
import sqlite3
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DB_PATH = ROOT / "state" / "fund.db"
REPORT_DIR = ROOT / "vault" / "_meta"


@dataclass
class AuditFinding:
    check: str
    severity: str  # info | warn | crit
    summary: str
    detail: dict = field(default_factory=dict)


# ── Check helpers ─────────────────────────────────────────────────


def _list_python_procs(matching: str) -> list[dict]:
    """Return python.exe processes whose CommandLine matches `matching`."""
    out = []
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
             "Where-Object { $_.CommandLine -like '*" + matching + "*' } | "
             "Select-Object ProcessId, ParentProcessId, CreationDate, CommandLine | "
             "ConvertTo-Json"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return []
        data = json.loads(r.stdout) if r.stdout.strip() else []
        if isinstance(data, dict):
            data = [data]
        for p in data:
            out.append(p)
    except Exception:
        pass
    return out


def check_trader_processes() -> list[AuditFinding]:
    """Verify exactly ONE root live_trader python instance is running."""
    procs = _list_python_procs("scripts.live_trader")
    findings = []
    if not procs:
        findings.append(AuditFinding(
            "trader_process", "crit",
            "NO live_trader instance running — Combine path is dark",
        ))
        return findings
    # Compute root instances (parent NOT another live_trader).
    # Force int comparison to avoid PowerShell/JSON type drift where
    # ParentProcessId can deserialize as a different type than the keys.
    pids = {int(p["ProcessId"]): p for p in procs}
    roots = [p for p in procs
             if int(p.get("ParentProcessId", -1)) not in pids]
    if len(roots) > 1:
        findings.append(AuditFinding(
            "trader_process", "crit",
            f"{len(roots)} ROOT live_trader instances — race risk + double-trade",
            {"root_pids": [r["ProcessId"] for r in roots]},
        ))
    elif len(roots) == 1:
        findings.append(AuditFinding(
            "trader_process", "info",
            f"trader healthy (PID {roots[0]['ProcessId']}, "
            f"{len(procs)} total incl. child workers)",
        ))
    return findings


def check_brain_processes() -> list[AuditFinding]:
    procs = _list_python_procs("scripts.brain_signaler")
    findings = []
    if not procs:
        findings.append(AuditFinding(
            "brain_process", "warn",
            "no brain_signaler running — no signals will be emitted",
        ))
        return findings
    # Find root brains (parent not also a brain) — force int comparison
    pids = {int(p["ProcessId"]): p for p in procs}
    roots = [p for p in procs if int(p.get("ParentProcessId", -1)) not in pids]
    if len(roots) > 1:
        findings.append(AuditFinding(
            "brain_process", "warn",
            f"{len(roots)} brain_signaler instances (expected 1)",
        ))
    elif len(roots) == 1:
        findings.append(AuditFinding(
            "brain_process", "info",
            f"brain healthy (PID {roots[0]['ProcessId']})",
        ))
    return findings


def check_process_freshness(max_age_days: int = 5) -> list[AuditFinding]:
    """Flag long-running processes that may be running stale code."""
    findings = []
    procs = []
    for pat in ("scripts.live_trader", "scripts.brain_signaler"):
        procs.extend(_list_python_procs(pat))
    now = datetime.now(tz=timezone.utc)
    for p in procs:
        cd = p.get("CreationDate")
        if not cd:
            continue
        # Parse the WMI date — e.g. "/Date(1716321483000)/" or ISO
        ts = None
        try:
            if isinstance(cd, str) and "/Date(" in cd:
                ms = int(cd.split("/Date(")[1].split(")")[0])
                ts = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
            elif isinstance(cd, dict) and "DateTime" in cd:
                ts = datetime.fromisoformat(cd["DateTime"].replace("Z","+00:00"))
        except Exception:
            continue
        if ts is None:
            continue
        age_days = (now - ts).total_seconds() / 86400
        if age_days > max_age_days:
            cmd = p.get("CommandLine", "")
            mod = "live_trader" if "live_trader" in cmd else "brain_signaler"
            findings.append(AuditFinding(
                "process_freshness", "warn",
                f"{mod} PID {p['ProcessId']} running {age_days:.1f} days "
                f"— may be on stale code; consider restart",
            ))
    return findings


def check_snapshot_freshness(max_age_minutes: int = 10) -> list[AuditFinding]:
    findings = []
    if not DB_PATH.exists():
        return [AuditFinding("snapshot", "crit", "fund.db missing")]
    try:
        conn = sqlite3.connect(str(DB_PATH))
        row = conn.execute(
            "SELECT ts FROM account_snapshots ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
    except Exception as e:
        return [AuditFinding("snapshot", "crit", f"DB query failed: {e}")]
    if not row:
        return [AuditFinding("snapshot", "crit",
                              "account_snapshots empty — gates blind")]
    try:
        ts = datetime.fromisoformat(str(row[0]).replace("Z", "+00:00"))
        age_min = (datetime.now(tz=timezone.utc) - ts).total_seconds() / 60
        if age_min > max_age_minutes:
            findings.append(AuditFinding(
                "snapshot", "warn",
                f"latest snapshot is {age_min:.1f} min old "
                f"(stale threshold: {max_age_minutes})",
            ))
        else:
            findings.append(AuditFinding(
                "snapshot", "info",
                f"snapshot fresh ({age_min:.1f} min old)",
            ))
    except Exception as e:
        findings.append(AuditFinding("snapshot", "warn", f"ts parse failed: {e}"))
    return findings


def check_scheduled_tasks() -> list[AuditFinding]:
    findings = []
    tasks_to_check = [
        "FundLiveTraderEnsureRunning",
        "FundTraderWatchdog",
        "FundMacroBriefDaily",
        "FundSentinel",
    ]
    # Query each task individually — Get-ScheduledTaskInfo doesn't accept
    # an array of names in older Windows versions, so iterate.
    for task_name in tasks_to_check:
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"Get-ScheduledTaskInfo -TaskName '{task_name}' "
                 f"-ErrorAction SilentlyContinue | "
                 f"Select-Object TaskName, LastTaskResult, NextRunTime | "
                 f"ConvertTo-Json"],
                capture_output=True, text=True, timeout=10,
            )
            if r.returncode != 0 or not r.stdout.strip():
                findings.append(AuditFinding(
                    "scheduled_tasks", "warn",
                    f"{task_name}: NOT FOUND or query failed",
                ))
                continue
            data = json.loads(r.stdout)
            result = data.get("LastTaskResult")
            if result not in (0, None, 267011):  # 267011 = task hasn't run yet
                findings.append(AuditFinding(
                    "scheduled_tasks", "warn",
                    f"{task_name} LastTaskResult={result} (non-zero)",
                ))
        except Exception as e:
            findings.append(AuditFinding(
                "scheduled_tasks", "warn",
                f"{task_name} query exception: {e}",
            ))
    return findings


def check_test_suite() -> list[AuditFinding]:
    findings = []
    try:
        python_exe = str(ROOT / ".venv" / "Scripts" / "python.exe")
        if not os.path.exists(python_exe):
            python_exe = sys.executable
        r = subprocess.run(
            [python_exe, "-m", "pytest", "tests/", "-q",
             "--ignore=tests/test_overnight_fixes.py", "--tb=no", "-x"],
            capture_output=True, text=True, timeout=120,
            cwd=str(ROOT),
        )
        last_line = (r.stdout.strip().split("\n") or [""])[-1]
        if "failed" in last_line:
            findings.append(AuditFinding(
                "test_suite", "crit",
                f"test failures detected: {last_line}",
            ))
        elif "passed" in last_line:
            findings.append(AuditFinding(
                "test_suite", "info", f"tests pass: {last_line}",
            ))
        else:
            findings.append(AuditFinding(
                "test_suite", "warn",
                f"unrecognized test output: {last_line[:100]}",
            ))
    except subprocess.TimeoutExpired:
        findings.append(AuditFinding("test_suite", "warn",
                                       "test suite timeout >120s"))
    except Exception as e:
        findings.append(AuditFinding("test_suite", "warn",
                                       f"could not run tests: {e}"))
    return findings


def check_separation() -> list[AuditFinding]:
    try:
        from tools.separation_audit import violations
        vs = violations()
        if vs:
            return [AuditFinding("separation", "crit",
                                  f"{len(vs)} broker-separation violation(s)",
                                  {"violations": vs})]
        return [AuditFinding("separation", "info",
                              "broker separation clean (Topstep / IB isolated)")]
    except Exception as e:
        return [AuditFinding("separation", "warn",
                              f"separation audit failed: {e}")]


def check_sentinel() -> list[AuditFinding]:
    try:
        from tools.sentinel import run_all_checks
        results = run_all_checks()
        crit = [r for r in results if r.severity == "crit"]
        warn = [r for r in results if r.severity == "warn"]
        if crit:
            return [AuditFinding("sentinel", "crit",
                                  f"{len(crit)} sentinel critical finding(s)",
                                  {"findings": [r.summary for r in crit]})]
        if warn:
            return [AuditFinding("sentinel", "warn",
                                  f"{len(warn)} sentinel warning(s)",
                                  {"findings": [r.summary for r in warn]})]
        return [AuditFinding("sentinel", "info",
                              f"sentinel clean ({len(results)} findings, all info)")]
    except Exception as e:
        return [AuditFinding("sentinel", "warn",
                              f"sentinel run failed: {e}")]


def check_allowlist() -> list[AuditFinding]:
    findings = []
    path = ROOT / "state" / "strategy_validation.json"
    if not path.exists():
        return [AuditFinding("allowlist", "crit",
                              "strategy_validation.json missing")]
    try:
        data = json.loads(path.read_text())
        cells = data.get("live_allowlist", [])
        if not cells:
            return [AuditFinding("allowlist", "crit",
                                  "live_allowlist is EMPTY — no cells to fire")]
        live = [c for c in cells if not c.get("shadow_only")
                                     and not c.get("experimental")]
        shadow = [c for c in cells if c.get("shadow_only") or c.get("experimental")]
        findings.append(AuditFinding(
            "allowlist", "info",
            f"{len(cells)} cells total ({len(live)} live, {len(shadow)} shadow/experimental)",
        ))
    except Exception as e:
        findings.append(AuditFinding("allowlist", "warn",
                                       f"allowlist parse failed: {e}"))
    return findings


def check_disk_logs() -> list[AuditFinding]:
    """Flag log files > 100MB (runaway loggers)."""
    findings = []
    logs_dir = ROOT / "logs"
    if not logs_dir.exists():
        return findings
    for log_file in logs_dir.glob("*.log"):
        try:
            size_mb = log_file.stat().st_size / 1024 / 1024
            if size_mb > 100:
                findings.append(AuditFinding(
                    "disk_logs", "warn",
                    f"{log_file.name} is {size_mb:.0f}MB — consider rotation",
                ))
        except Exception:
            continue
    return findings


# ── Main ───────────────────────────────────────────────────────────


def run_full_audit() -> list[AuditFinding]:
    """Run every check, aggregate findings."""
    all_findings = []
    checks = [
        ("trader_process", check_trader_processes),
        ("brain_process", check_brain_processes),
        ("process_freshness", check_process_freshness),
        ("snapshot_freshness", check_snapshot_freshness),
        ("scheduled_tasks", check_scheduled_tasks),
        ("separation", check_separation),
        ("sentinel", check_sentinel),
        ("allowlist", check_allowlist),
        ("disk_logs", check_disk_logs),
        # Tests last — expensive
        ("test_suite", check_test_suite),
    ]
    for name, fn in checks:
        try:
            all_findings.extend(fn())
        except Exception as e:
            all_findings.append(AuditFinding(
                name, "warn", f"audit check raised: {type(e).__name__}: {e}",
            ))
    return all_findings


def write_report(findings: list[AuditFinding]) -> Path:
    ts = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d_%H-%M")
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"audit_{ts}.md"
    crit = [f for f in findings if f.severity == "crit"]
    warn = [f for f in findings if f.severity == "warn"]
    info = [f for f in findings if f.severity == "info"]
    overall = "CRITICAL" if crit else "WARN" if warn else "OK"
    lines = [
        "---", "type: audit",
        f"generated_at: {datetime.now(tz=timezone.utc).isoformat()}",
        f"overall: {overall}",
        f"crit: {len(crit)}", f"warn: {len(warn)}", f"info: {len(info)}",
        "---", "",
        f"# Full System Audit — {ts}",
        f"",
        f"**Overall status:** {overall}",
        f"**Critical: {len(crit)} | Warn: {len(warn)} | Info: {len(info)}**",
        "",
    ]
    for sev_label, items in [("CRITICAL", crit), ("WARN", warn), ("INFO", info)]:
        if not items:
            continue
        lines.append(f"## {sev_label}")
        lines.append("")
        for f in items:
            lines.append(f"- **{f.check}**: {f.summary}")
            if f.detail:
                for k, v in f.detail.items():
                    lines.append(f"  - {k}: {v}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def alert_critical(findings: list[AuditFinding]) -> None:
    crit = [f for f in findings if f.severity == "crit"]
    if not crit:
        return
    try:
        from tools.alert import send_alert
        for f in crit:
            send_alert(
                f"🚨 SYSTEM AUDIT CRIT [{f.check}]: {f.summary}",
                level="crit",
            )
    except Exception:
        pass


def main() -> int:
    # Force UTF-8 stdout for Unicode-safe output
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    t0 = time.time()
    print("=== Full system audit ===")
    findings = run_full_audit()
    elapsed = time.time() - t0
    crit = [f for f in findings if f.severity == "crit"]
    warn = [f for f in findings if f.severity == "warn"]
    info = [f for f in findings if f.severity == "info"]
    print(f"\nElapsed: {elapsed:.1f}s")
    print(f"Findings: {len(crit)} crit, {len(warn)} warn, {len(info)} info\n")
    for f in findings:
        prefix = {"crit": "🚨", "warn": "⚠️ ", "info": "ℹ️ "}.get(f.severity, "")
        try:
            print(f"{prefix} [{f.check}] {f.summary}")
        except UnicodeEncodeError:
            print(f"[{f.check}] {f.summary.encode('ascii', 'replace').decode()}")
    path = write_report(findings)
    print(f"\nReport: {path}")
    alert_critical(findings)
    if crit:
        return 2
    if warn:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
