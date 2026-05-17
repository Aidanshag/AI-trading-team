---
name: feedback-trader-shutdown-for-deploys
description: Trader shutdown is acceptable during overnight/weekend deploy windows to ship patches that require restart. User authorized 2026-05-15.
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 01330334-e95e-4182-b81f-d9cbbd00f2f1
---

When working autonomously overnight or on weekends, shutting down the trader to restart it (so patches take effect) is acceptable.

**Why:** Patches to `tools/profit_protect.py`, `tools/bracket_placement.py`, `scripts/live_trader.py`, etc. are imported at trader startup — they're inert until restart. The "trader-running caveat" of "patch won't take effect until restart" can be resolved during off-hours by shutting down + relaunching. Trader downtime overnight or weekend isn't lost edge; it's normal maintenance window.

**How to apply:**
- Live trading hours (Sun 18:00 ET → Fri 17:00 ET): restart only when no open positions and during low-signal windows. Wait for current trades to exit naturally first.
- Weekend window (Fri 17:00 ET → Sun 18:00 ET): full restart freedom; deploy aggressively.
- Overnight Mon-Fri: case-by-case. Asian session is slow signal; restart is usually fine. Watch for in-flight positions first.
- Always: confirm the scheduled task (`FundLiveTraderEnsureRunning`) will relaunch on next trigger, OR launch the trader manually after shutdown.
- Sequence: (1) verify no open positions, (2) `taskkill` the python.exe trader process, (3) re-launch via `scripts/restart-live-trader-if-dead.ps1` (idempotent), (4) verify new process is up + scanning.

Related: [[feedback-restart-after-patch]] (general rule that imported code needs restart), [[feedback-do-dont-backlog]] (do-don't-queue principle that motivates aggressive deploy cadence).
