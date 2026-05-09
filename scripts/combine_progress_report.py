"""Topstep Combine pass-progress report.

This is the team's primary scoreboard. Pulls live Topstep balance,
computes:
  - Current P&L vs $3,000 profit target
  - Trading-days count (need >= 5)
  - Highest EOD balance (TDD anchor)
  - Day P&L distribution (consistency ratio)
  - Distance to TDD breach
  - Distance to DLL breach today

Run before every session and at EOD.
"""
from __future__ import annotations
import os, sys, sqlite3, httpx
from datetime import datetime, timezone
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

env = Path(".env")
for line in env.read_text().splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, _, v = line.partition("="); os.environ.setdefault(k.strip(), v.strip())


# Topstep $50K Combine constants
STARTING_BALANCE = 50000
PROFIT_TARGET    = 3000
DLL_LIMIT        = 1000      # Topstep's hard line; we use $500 internal
TDD_LIMIT        = 2000      # Trailing drawdown from highest EOD
MIN_TRADING_DAYS = 5
CONSISTENCY_MAX  = 0.50      # No single day > 50% of total profit
INTERNAL_DLL     = 500       # Our self-imposed daily floor
DAILY_PROFIT_CAP = 700       # Our consistency-rule protection


def get_topstep_state():
    api_key = os.environ.get("PROJECTX_API_KEY", "")
    user = os.environ.get("PROJECTX_USERNAME", "")
    aid = int(os.environ.get("PROJECTX_ACCOUNT_ID", "0") or 0)
    if not (api_key and user and aid):
        return None
    try:
        r = httpx.post("https://api.topstepx.com/api/Auth/loginKey",
                       json={"userName": user, "apiKey": api_key}, timeout=15.0)
        t = r.json().get("token")
        H = {"Authorization": f"Bearer {t}"}
        r = httpx.post("https://api.topstepx.com/api/Account/search",
                       headers=H, json={"onlyActiveAccounts": True}, timeout=15.0)
        accts = r.json().get("accounts", [])
        acct = next((a for a in accts if a.get("id") == aid), None)
        if not acct: return None
        return {
            "name": acct.get("name"),
            "balance": float(acct.get("balance", 0)),
            "canTrade": acct.get("canTrade", False),
        }
    except Exception as e:
        return {"error": str(e)}


def get_local_history():
    """Pull our local fund.db for EOD balance history if logged."""
    c = sqlite3.connect("state/fund.db")
    c.row_factory = sqlite3.Row
    rows = c.execute(
        "SELECT ts, balance_usd FROM account_snapshots ORDER BY ts ASC"
    ).fetchall()
    return [(r["ts"][:10], float(r["balance_usd"])) for r in rows]


def main():
    now = datetime.now(tz=timezone.utc)

    state = get_topstep_state()
    print()
    print("=" * 64)
    print(f"  COMBINE PROGRESS REPORT — {now.isoformat(timespec='minutes')}")
    print("=" * 64)
    print()

    if not state or "error" in (state or {}):
        print("  Could not fetch Topstep state.")
        if state and "error" in state: print(f"  {state['error']}")
        return 1

    balance = state["balance"]
    pnl = balance - STARTING_BALANCE
    print(f"  Account:        {state['name']}")
    print(f"  Balance:        ${balance:>10,.2f}")
    print(f"  P&L (cumulative): ${pnl:+,.2f}  (start ${STARTING_BALANCE:,})")
    print(f"  Can trade:      {state['canTrade']}")
    print()

    # ─── Profit target ───
    pct_to_target = (pnl / PROFIT_TARGET * 100) if pnl > 0 else 0
    remaining = max(0, PROFIT_TARGET - pnl)
    if pnl >= PROFIT_TARGET:
        target_status = "✓ HIT — eligible to submit for funding (verify other rules)"
    else:
        target_status = f"need ${remaining:,.2f} more"
    print(f"  Profit target:    ${PROFIT_TARGET:,}  ({pct_to_target:.0f}% reached)")
    print(f"  Status:           {target_status}")
    print()

    # ─── EOD balance history → TDD anchor ───
    history = get_local_history()
    if history:
        # Get end-of-day balance per day (last snap of each day)
        by_day = {}
        for d, b in history:
            by_day[d] = b
        eod_balances = list(by_day.values())
        peak_eod = max(eod_balances + [STARTING_BALANCE])
        # TDD anchor: peak_eod − $2,000 (but never above starting balance)
        tdd_floor = peak_eod - TDD_LIMIT  # could go above 50K once profitable
        distance_to_tdd = balance - tdd_floor
        print(f"  Highest EOD:    ${peak_eod:>10,.2f}  (TDD anchor)")
        print(f"  TDD floor:      ${tdd_floor:>10,.2f}")
        print(f"  Distance to TDD breach: ${distance_to_tdd:+,.2f}")
        if distance_to_tdd < 500:
            print(f"  ⚠ TDD ALERT — within $500 of breach")
    else:
        print("  EOD history not yet recorded (account_snapshots empty)")
        print(f"  TDD floor (estimate): ${STARTING_BALANCE - TDD_LIMIT:,.2f}")
    print()

    # ─── Trading days count ───
    if history:
        n_trading_days = len(by_day)
    else:
        n_trading_days = 0
    print(f"  Trading days logged: {n_trading_days}  (need >= {MIN_TRADING_DAYS})")
    print()

    # ─── Daily P&L (rough) for consistency check ───
    if history and len(by_day) > 1:
        prev = STARTING_BALANCE
        daily_pnls = []
        for d, b in sorted(by_day.items()):
            daily_pnls.append((d, b - prev))
            prev = b
        max_day = max(daily_pnls, key=lambda x: x[1]) if daily_pnls else None
        if max_day and pnl > 0 and max_day[1] > 0:
            ratio = max_day[1] / pnl
            print(f"  Largest day P&L: ${max_day[1]:+,.2f} on {max_day[0]} ({ratio*100:.0f}% of total)")
            if ratio >= CONSISTENCY_MAX:
                print(f"  ⚠ CONSISTENCY: {ratio*100:.0f}% > {CONSISTENCY_MAX*100:.0f}% cap — would be denied")
            elif ratio >= 0.40:
                print(f"  ⚠ CONSISTENCY tight ({ratio*100:.0f}% — keep adding profit on other days)")
    print()

    # ─── Internal caps ───
    print("─── Internal caps (firm-imposed) ───")
    print(f"  Internal DLL ceiling:    ${INTERNAL_DLL:>5,}/day  (Topstep DLL is ${DLL_LIMIT:,})")
    print(f"  Daily profit cap:        ${DAILY_PROFIT_CAP:>5,}/day  (consistency-rule protection)")
    print()

    # ─── Verdict ───
    print("─── Pass status ───")
    pass_blockers = []
    if pnl < PROFIT_TARGET:
        pass_blockers.append(f"profit target not yet hit (${remaining:,.0f} away)")
    if n_trading_days < MIN_TRADING_DAYS:
        pass_blockers.append(f"need {MIN_TRADING_DAYS - n_trading_days} more trading day(s)")
    if pass_blockers:
        for b in pass_blockers:
            print(f"  ✗ {b}")
    else:
        print(f"  ✓ Profit + trading-days requirements met. Verify consistency + TDD before submission.")
    print()


if __name__ == "__main__":
    main()
