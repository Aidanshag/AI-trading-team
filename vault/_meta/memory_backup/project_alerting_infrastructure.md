---
name: Project — Discord alerting + unified trader recovery task (2026-05-10)
description: Crash-detection layer wired 2026-05-10. Single scheduled task + Discord webhook ping when trader has to be restarted or relaunch fails.
type: project
originSessionId: 050d245a-e481-4632-9707-935db0dc239f
---
Built 2026-05-10 (Sunday night, pre-Combine).

**Why**: Tonight was the first live_trader overnight run. User asked for "stop a silent crash overnight." Answered with detection (Discord alerts) rather than aggressive auto-revive triggers — measure-first stance per the close-the-gap reframe.

**How to apply**:
- If a future session adds a new trader entrypoint, point its scheduled task to `scripts/restart-live-trader-if-dead.ps1` instead of writing a new launcher. That script is the single idempotent path.
- If we ever need additional alert paths (mid-day death, watchdog ping), build on `tools/alert.py` rather than rolling new alert code.
- Do NOT promote to aggressive multi-hour recovery triggers without evidence of recurring overnight deaths. The 5/8 watchdog thrashing pattern in `logs/watchdog.log` (29 revivals masking the real bug) is the cautionary tale.

**Components**:

1. `tools/alert.py` — Discord webhook sender. `send_alert(msg, level)`. Reads `DISCORD_WEBHOOK_URL` from `.env` (lightweight loader, no python-dotenv dep). Levels: info / warn / crit. Username "fund-alert". Silently no-ops if webhook unset.

2. `scripts/restart-live-trader-if-dead.ps1` — idempotent launcher. Process-table scan for `scripts.live_trader` in python.exe command lines. If found: log + exit. If not: Start-Process detached + warn alert. If launch itself fails: crit alert.

3. `FundLiveTraderEnsureRunning` scheduled task — one task, two triggers (Sun 17:00 ET + Mon-Fri 06:30 ET). Both invoke restart-live-trader-if-dead.ps1 via `-File`. Replaces the prior FundLiveTraderSundayKickstart + FundLiveTraderMonMorning split (deleted).

**Coverage gaps to know about**:
- Mid-day death (e.g., trader dies at 14:00) → no alert until next scheduled fire (Mon 06:30 ET). For tighter coverage, add a recurring watchdog scheduled task that reads `account_snapshots.ts` freshness and alerts on stale, but only do this AFTER observing real death frequency. Don't pre-build.
- Hard kills (SIGKILL, segfault, OOM) → process disappears with no in-process alert path. The restart task catches them at next fire, that's the safety net.
- live_trader.py itself has NO atexit/signal alert hook. Deliberate — keep the "knife" file thin per the continuous-trim directive. Death is detected externally via process-absence at next scheduled check.

**Replaced / deleted infrastructure**:
- `FundLiveTraderSundayKickstart` (one-shot Sunday task, multi-line `-Command` quoting bug that failed its first real fire at 2026-05-10 17:00 with LastTaskResult=1)
- `FundLiveTraderMonMorning` (separate Mon-Fri task, redundant once merged)
- `FundAutoTraderDaily` still registered but DISABLED (points to old auto_trader.py). Harmless artifact, can be unregistered when the two-trader split is fully resolved.
