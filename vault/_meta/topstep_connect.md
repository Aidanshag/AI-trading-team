---
type: meta
status: active
updated: 2026-04-23
---

# Connect the fund to your Topstep Combine

You purchased the $50K Combine. Here's the checklist to bring the agents online against it. Order matters.

## 0. Prerequisites (already done)

- ✓ Python 3.14 + venv installed
- ✓ `.venv` has all fund dependencies
- ✓ `state/fund.db` initialized
- ✓ ProjectX client (`tools/projectx_client.py`) written
- ✓ Topstep broker tools (`tools/topstep.py`) wired to real client
- ✓ Market-data tools (`tools/market_data.py`) routed through ProjectX
- ✓ Risk Manager prompt locked down for Combine ($500 internal DLL target)
- ✓ `config/risk_limits.yaml` + `config/topstep.yaml` updated for $50K Combine

## 1. Get your ProjectX API key

1. Log in to [dashboard.topstepx.com](https://dashboard.topstepx.com).
2. Navigate to **Settings → API Keys** (exact label may vary; look for "API" or "Automation").
3. Click **Generate new API key**.
4. Copy it immediately — most dashboards only show it once.

## 2. Fill in `.env`

```powershell
Copy-Item .env.example .env
notepad .env
```

At minimum, set:

```
ANTHROPIC_API_KEY=sk-ant-...
PROJECTX_API_KEY=<paste the key>
PROJECTX_USERNAME=<your Topstep login username or email>
# PROJECTX_ACCOUNT_ID will be filled in the next step
PROJECTX_ENV=demo
FUND_MODE=paper
```

Save and close.

## 3. Run the connection wizard

```powershell
.\scripts\connect-topstep.ps1
```

Expected output:

```
[ OK ] PROJECTX_API_KEY + PROJECTX_USERNAME present
Authenticating against ProjectX...
[ OK ] Authenticated!

Your accounts:
  id=123456  name=Combine-50K  balance=$50000
  ...

Find your Combine account above, then run:
  Edit .env and set: PROJECTX_ACCOUNT_ID=<the_id>
```

Copy the **id** of your Combine account into `.env` as `PROJECTX_ACCOUNT_ID`.

## 4. Verify

```powershell
.\scripts\verify.ps1
```

All ✓ expected. If `[FAIL]` on anything, address it before proceeding.

## 5. First live test — read-only

Before any order goes near the broker, do a read-only probe:

```powershell
.\.venv\Scripts\python.exe -c "from tools.projectx_client import get_client, get_account_id; c = get_client(); print('Account:', next(a for a in c.get_accounts() if str(a['id']) == str(get_account_id()))); print('Positions:', c.get_positions(get_account_id())); print('Working orders:', c.get_working_orders(get_account_id()))"
```

If that prints your balance and an empty positions list, you're connected.

## 6. First agent wake (CIO — non-trading)

```powershell
.\.venv\Scripts\python.exe -c "import asyncio; from runtime.orchestrator import Orchestrator; r = asyncio.run(Orchestrator().wake_agent('CIO', 'Session open - read current account state via topstep_get_account and write a one-paragraph hello to vault/journal/.')); print(r)"
```

This wakes the CIO on Haiku. Expected cost: <$0.01. It should call `topstep_get_account`, see your $50K balance, and write a note to today's journal. Check `vault/journal/<today>.md` for the output.

## 7. First paper trade (optional — manual sanity check)

Before letting agents place orders, manually run:

```powershell
.\.venv\Scripts\python.exe -c "from tools.projectx_client import get_client, get_account_id; c = get_client(); print(c.front_month_contract_id('MCL'))"
```

This should return a contract ID for the front-month Micro Crude. If it works, you can place a $1 micro test order manually via the TopstepX web UI first before trusting agents with placement.

## 8. Bring the fund online

```powershell
fund
```

(This runs `runtime.main:main`, which starts the event loop. Won't place trades until agents decide to, and every order goes through the risk hook.)

## Checklist summary

- [ ] ProjectX API key generated on TopstepX dashboard
- [ ] `.env` populated with ANTHROPIC_API_KEY, PROJECTX_API_KEY, PROJECTX_USERNAME, PROJECTX_ACCOUNT_ID
- [ ] `.\scripts\connect-topstep.ps1` authenticates successfully
- [ ] `.\scripts\verify.ps1` green
- [ ] Read-only probe shows $50K balance
- [ ] CIO wake prints session greeting to journal
- [ ] Ready to run `fund`

## Risk-priority reminder

Per your directive, **the Risk Manager treats −$500 day P&L as the true daily floor** (50% of Topstep's $1,000 DLL). The defensive ladder engages at −$150, restricts at −$300, locks down at −$500, and emergency-flattens at −$750. See `agents/risk_manager.md` and `config/risk_limits.yaml:combine_defense.ladder`.

The fund is designed so Topstep's DLL should never even come into play. If you ever see day P&L approach −$500, something has gone wrong — investigate immediately.
