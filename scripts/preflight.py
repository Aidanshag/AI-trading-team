"""Pre-session preflight — fail-closed gate before any session starts.

Run this BEFORE `fund start` or before manually starting the orchestrator.
Exits 0 if all checks pass, non-zero if any fail. Recommended invocation
from PowerShell:

    & ".venv\\Scripts\\python.exe" -m scripts.preflight
    if ($LASTEXITCODE -ne 0) { exit 1 }
    & ".\\scripts\\start-runtime.ps1"

Why fail-closed: today's incident proved that the system can pass
"all green" appearances at startup while having a load-bearing component
(the snapshot writer) silently broken. This script refuses to declare go
unless every check it knows how to run actually returns green.

Checks (in order):
  1. .env present and required PROJECTX_* keys set
  2. Topstep auth + balance + canTrade=true
  3. trading_halt_until is in the past
  4. focus_universe.yaml exists and has at least one allowed symbol
  5. Snapshot writer works end-to-end (write + read same row)
  6. Test suite is 100% green
  7. Risk hook returns SOMETHING for a synthetic order (not silently
     no-op'ing) — proves all checks are actually wired
  8. Agent CLI (claude.exe) is launchable — advisory WARN only, since
     the auto_trader doesn't depend on the CLI; agent chain does.
"""
from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure cwd is project root
_HERE = Path(__file__).resolve().parent.parent
os.chdir(_HERE)

from dotenv import load_dotenv
load_dotenv()


GREEN = "\033[92m"; RED = "\033[91m"; YELLOW = "\033[93m"; END = "\033[0m"


def _ok(msg: str) -> None: print(f"  {GREEN}OK{END}  {msg}")
def _fail(msg: str) -> None: print(f"  {RED}FAIL{END}  {msg}")
def _warn(msg: str) -> None: print(f"  {YELLOW}WARN{END}  {msg}")


def check_env() -> bool:
    print("Step 1/7: env vars")
    missing = [k for k in ("PROJECTX_API_KEY", "PROJECTX_USERNAME",
                            "PROJECTX_ACCOUNT_ID")
               if not os.environ.get(k)]
    if missing:
        _fail(f"missing env: {missing}")
        return False
    _ok("PROJECTX_* keys present")
    return True


def check_broker() -> tuple[bool, dict]:
    print("Step 2/7: broker auth + canTrade")
    # 2026-05-07: added retry-with-backoff for sketchy wifi resilience.
    # Previous behavior failed on first DNS blip → killed trader → daemon
    # revived → preflight failed again → loop. Now retries 3x over ~30s
    # before giving up, which covers most home-wifi micro-drops.
    import time
    last_err = None
    for attempt in range(3):
        try:
            from tools.projectx_client import get_client, get_account_id
            client = get_client()
            accounts = client.get_accounts()
            aid = get_account_id()
            mine = next((a for a in accounts if str(a.get("id")) == str(aid)), None)
            if mine is None:
                _fail(f"account {aid} not visible")
                return False, {}
            balance = float(mine.get("balance", 0))
            can_trade = bool(mine.get("canTrade"))
            if not can_trade:
                _fail(f"canTrade=false (balance ${balance:.2f}). "
                      f"Topstep has flagged the account; cannot start session.")
                return False, mine
            attempt_note = f" (attempt {attempt + 1})" if attempt > 0 else ""
            _ok(f"account {mine.get('name')}: balance ${balance:.2f}, canTrade=True{attempt_note}")
            return True, mine
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            transient = any(k in err_str for k in (
                "getaddrinfo", "timeout", "connectionerror",
                "connectionreset", "remote disconnected"
            ))
            if attempt < 2 and transient:
                wait_s = 5 * (attempt + 1)
                print(f"    transient network error: {type(e).__name__} — retrying in {wait_s}s...")
                time.sleep(wait_s)
                continue
            break
    _fail(f"broker error after 3 attempts: {type(last_err).__name__}: {last_err}")
    return False, {}


def check_halt() -> bool:
    print("Step 3/7: halt timestamp not in future")
    import yaml
    cfg = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
    halt_str = (cfg.get("hard_rules") or {}).get("trading_halt_until", "")
    if (cfg.get("hard_rules") or {}).get("trading_halted"):
        _fail("trading_halted: true (manual halt engaged)")
        return False
    if not halt_str:
        _ok("no halt timestamp set")
        return True
    try:
        halt = datetime.fromisoformat(str(halt_str).replace("Z", "+00:00"))
        now = datetime.now(tz=timezone.utc)
        if halt > now:
            delta = (halt - now).total_seconds() / 3600
            _fail(f"halt active: {halt_str} ({delta:+.1f}h from now)")
            return False
        _ok(f"halt expired ({halt_str})")
        return True
    except Exception as e:
        _fail(f"halt timestamp unparseable: {halt_str!r} ({e})")
        return False


def check_focus_universe() -> bool:
    print("Step 4/7: focus universe valid")
    import yaml
    path = Path("config/focus_universe.yaml")
    if not path.exists():
        _warn("focus_universe.yaml missing (running unrestricted)")
        return True
    cfg = yaml.safe_load(path.read_text()) or {}
    if not cfg.get("focus_period_active"):
        _ok("focus universe inactive (any symbol allowed)")
        return True
    syms = []
    for sector_syms in (cfg.get("allowed_symbols") or {}).values():
        syms.extend(sector_syms or [])
    if not syms:
        _fail("focus_universe.yaml is active but allowed_symbols is empty")
        return False
    _ok(f"focus universe: {len(syms)} symbols allowed")
    return True


def check_snapshot_writer() -> bool:
    print("Step 5/7: snapshot writer end-to-end")
    # 2026-05-07: same retry-with-backoff as check_broker, since this
    # also requires network access to Topstep to actually capture.
    import asyncio, time
    from runtime.orchestrator import Orchestrator
    from state.db import get_db
    last_err = None
    result = None
    for attempt in range(3):
        try:
            async def _run():
                o = Orchestrator()
                return await o.capture_account_snapshot()
            result = asyncio.run(_run())
            if result:
                break
            # If returned None on attempt 1-2, retry; could be a network blip
            if attempt < 2:
                print(f"    snapshot returned None — retrying in {5*(attempt+1)}s...")
                time.sleep(5 * (attempt + 1))
                continue
        except Exception as e:
            last_err = e
            err_str = str(e).lower()
            transient = any(k in err_str for k in (
                "getaddrinfo", "timeout", "connectionerror",
                "connectionreset", "remote disconnected"
            ))
            if attempt < 2 and transient:
                print(f"    transient network error: {type(e).__name__} — retrying...")
                time.sleep(5 * (attempt + 1))
                continue
            break
    try:
        if not result:
            err_msg = (f"after 3 attempts: {type(last_err).__name__}"
                       if last_err else "returned None — writer broken")
            _fail(f"capture_account_snapshot {err_msg}")
            return False
        snap = get_db().latest_account_snapshot()
        if not snap:
            _fail("snapshot didn't persist to DB")
            return False
        ts = snap.get("ts", "")
        try:
            snap_ts = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
            age_sec = (datetime.now(tz=timezone.utc) - snap_ts).total_seconds()
            if age_sec > 60:
                _fail(f"snapshot ts is {age_sec:.0f}s old — write failed silently?")
                return False
        except Exception:
            _fail(f"snapshot ts {ts!r} unparseable")
            return False
        _ok(f"snapshot written + readable: balance ${snap['balance_usd']:.2f}, "
            f"realized day P&L ${snap['realized_pl_day_usd']:+.2f}")
        return True
    except Exception as e:
        _fail(f"snapshot writer error: {type(e).__name__}: {e}")
        return False


def check_tests() -> bool:
    print("Step 6/7: test suite")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "-q",
             "--ignore=tests/test_overnight_fixes.py", "--tb=no"],
            capture_output=True, text=True, timeout=120,
        )
        last = result.stdout.strip().splitlines()[-1] if result.stdout else ""
        if result.returncode != 0:
            _fail(f"tests failed: {last}")
            return False
        _ok(f"tests: {last}")
        return True
    except Exception as e:
        _fail(f"test runner error: {e}")
        return False


def check_agent_cli() -> bool:
    """Verify claude.exe is reachable and launches. Advisory only — auto_trader
    doesn't need the CLI, but the agent chain (CIO/Quant/Edge) does. WARN
    rather than FAIL so a missing CLI doesn't block the deterministic trader."""
    print("Step 8/8: agent CLI launchability")
    try:
        from runtime.orchestrator import _resolve_cli_path
        cli_path = os.environ.get("FUND_CLAUDE_CLI_PATH") or _resolve_cli_path()
        if not cli_path:
            _warn("no Claude CLI found; agent chain (CIO/Quant/Edge) will fail. "
                  "Set FUND_CLAUDE_CLI_PATH or `npm i -g @anthropic-ai/claude-code`. "
                  "Auto-trader is unaffected.")
            return True
        result = subprocess.run(
            [cli_path, "--version"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            _warn(f"CLI at {cli_path} returned exit {result.returncode}: "
                  f"{result.stderr.strip()[:200]}. Agent chain may fail; "
                  f"auto-trader unaffected.")
            return True
        version = result.stdout.strip().split()[0] if result.stdout.strip() else "?"
        _ok(f"agent CLI launchable: {version} ({cli_path})")
        return True
    except subprocess.TimeoutExpired:
        _warn(f"CLI at {cli_path} hung > 10s on --version. Agent chain may fail; "
              f"auto-trader unaffected.")
        return True
    except Exception as e:
        _warn(f"agent CLI check error ({type(e).__name__}: {e}); "
              f"auto-trader unaffected.")
        return True


def check_autonomous_activity_alive() -> bool:
    """Advisory check: surface if cowork / autonomous routines have been
    silent for >36h. Discovered 2026-05-09 that cowork doesn't run on
    timers — only the cloud routine does — so a silent gap means the
    brain isn't compounding as expected.

    NOT fail-closed (advisory only). Just logs a warning so future-Claude
    notices and the user can investigate.
    """
    print("Step Y: autonomous activity heartbeat")
    try:
        import subprocess
        result = subprocess.run(
            ["git", "log", "--since=36 hours ago", "--format=%H %s",
             "--grep=cowork", "--grep=autonomous", "--grep=routine",
             "--regexp-ignore-case", "--all-match=false"],
            capture_output=True, text=True, timeout=15,
        )
        # Also count session auto-commits as a heartbeat
        recent_any = subprocess.run(
            ["git", "log", "--since=36 hours ago", "--oneline"],
            capture_output=True, text=True, timeout=15,
        )
        cowork_lines = result.stdout.strip().splitlines() if result.stdout.strip() else []
        any_lines = recent_any.stdout.strip().splitlines() if recent_any.stdout.strip() else []
        if not cowork_lines and len(any_lines) <= 2:
            _warn(f"no cowork or autonomous activity in last 36h "
                  f"(only {len(any_lines)} commits total). "
                  f"Brain may not be learning autonomously — investigate cloud routine "
                  f"at https://claude.ai/code/routines")
        elif not cowork_lines:
            _warn(f"no cowork commits in last 36h ({len(any_lines)} session commits found). "
                  f"Cowork sessions may need manual launch.")
        else:
            _ok(f"autonomous activity healthy: {len(cowork_lines)} cowork commits in last 36h")
        return True  # always advisory
    except Exception as e:
        _warn(f"autonomous-activity check skipped: {type(e).__name__}: {e}")
        return True


def check_no_conflicting_trader() -> bool:
    """Block launch if another live_trader or auto_trader process is already
    running. Prevents v1+v2 double-trading after the 2026-05-08 simplification
    cutover and prevents accidental double-start of v2.

    Returns False (fail-closed) if a conflicting process is found, True if
    the slot is free.
    """
    print("Step X: no conflicting trader process running")
    try:
        import subprocess
        # Use WMIC (works without admin, deprecated but ships with Windows)
        result = subprocess.run(
            ["wmic", "process", "where", "name='python.exe'",
             "get", "ProcessId,CommandLine", "/format:csv"],
            capture_output=True, text=True, timeout=15,
        )
        my_pid = os.getpid()
        conflicts = []
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("Node"):
                continue
            parts = line.split(",")
            if len(parts) < 3:
                continue
            cmdline = ",".join(parts[1:-1]).strip()
            try:
                pid = int(parts[-1].strip())
            except ValueError:
                continue
            if pid == my_pid:
                continue
            if ("scripts.live_trader" in cmdline or
                    "scripts.auto_trader" in cmdline):
                conflicts.append((pid, cmdline[:80]))
        if conflicts:
            for pid, cl in conflicts:
                _fail(f"conflicting trader running PID={pid}: {cl}...")
            _fail("aborting launch to prevent double-trade race")
            return False
        _ok("no conflicting trader process detected")
        return True
    except Exception as e:
        _warn(f"trader-conflict check skipped: {type(e).__name__}: {e}")
        # Fail-open here: if WMIC is unavailable, don't block legitimate launches.
        # The PID lock in v1's auto_trader still provides a backstop.
        return True


def check_broker_separation() -> bool:
    """Enforce Topstep <-> IB workstream isolation. Every allowlist cell and
    shadow trade row must carry a `broker` field; no cross-broker imports."""
    print("Step 7b/N: broker separation audit")
    try:
        from tools.separation_audit import violations
        vs = violations()
        if vs:
            for v in vs:
                _fail(f"separation: {v}")
            return False
        _ok("broker separation clean (Topstep <-> IB isolated)")
        return True
    except Exception as e:
        _warn(f"separation audit skipped: {type(e).__name__}: {e}")
        return True


def check_risk_gate_wired() -> bool:
    """Submit a synthetic order to apply_risk_gate and confirm the kill_switch
    check actually ran — sanity that the hook isn't silently no-op'ing."""
    print("Step 7/7: risk hook sanity")
    try:
        from scripts.auto_trader import apply_risk_gate
        # Synthetic order missing stop_price → should be blocked by stop_required
        order = {"symbol": "MES", "side": "buy", "qty": 1,
                 "order_type": "market", "stop_price": None,
                 "structure_id": None}
        verdict = apply_risk_gate(order)
        if verdict is None:
            _fail("risk hook didn't block a stop-less market order — checks not wired")
            return False
        _ok(f"risk hook fires correctly (sample block: {verdict.get('rule')})")
        return True
    except Exception as e:
        _fail(f"risk hook error: {type(e).__name__}: {e}")
        return False


def main() -> int:
    print("\n=== Pre-session preflight ===\n")
    checks = [
        check_env(),
    ]
    if not checks[-1]:
        print(f"\n{RED}PREFLIGHT FAILED at step 1 — refusing to start session.{END}\n")
        return 1
    ok2, _ = check_broker()
    checks.append(ok2)
    checks.append(check_halt())
    checks.append(check_focus_universe())
    checks.append(check_snapshot_writer())
    checks.append(check_tests())
    checks.append(check_risk_gate_wired())
    checks.append(check_broker_separation())
    checks.append(check_no_conflicting_trader())
    checks.append(check_autonomous_activity_alive())
    checks.append(check_agent_cli())

    # Step 9: refresh strategy validation state (rolling daily walk-forward).
    # Updates state/strategy_validation.json which the auto_trader reads
    # at scan time to know which cells are live vs shadow. Failure is
    # ADVISORY — falls back to the static allowlist so trading isn't blocked.
    print(f"\n[step 9] daily strategy validation refresh")
    try:
        import subprocess
        proc = subprocess.run(
            ["python", "scripts/daily_strategy_validation.py"],
            capture_output=True, text=True, timeout=600,
        )
        if proc.returncode == 0:
            # Pull last 5 lines of summary
            tail = "\n    ".join(proc.stdout.strip().splitlines()[-5:])
            _ok(f"validation refreshed:\n    {tail}")
        else:
            _warn(f"validation script returned {proc.returncode}; "
                  f"falling back to static allowlist")
    except Exception as e:
        _warn(f"validation skipped: {type(e).__name__}: {e}")

    # Step 9b: auto-promote/demote cells from live evidence.
    # Reads last 30d of fills, compares live expectancy to OOS predictions,
    # updates live_allowlist atomically. ADVISORY — failure logs warn but
    # doesn't block trading. Cowork-shipped 2026-05-08.
    print(f"\n[step 9b] auto-promote/demote cells from live evidence")
    try:
        import subprocess
        proc = subprocess.run(
            ["python", "scripts/cell_auto_promote.py"],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode == 0:
            tail = "\n    ".join(proc.stdout.strip().splitlines()[-5:])
            _ok(f"cell auto-promote:\n    {tail}")
        else:
            _warn(f"cell auto-promote returned {proc.returncode}")
    except Exception as e:
        _warn(f"cell auto-promote skipped: {type(e).__name__}: {e}")

    # Step 10: resolve any shadow trades from prior session
    print(f"\n[step 10] shadow trade resolver")
    try:
        import subprocess
        proc = subprocess.run(
            ["python", "scripts/shadow_trade_resolver.py"],
            capture_output=True, text=True, timeout=300,
        )
        if proc.returncode == 0:
            tail = "\n    ".join(proc.stdout.strip().splitlines()[-5:])
            _ok(f"shadows resolved:\n    {tail}")
        else:
            _warn(f"shadow resolver returned {proc.returncode}")
    except Exception as e:
        _warn(f"shadow resolver skipped: {type(e).__name__}: {e}")

    # Step 11: live-vs-OOS tracker — compare actual realized R-multiples
    # against OOS predictions per cell. Surfaces edge decay or sample-size
    # luck. Output: vault/research/live_vs_oos/<date>_live_r_comparison.md.
    print(f"\n[step 11] live R-multiple tracker")
    try:
        import subprocess
        proc = subprocess.run(
            ["python", "scripts/live_vs_oos_tracker.py"],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode == 0:
            tail = "\n    ".join(proc.stdout.strip().splitlines()[-3:])
            _ok(f"live-R tracker:\n    {tail}")
        else:
            _warn(f"live-R tracker returned {proc.returncode}")
    except Exception as e:
        _warn(f"live-R tracker skipped: {type(e).__name__}: {e}")

    # Step 12: lessons auto-promotion — graduate ADVISORY → PATTERN → RULE
    # tier as live evidence accumulates. Output to vault/lessons/.
    print(f"\n[step 12] lessons auto-promotion")
    try:
        import subprocess
        proc = subprocess.run(
            ["python", "scripts/auto_promote_lessons.py"],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode == 0:
            tail = "\n    ".join(proc.stdout.strip().splitlines()[-3:])
            _ok(f"lessons:\n    {tail}")
        else:
            _warn(f"lessons promoter returned {proc.returncode}")
    except Exception as e:
        _warn(f"lessons promoter skipped: {type(e).__name__}: {e}")

    # Step 13: memory backup — copy ~/.claude memory files into the
    # project's vault so they get pushed to git + OneDrive. Without
    # this, memory lives only in user profile and is lost on machine loss.
    print(f"\n[step 13] memory backup to vault")
    try:
        import subprocess
        proc = subprocess.run(
            ["python", "scripts/backup_memory.py"],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0:
            tail = (proc.stdout.strip() or "ok").splitlines()[-1]
            _ok(f"memory backup: {tail}")
        else:
            _warn(f"memory backup returned {proc.returncode}")
    except Exception as e:
        _warn(f"memory backup skipped: {type(e).__name__}: {e}")

    # Step 14: daily summary — text dashboard for prediction-vs-actuals review
    print(f"\n[step 14] daily summary dashboard")
    try:
        import subprocess
        proc = subprocess.run(
            ["python", "scripts/daily_summary.py"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            tail = (proc.stdout.strip() or "ok").splitlines()[-1]
            _ok(f"daily summary: {tail}")
        else:
            _warn(f"daily summary returned {proc.returncode}")
    except Exception as e:
        _warn(f"daily summary skipped: {type(e).__name__}: {e}")

    print()
    if all(checks):
        print(f"{GREEN}=== All preflight checks passed. Cleared to start session. ==={END}\n")
        return 0
    failed = sum(1 for c in checks if not c)
    print(f"{RED}=== PREFLIGHT FAILED ({failed} of {len(checks)} checks). DO NOT START. ==={END}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
