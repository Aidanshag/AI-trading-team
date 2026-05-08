---
type: deployment_runbook
event: simplification/layer1-minimal-knife → master
target_deployment: 2026-05-10 17:00 ET (Sunday Globex reopen)
created: 2026-05-08
---

# Deployment runbook — Layer 1 simplified trader

## Background

The v1 `auto_trader.py` (2,929 lines) accumulated complexity that made
it un-debuggable: orphan cleanup races, misdirected-leg false positives,
multi-tier filters, time-window gates, etc. After 4 days of intermittent
trading bugs, diagnosed the root cause: `MIN_STOP_TICKS=3` for gap_fill
was rejecting 100% of signals because their natural stops are sub-tick.

The simplified `live_trader.py` (~480 lines) replaces v1. Brain (Layer 2:
agents, vault, validation pipeline, walk-forward) is unchanged.

## What's preserved (NOT TOUCHED)

- `scripts/auto_trader.py` — original v1, untouched
- `scripts/auto_trader_v1_complex.py` — explicit archive copy
- All `tools/`, `runtime/`, `hooks/`, `agents/`, `state/`, `config/` files
- All `vault/_meta/`, `vault/lessons/`, `vault/research/`, `vault/sessions/`
- All memory entries at `~/.claude/projects/.../memory/`
- All Cowork coordination + handoff log

## What's added

- `scripts/live_trader.py` — new ~480-line trader (alongside v1, not replacing)
- `scripts/install-livetrader-daily.ps1` — installer for new scheduled task
- `tests/test_live_trader.py` — 20 unit tests, all passing
- `vault/_meta/deployment_runbook_layer1_simplification.md` — this file
- `vault/lessons/2026-05-08_layer1_simplification.md` — TODO before deploy

## Deployment steps (Sunday 2026-05-10)

### Pre-deployment (Saturday or earlier)

1. **Branch check**: ensure on `simplification/layer1-minimal-knife`
2. **Test suite**: `python -m pytest tests/test_live_trader.py -q` → 20 passing
3. **Dry-run**: `python -m scripts.live_trader --once --dry-run` → no errors
4. **Paper-mode**: `python -m scripts.live_trader --once --paper` → no errors
5. **Compile check**: all key files compile cleanly

### Deployment cutover (Sunday afternoon, before 5 PM ET Globex reopen)

1. **Merge to master**:
   ```bash
   git checkout master
   git merge simplification/layer1-minimal-knife
   git push origin master
   ```

2. **Install new scheduled task** (run as Administrator):
   ```powershell
   powershell.exe -ExecutionPolicy Bypass -File scripts\install-livetrader-daily.ps1
   ```

3. **Disable old v1 task** (don't delete — keep for rollback):
   ```powershell
   Disable-ScheduledTask -TaskName FundAutoTraderDaily
   ```

4. **Verify both states**:
   ```powershell
   Get-ScheduledTask -TaskName FundLiveTraderDaily | Format-Table TaskName, State
   Get-ScheduledTask -TaskName FundAutoTraderDaily | Format-Table TaskName, State
   ```
   Expected: `FundLiveTraderDaily`=Ready, `FundAutoTraderDaily`=Disabled

5. **Stop any running v1 trader process**:
   ```powershell
   $pid_file = "logs\auto_trader.pid"
   if (Test-Path $pid_file) {
       $pid = Get-Content $pid_file
       Stop-Process -Id $pid -ErrorAction SilentlyContinue
   }
   ```

6. **Manually trigger live_trader for first run**:
   ```powershell
   Start-ScheduledTask -TaskName FundLiveTraderDaily
   ```
   Then verify it's running:
   ```powershell
   Get-ScheduledTask -TaskName FundLiveTraderDaily | Select-Object -ExpandProperty State
   ```

7. **Watch logs** for first 30 minutes after Globex reopen (5 PM ET):
   ```bash
   Get-Content -Path logs\livetrader_$(Get-Date -Format yyyyMMdd).log -Wait
   ```

### Rollback procedure (if v2 has issues)

1. Halt v2 immediately:
   ```powershell
   Disable-ScheduledTask -TaskName FundLiveTraderDaily
   New-Item -ItemType File -Path state\live_trader_halt
   ```
2. Stop the running process:
   ```powershell
   Get-Process python | Where-Object { $_.MainWindowTitle -like "*live_trader*" } | Stop-Process
   ```
3. Re-enable v1:
   ```powershell
   Enable-ScheduledTask -TaskName FundAutoTraderDaily
   Start-ScheduledTask -TaskName FundAutoTraderDaily
   ```
4. v1 picks up from same `state/strategy_validation.json` and trades.

No data loss — both readers use the same DB.

## Monitoring tomorrow morning

After Sunday 5 PM ET → Monday 8 AM ET first overnight run, check:

- [ ] `logs/livetrader_2026-05-10.log` has scan summaries
- [ ] `state/fund.db:orders WHERE agent='live_trader'` has rows
- [ ] `state/fund.db:account_snapshots` has fresh entries every ~5 min
- [ ] No `daily_cap_hit` events
- [ ] No `dll_halt` events
- [ ] Per-trade fill data captured (entry/exit avg_fill_price set)

## Differences from v1

| Aspect | v1 (auto_trader.py) | v2 (live_trader.py) |
|---|---|---|
| Lines of code | 2,929 | ~480 |
| Strategy roster | hardcoded (24 strategies) | reads from `live_allowlist` |
| Cell allowlist | static + dynamic + filter overlay | reads from `live_allowlist` |
| Time windows | `PREFERRED_TIME_WINDOWS_UTC` overlay | none — brain decides |
| Min stop ticks | per-sector (3-10) | none — accepts strategy's natural stops |
| Orphan/misdirected cleanup | yes (caused bugs) | none — bracket OCO trusted |
| Daily target lock + cancel_working | yes | none — DLL hard kill is the only floor |
| Trailing profit lock (5 tiers) | yes | none — bracket target is the only profit-take |
| Per-trade loss cap | $200 | $150 |
| Daily DLL | $1,000 (Topstep) + $500 internal | $1,000 (Topstep) only |
| Max trades / day | 8 | 8 |
| Cooldown | 45 min same-symbol | 45 min same-symbol (kept) |
| Open-position bound | `rates_curve.max_net_contracts: 1` | "skip if any position open" (simpler) |
| Watchdog integration | DB heartbeat | DB heartbeat (same — no change needed) |

## Why each cut

- **Strategy roster**: brain's `live_allowlist` is the authoritative list
- **Cell allowlist tiers**: collapsed into `live_allowlist`
- **Time windows**: brain's validation already produces session-aware cells
- **Min stop ticks**: was the cause of v1's 0-trade nights; brain's validation
  already respects whatever stops the strategy generates
- **Orphan/misdirected cleanup**: was cancelling protective legs prematurely;
  trust the broker's OCO + per-trade loss-cap as backstop
- **Trailing profit lock + daily target action**: complexity for marginal benefit;
  bracket target + DLL is simpler
- **Internal DLL**: redundant with Topstep DLL; the latter is the real wall
