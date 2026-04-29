"""Monthly P&L vs cost report.

Pulls today's spend + month-to-date spend + Topstep account state.
Compares to the breakeven thresholds in vault/_meta/economic_health.md.
Writes a snapshot to vault/journal/{date}.md and stdout.

Run weekly minimum, daily preferred:
  .\.venv\Scripts\python.exe scripts/monthly_pnl_report.py
"""
from __future__ import annotations
import os, sys, sqlite3, httpx
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

env = Path(".env")
for line in env.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip())


# Cost thresholds from vault/_meta/economic_health.md
MONTHLY_COSTS = {
    "anthropic_api": 250,
    "claude_subscription": 100,
    "topstep_combine": 165,
    "topstep_data": 10,
    "buffer": 50,
}
TOTAL_COSTS = sum(MONTHLY_COSTS.values())  # $575

THRESHOLDS = {
    "breakeven":   TOTAL_COSTS,                # $575
    "worthwhile":  TOTAL_COSTS * 2,            # $1,150
    "comfortable": TOTAL_COSTS * 3,            # $1,725
    "strong":      TOTAL_COSTS * 5,            # $2,875
}


def main():
    now = datetime.now(tz=timezone.utc)
    month = now.strftime("%Y-%m")
    today = now.strftime("%Y-%m-%d")

    # 1. API spend month-to-date
    c = sqlite3.connect("state/fund.db")
    api_mtd = float(c.execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day LIKE ?",
        (f"{month}%",)
    ).fetchone()[0] or 0)
    api_today = float(c.execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs WHERE day = ?",
        (today,)
    ).fetchone()[0] or 0)
    api_alltime = float(c.execute(
        "SELECT COALESCE(SUM(usd_est), 0) FROM costs"
    ).fetchone()[0] or 0)

    # 2. Topstep account P&L
    api_key = os.environ.get("PROJECTX_API_KEY", "")
    user = os.environ.get("PROJECTX_USERNAME", "")
    aid = int(os.environ.get("PROJECTX_ACCOUNT_ID", "0") or 0)
    balance = None
    starting_balance = 50000
    if api_key and user and aid:
        try:
            r = httpx.post("https://api.topstepx.com/api/Auth/loginKey",
                           json={"userName": user, "apiKey": api_key}, timeout=15.0)
            t = r.json().get("token")
            if t:
                H = {"Authorization": f"Bearer {t}"}
                r = httpx.post("https://api.topstepx.com/api/Account/search",
                               headers=H, json={"onlyActiveAccounts": True}, timeout=15.0)
                acct = next((a for a in r.json().get("accounts", []) if a.get("id") == aid), None)
                if acct:
                    balance = float(acct.get("balance", 0))
        except Exception as e:
            print(f"  [warn] Topstep query failed: {e}")

    # P&L since Combine start
    if balance is not None:
        topstep_pnl = balance - starting_balance
    else:
        topstep_pnl = None

    # 3. Total monthly outflow
    estimated_other_costs = (
        MONTHLY_COSTS["claude_subscription"] +
        MONTHLY_COSTS["topstep_combine"] +
        MONTHLY_COSTS["topstep_data"] +
        MONTHLY_COSTS["buffer"]
    )
    total_outflow_mtd = api_mtd + estimated_other_costs

    # Net position
    if topstep_pnl is not None:
        net_mtd = topstep_pnl - total_outflow_mtd
    else:
        net_mtd = None

    # ---- Output ----
    print()
    print("=" * 60)
    print(f"  MONTHLY P&L vs COST REPORT — {now.isoformat(timespec='minutes')}")
    print("=" * 60)
    print()
    print(f"Month: {month}    Day-of-month: {now.day}")
    print()
    print("─── Monthly costs ───")
    for k, v in MONTHLY_COSTS.items():
        print(f"  {k:<24} ${v:>6,.2f}/mo")
    print(f"  {'TOTAL':<24} ${TOTAL_COSTS:>6,.2f}/mo")
    print()
    print("─── Cost burn (actuals) ───")
    print(f"  API today:           ${api_today:>7,.2f}")
    print(f"  API month-to-date:   ${api_mtd:>7,.2f}  (vs ${MONTHLY_COSTS['anthropic_api']:.0f} budget)")
    print(f"  Other costs (est.):  ${estimated_other_costs:>7,.2f}")
    print(f"  Total outflow MTD:   ${total_outflow_mtd:>7,.2f}")
    print()
    if topstep_pnl is not None:
        print("─── Trading P&L ───")
        print(f"  Topstep account: ${balance:,.2f} (start ${starting_balance:,.2f})")
        sign = "+" if topstep_pnl >= 0 else ""
        print(f"  Combine P&L:    {sign}${topstep_pnl:,.2f}")
        if net_mtd is not None:
            sign = "+" if net_mtd >= 0 else ""
            print(f"  NET (P&L − outflow): {sign}${net_mtd:,.2f}")
        print()
    print("─── Profit thresholds (monthly target) ───")
    for label, target in THRESHOLDS.items():
        if topstep_pnl is None:
            mark = "?"
        elif topstep_pnl >= target:
            mark = "✓ HIT"
        else:
            gap = target - topstep_pnl
            mark = f"need ${gap:,.0f} more"
        print(f"  {label:<14} ${target:>5,}/mo   {mark}")
    print()
    print("─── All-time fund spend ───")
    print(f"  API total: ${api_alltime:,.2f}")
    print()


if __name__ == "__main__":
    main()
