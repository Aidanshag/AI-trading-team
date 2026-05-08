# Running the fund as a Windows Service with NSSM

NSSM ("the Non-Sucking Service Manager") wraps any console program as a proper Windows Service. The fund survives user logoff, reboots, and crashes.

## One-time setup

1. **Install NSSM**

   Download from https://nssm.cc/download (grab the 2.24+ release). Extract `nssm.exe` somewhere on PATH (e.g. `C:\tools\nssm\nssm.exe`). Verify:

   ```powershell
   nssm --version
   ```

2. **Create a Python venv in the project folder**

   ```powershell
   cd "C:\Users\Owner\OneDrive\Personal AI\AI Trading"
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -e ".[dev]"
   ```

3. **Verify the fund runs in the foreground first**

   ```powershell
   fund
   ```

   If you see "Fund starting in paper mode" and no crash, Ctrl-C and proceed.

4. **Install the service**

   Open an **elevated** PowerShell (Run as Administrator):

   ```powershell
   $fundDir = "C:\Users\Owner\OneDrive\Personal AI\AI Trading"
   nssm install AITradingFund "$fundDir\.venv\Scripts\python.exe"
   nssm set AITradingFund AppParameters "-m runtime.main"
   nssm set AITradingFund AppDirectory "$fundDir"
   nssm set AITradingFund AppEnvironmentExtra "PYTHONUNBUFFERED=1"

   # Logging
   nssm set AITradingFund AppStdout "$fundDir\logs\service_stdout.log"
   nssm set AITradingFund AppStderr "$fundDir\logs\service_stderr.log"
   nssm set AITradingFund AppRotateFiles 1
   nssm set AITradingFund AppRotateBytes 10485760

   # Restart policy — relaunch immediately on crash
   nssm set AITradingFund AppExit Default Restart
   nssm set AITradingFund AppRestartDelay 5000

   # Startup
   nssm set AITradingFund Start SERVICE_AUTO_START

   nssm start AITradingFund
   ```

5. **Verify**

   ```powershell
   nssm status AITradingFund
   Get-Content "$fundDir\logs\service_stdout.log" -Tail 50
   ```

## Day-to-day

```powershell
nssm start   AITradingFund
nssm stop    AITradingFund
nssm restart AITradingFund
nssm status  AITradingFund
```

Edit `.env` or any config → `nssm restart AITradingFund` to pick up changes.

## Removing

```powershell
nssm stop   AITradingFund
nssm remove AITradingFund confirm
```

## Notes

- Under NSSM the service runs as `LocalSystem` by default. If ProjectX credentials live in `C:\Users\Owner\...`, configure NSSM to run under your user account instead (`nssm set AITradingFund ObjectName ".\Owner" <password>`), or move `.env` to a path `LocalSystem` can read.
- The logs under `logs/service_*.log` complement `logs/audit.jsonl` — the latter is the structured agent log, the former is Python stdout/stderr including crashes.
