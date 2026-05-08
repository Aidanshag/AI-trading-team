---
name: ALWAYS restart the live trader after patching code it imports
description: Python imports are bound at process start. Patches to reconcile_positions.py, hooks/, tools/, or any module imported by auto_trader take effect ONLY after the trader process is restarted. Forgetting to restart = the patch is inert.
type: feedback
originSessionId: b1c69b67-a794-46cc-bb06-6e08fbeea607
---
On 2026-05-04 I patched `scripts/reconcile_positions.py` to auto-flatten phantom positions (OCO race fix). I tested the patch in isolation, confirmed it worked, declared the system safe, and told the user to sleep.

**Then the same bug fired three more hours later.** A GC buy-stop fired into a phantom long, the user manually closed for $1190, the patched auto-flatten DID NOT trigger.

Reason: the running trader process started at 18:32:51 UTC, my patch landed at ~22:53 UTC. Python imports are bound at process start. The running trader was still executing the pre-patch reconcile_positions code from memory. My patch was inert.

**Rule: after patching ANY .py file imported by the auto_trader, restart the trader.**

Files to watch:
- `scripts/auto_trader.py` itself
- `scripts/reconcile_positions.py`
- `tools/topstep.py` / `tools/projectx_client.py`
- `hooks/risk_gate.py`
- `state/db.py` / `state/schema.sql`
- `tools/backtest/strategies.py` (if strategy code edited)
- `tools/strategy_performance.py`
- Any config YAML that auto_trader reloads dynamically (those DON'T need restart — they're re-read each scan)

**How to restart safely:**
1. `Get-Process -Name python | Stop-Process -Force` (or use TaskKill)
2. Clear stale `logs/auto_trader.pid`
3. Run `python -m scripts.trader_watchdog --force` — uses the patched Popen revival path
4. Verify new python PID exists, snapshot heartbeat fresh within 60s
5. `python -c "import inspect; from <module> import <fn>; assert <expected_text> in inspect.getsource(<fn>)"` to confirm patched code loaded

**Cost of forgetting:** patches are silent failures. The bug appears identical to "no patch yet" from the user's perspective. Trust erosion.

**Don't:** declare the system patched until you've restarted AND verified the patched code is in memory.
