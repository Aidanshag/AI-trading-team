# Operator scripts

PowerShell helpers you run from the fund's root directory. They are the
day-to-day command line — `status`, `tail`, `cost`, `verify`, `journal`.

## Setup (once)

1. Open PowerShell in this folder.
2. If scripts are blocked by execution policy:
   ```powershell
   Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
   ```
3. Verify:
   ```powershell
   .\scripts\verify.ps1
   ```

## Day-to-day commands

| Command                              | What it does                                   |
|--------------------------------------|------------------------------------------------|
| `.\scripts\status.ps1`               | Fund status: mode, positions, day P&L, DLL usage, recent risk events, today's cost |
| `.\scripts\tail.ps1`                 | Live-tail the audit log (every tool call)      |
| `.\scripts\journal.ps1`              | Open today's journal note in default editor    |
| `.\scripts\cost.ps1`                 | Token spend by agent for today or a given date |
| `.\scripts\verify.ps1`               | Preflight checks (env, DB, vault, permissions) |
| `.\scripts\git-init.ps1`             | Initialize a git repo for this project         |
| `.\scripts\idle-mode-on.ps1`         | Activate autonomous idle-work mode (agents pull from the backlog) |
| `.\scripts\idle-mode-off.ps1`        | Deactivate idle-work mode                      |
| `.\scripts\install-claude-cli.ps1`   | Install Node.js + claude-code CLI so `claude` works in PowerShell |
| `.\scripts\agent-scorecard.ps1`      | Per-agent activity summary from the decisions log |
| `.\scripts\connect-topstep.ps1`      | Authenticate against ProjectX, list accounts |
| `.\scripts\install-fund-service.ps1` | Install fund as Windows Service via NSSM (manual-start by default) |

## Notes

- The fund is a Python process. These scripts don't start/stop it — use
  NSSM for that (`nssm start AITradingFund`) once deployed as a service.
- None of these scripts modify broker state. They are read-only on the DB
  and the vault.
