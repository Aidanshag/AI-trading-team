# Sunday-evening one-command preflight before first supervised live session.
# Runs verify, connection check, cost summary, and a CIO test wake.
# Run from project root:  .\scripts\sunday-open.ps1

Write-Host ""
Write-Host "=== Sunday Open: Pre-Session Preflight ===" -ForegroundColor Cyan
Write-Host ""

# Load .env
if (-not (Test-Path ".\.env")) {
    Write-Host "[FAIL] No .env present" -ForegroundColor Red
    exit 1
}
Get-Content ".\.env" | ForEach-Object {
    if ($_ -match "^\s*([A-Z_]+)\s*=\s*(.+)$") {
        [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), "Process")
    }
}

Write-Host "Step 1/4: Full preflight verify" -ForegroundColor Yellow
Write-Host ("-" * 60)
& ".\scripts\verify.ps1"
Write-Host ""

Write-Host "Step 2/4: ProjectX connection check" -ForegroundColor Yellow
Write-Host ("-" * 60)
& ".\scripts\connect-topstep.ps1"
Write-Host ""

Write-Host "Step 3/4: Cost summary" -ForegroundColor Yellow
Write-Host ("-" * 60)
& ".\.venv\Scripts\python.exe" ".\scripts\_cost_summary.py"
Write-Host ""

Write-Host "Step 4/4: CIO read-only wake (account state confirmation)" -ForegroundColor Yellow
Write-Host ("-" * 60)
& ".\.venv\Scripts\python.exe" -c @'
import asyncio
from runtime.orchestrator import Orchestrator

async def main():
    orch = Orchestrator()
    print(f"Agents loaded: {len(orch.specs)}")
    print(f"MCP servers:   {list(orch.mcp_servers)}")
    print()
    result = await orch.wake_agent(
        "CIO",
        "PRE-SESSION CHECK. Read account state via topstep_get_account. "
        "Confirm balance and trading status. Single paragraph response."
    )
    print(result.get("final_text") or "(no text)")

asyncio.run(main())
'@

Write-Host ""
Write-Host "=== Preflight Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "If everything above shows OK and the CIO greeting confirms balance,"
Write-Host "you're ready for the supervised live session."
Write-Host ""
Write-Host "Next step:  type 'start session' to me in Claude Code"
