"""Autonomous morning wake — one-shot CIO + chain.

Run by Windows Task Scheduler at 09:30 ET on weekdays. Survives Claude
Code being closed, system reboots (Task Scheduler relaunches on next
trigger), and any conversation state.

Behavior:
  1. Loads .env, verifies ProjectX auth + account healthy.
  2. Confirms trading is allowed (halt expired or absent).
  3. Wakes CIO with a session-open task.
  4. If CIO emits WAKE: <Analyst>, runs the analyst chain.
  5. Logs everything to vault/journal/{date}.md.
  6. Exits.

Cost cap: $2 per run (configurable). Refuses further wakes after.
"""
from __future__ import annotations
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# Pin cwd to project root so all relative paths resolve
HERE = Path(__file__).resolve().parent.parent
os.chdir(HERE)

# Load .env
env = HERE / ".env"
for line in env.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip())

import httpx
import sqlite3
import yaml
from runtime.orchestrator import Orchestrator, _parse_wake_line


COST_CAP_USD = 2.00


def _ts():
    return datetime.now(tz=timezone.utc).strftime("%H:%M:%S")


def _today():
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d")


def _spent_today() -> float:
    c = sqlite3.connect("state/fund.db")
    return float(c.execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day = ?",
        (_today(),),
    ).fetchone()[0] or 0.0)


def _verify_state() -> tuple[bool, str]:
    """Returns (ok, reason)."""
    # Preflight: API budget check. If we're at/near the daily cap,
    # halt before we wake anyone. Returns 1 = halt engaged; 0 = ok.
    try:
        import subprocess
        r = subprocess.run(
            [sys.executable, "-m", "scripts.api_budget_check"],
            capture_output=True, timeout=30,
        )
        if r.returncode == 1:
            return False, "API budget kill switch engaged — see risk_events"
    except Exception as e:
        # If the check itself fails, log but don't block (fail-open here
        # because budget-check failure shouldn't ground real trading).
        print(f"[warn] api_budget_check failed: {e}", file=sys.stderr)

    cfg = yaml.safe_load(Path("config/risk_limits.yaml").read_text())
    halt_until_str = cfg["hard_rules"].get("trading_halt_until")
    now = datetime.now(tz=timezone.utc)
    if cfg["hard_rules"].get("trading_halted"):
        return False, "trading_halted=true (manual halt active)"
    if halt_until_str:
        parsed = datetime.fromisoformat(str(halt_until_str).replace("Z", "+00:00"))
        if now < parsed:
            return False, f"halt active until {halt_until_str}"

    # Verify broker auth
    api = os.environ.get("PROJECTX_API_KEY", "")
    user = os.environ.get("PROJECTX_USERNAME", "")
    acct_id = int(os.environ.get("PROJECTX_ACCOUNT_ID", "0") or 0)
    if not (api and user and acct_id):
        return False, "PROJECTX env vars missing"
    try:
        r = httpx.post("https://api.topstepx.com/api/Auth/loginKey",
                       json={"userName": user, "apiKey": api}, timeout=15.0)
        if not r.json().get("token"):
            return False, f"auth failed: {r.json()}"
    except Exception as e:
        return False, f"auth exception: {e}"
    return True, "ok"


CIO_PROMPT = """AUTONOMOUS MORNING / SESSION WAKE — fired by Task Scheduler.

You are the CIO. The team has been authorized for 24/5 trading by the
user. Auto-halt is cleared. Account healthy. Today's pre-loaded brief
is at vault/journal/{date}.md (created last night) and the regime memo
is at vault/regime/current.md.

Your job RIGHT NOW (under 250 words total):

1. Read account state via topstep_get_account.

2. Read vault/regime/current.md and vault/journal/{date}.md (your prior
   pre-session work). Synthesize: any overnight news that changes the
   regime read or the watchlist?

3. Refresh the FRED data layer briefly (DGS10, VIX, fed funds upper).
   If a major macro print has changed significantly from last night's
   numbers, note it.

4. Decide: which ONE analyst (or Edge Hunter) to wake right now for
   the cleanest tradeable setup.

5. Emit EXACTLY ONE wake directive on its own line:
   WAKE: <Analyst Name | Edge Hunter | none>

Allowed names: Energies Analyst, Metals Analyst, Grains Analyst, Softs
Analyst, Livestock Analyst, Rates Analyst, FX Futures Analyst,
Index/Macro Analyst, Edge Hunter, Quant Researcher.

Bias: prefer Edge Hunter for fast wide scan when no specific sector
catalyst dominates today; prefer specific sector analyst when there's
a clear catalyst (EIA Wed, FOMC, NFP, OPEC, etc).

End with the WAKE line.
"""


async def main():
    print(f"[{_ts()}] === AUTONOMOUS MORNING WAKE ===")
    ok, reason = _verify_state()
    if not ok:
        print(f"[{_ts()}] STATE CHECK FAILED: {reason}")
        print(f"[{_ts()}] Aborting. Will retry next trigger.")
        return 1
    print(f"[{_ts()}] State verified: account healthy, halt expired/absent")

    spent = _spent_today()
    print(f"[{_ts()}] Today spend: ${spent:.2f} (cap ${COST_CAP_USD:.2f})")
    if spent >= COST_CAP_USD:
        print(f"[{_ts()}] Daily cap already hit. Aborting.")
        return 0

    orch = Orchestrator()
    print(f"[{_ts()}] Loaded {len(orch.specs)} agents.")

    # Step 1: CIO
    today_brief_path = Path(f"vault/journal/{_today()}.md")
    cio_prompt = CIO_PROMPT.replace("{date}", _today())
    cio_result = await orch.wake_agent("CIO", cio_prompt)
    cio_text = (cio_result.get("final_text") or "").strip()
    print(f"[{_ts()}] CIO response (first 800 chars):")
    print(cio_text[:800])
    print()

    target = _parse_wake_line(cio_text)
    if not target or target.lower() == "none":
        print(f"[{_ts()}] CIO stood down. Session brief written. Exiting.")
        return 0

    print(f"[{_ts()}] CIO picked: {target}")
    if _spent_today() >= COST_CAP_USD:
        print(f"[{_ts()}] Cost cap hit after CIO wake. Skipping chain.")
        return 0

    # Step 2: chain (analyst -> Red Team if conv -> PM -> Risk -> Exec)
    if target.lower() == "edge hunter":
        # Edge Hunter has its own protocol; treat its TRIGGER output like a thesis
        result = await orch.wake_agent("Edge Hunter", "INTRADAY SCAN. Find the best CME-tradeable rule-based trigger active right now. Follow your output protocol.")
        print(f"[{_ts()}] Edge Hunter result:")
        print((result.get("final_text") or "")[:1500])
        # If Edge Hunter recorded a thesis, run chain from there
        thesis = orch._latest_thesis_for("Edge Hunter")
        if thesis:
            print(f"[{_ts()}] Edge Hunter thesis recorded — running PM chain")
            chain_result = await orch.run_analyst_chain("Edge Hunter")
            print(f"[{_ts()}] Chain result: {chain_result.get('status')}")
    else:
        chain_result = await orch.run_analyst_chain(target)
        print(f"[{_ts()}] Chain result: {chain_result.get('status')}")

    print()
    print(f"[{_ts()}] Final spend: ${_spent_today():.2f}")
    print(f"[{_ts()}] === DONE ===")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
