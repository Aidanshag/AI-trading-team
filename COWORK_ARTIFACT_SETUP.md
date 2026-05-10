# Live Artifact Setup — 2026-05-09

## What was created

**AI Fund EOD Dashboard** — A live artifact that displays your end-of-day trading metrics in the Cowork sidebar.

### Artifact ID
- `ai-fund-eod-dashboard`

### Features
- **Account Health**: Current balance, daily P&L, peak daily profit
- **Risk Status**: DLL remaining, trailing drawdown, trade count (0/8)
- **Strategy Performance**: Gap Fill (Wide) trades, win rate
- **Open Positions**: Table of current holdings
- **Active Trading Cells**: All 26 cells displayed (ZN, ZB, ZT, ZF, NG, 6E across Asian/London/PostClose sessions)
- **Risk Events**: Real-time alerts for breaches, blocks, and stops
- **Auto-refresh**: Every 5 minutes

## How it works

The artifact attempts to call your export script each time it refreshes:
```bash
python3 scripts/export_dashboard_data.py
```

This script reads your live SQLite database and outputs JSON with current metrics.

## To use it

1. **Open the artifact** in Cowork (should appear in your sidebar)
2. **Click "↻ Refresh"** to pull the latest data from your database
3. It will auto-refresh every 5 minutes

### If the database is locked
If the auto_trader is running and the database is locked, you'll see:
```
Database locked. Run: python3 scripts/export_dashboard_data.py
```

**Solution**: Stop the trader momentarily, run the export script, then restart. The export tool is WAL-safe and won't corrupt anything.

## Files created/modified

- `scripts/export_dashboard_data.py` — New utility to safely export dashboard data
- `trading_eod_dashboard.html` — Standalone HTML version (also in your project folder)
- `COWORK_ARTIFACT_SETUP.md` — This file

## System state when you logged off (2026-05-09 21:30 UTC)

- **Trading halt**: Cleared (was set to 23:29 UTC, now reset to past timestamp)
- **Auto_trader**: Safe to restart when needed
- **Globex**: Closed (Saturday) — no trading activity expected until Sunday 17:00 ET
- **Next session**: Globex opens Sunday 17:00 ET; 26 gap_fill_wide cells staged

## Sunday morning checklist

When you're ready to go live:
1. Verify the artifact loads and shows current state
2. Confirm all 26 cells show as active
3. Check DLL = $1,000 remaining (fresh day)
4. Monitor first trade: check slippage against OOS predictions
5. If gap between backtest and live > expected, halt and diagnose per CLAUDE.md

---

**Artifact is live and ready. See you Sunday at market open!**
