---
type: canon
status: active
read_on_first_wake: [CIO, Risk Manager, Portfolio Manager, Edge Hunter, Quant Researcher]
---

# Trading principles — distilled canon

Single page of one-liners, indexed by situation. Each is sourced from a specific book or trader's documented practice. **Cite the principle by name when applying it in a decision** so the lesson stays load-bearing instead of becoming wallpaper.

When a principle here gets encoded into code or config, mark it with `→ encoded:`. That tells future-us which principles still live in prose and which are enforced.

---

## DRAWDOWN — what to do when losing

- **After 3 losses in a row, stop.** No exceptions. Wait an hour minimum. — *Bellafiore, "The PlayBook"*  → encoded: `fund.yaml:autonomous_restrictions.consecutive_losers_halt: 3`
- **Position size shrinks with drawdown depth.** When you're 2% down, your next trade is half-size. Don't martingale into "getting it back." — *Tharp, "Trade Your Way to Financial Freedom"*  → encoded: `risk_limits.yaml:risk_framework.adaptive_discipline`
- **The first loss is the cheapest.** Cut it; don't widen the stop. — *Schwager, "Market Wizards"*  → encoded: `risk_limits.yaml:hard_rules.require_stop_on_every_trade: true`
- **Don't add to losers.** Adding to a losing position is the most expensive way to be wrong. — *anonymous canon, agreed by every Wizards interviewee*

## REGIME — when the tape isn't behaving the way you expect

- **If you don't recognize the tape, sit out.** Boredom is not a signal. — *Steenbarger, "The Daily Trading Coach"*  → encoded: `risk_limits.yaml:regime_gates.thin_tape`
- **Strategy must match regime.** A mean-reversion setup in a trending market is a losing trade with extra steps. — *Lo, "Adaptive Markets"*
- **Liquidity matters more than signal.** A great setup in thin tape is worse than no setup. — *Lefèvre, "Reminiscences of a Stock Operator"*  → encoded: `auto_trader._in_thin_tape_window` blocks 21:00-04:00 ET
- **Reflexivity: when prices move enough, they change the underlying.** Watch for moments when the tape stops respecting fundamentals — that's a regime shift, not a tradeable trend. — *Soros, "The Alchemy of Finance"*

## PSYCHOLOGY — the trader you become matters more than the trade

- **Patience IS a trade.** Sitting on cash because nothing fits is the right answer more often than people admit. — *Lefèvre, "Reminiscences"*
- **Probabilistic thinking, not predictive thinking.** Each setup has an edge or it doesn't; the outcome of any single trade tells you nothing. — *Douglas, "Trading in the Zone"*
- **Survivorship bias is the silent killer of strategies.** The strategies you're testing exist BECAUSE they worked in the past — that's the selection bias. — *Taleb, "Fooled by Randomness"*
- **The market doesn't owe you a win.** It owes you nothing. Show up, do the work, and let the math accumulate. — *Schwager interviews, especially Marty Schwartz*

## EXECUTION — the mechanics of staying in the game

- **Cut losers fast. Let winners run.** The most quoted rule in trading because nobody actually does it. — *Schwager, "Market Wizards"* (every interviewee, in different words)
- **Stops outside the noise, but inside the thesis.** A stop that gets hit by normal noise is a fake stop. A stop wider than your thesis-invalidation level is a fake thesis. — *applied tactical canon*
- **Don't trade the open.** First 5 minutes are noise; the institutional flow shows up after that. — *Steenbarger, "The Daily Trading Coach"*  → encoded: `risk_limits.yaml:sessions.block_first_n_seconds_after_open: 60`
- **Don't trade the close.** Last 2 minutes have liquidity holes; the marks are unreliable. — *standard floor wisdom*

## SIZING — how big to bet

- **Kelly is an upper bound, not a target.** Half-Kelly or quarter-Kelly is what real traders use because Kelly assumes a known edge. — *Thorp, Beat the Market*
- **Position size = max acceptable loss / stop distance.** Not "feeling confident" or "this one's big." — *Tharp, basic sizing math*  → encoded: `risk_limits.yaml:account.per_trade_risk_pct_of_equity: 0.005`
- **Concentration kills.** LTCM had positions correctly sized for one regime; the regime changed, the leverage didn't. — *Lowenstein, "When Genius Failed"*  → encoded: `risk_limits.yaml:correlated_baskets`
- **Size up after a string of small wins, not after a single big one.** A big win can make you reckless; small wins prove the edge is real. — *Bellafiore, "One Good Trade"*

## COST — every trade pays a tax to be made

- **Every trade pays 3 taxes: spread, fees, slippage.** A round-trip on Topstep micros costs $1.50 in fees PLUS spread PLUS expected slippage. Trades that don't clear those costs in expectation are negative-EV before you even start. — *Carver, "Systematic Trading"*  → encoded: `risk_limits.yaml:fee_decision.min_reward_to_fee_ratio: 3.0`
- **Frequency is a cost.** Even a positive-EV strategy run too frequently can lose to costs. — *AQR research notes on trading-cost analysis*  → encoded: `risk_limits.yaml:cost_discipline.daily_fee_budget_usd`
- **Subscription costs are real losses.** $20/day in fixed costs (Topstep + Claude + API + buffer) means a flat day is a -$20 day. Every session must clear $20+ to be net-economic. — *bespoke to this fund*  → encoded: see `vault/_meta/economics.md`
- **The market doesn't reward activity. It rewards correctness.** The best traders in Schwager interviews trade LESS than novices, not more. — *Schwager, recurring theme*

## RISK MANAGEMENT — the only thing that decides survival

- **The first job is survival. Profit is the second job.** Without survival, profit is impossible. — *Soros, "Soros on Soros"*
- **Hard stops are mandatory; mental stops are aspirational.** The market doesn't care about your aspirations. — *standard prop-firm canon*  → encoded: `risk_limits.yaml:hard_rules.require_stop_on_every_trade: true`
- **Diversification across uncorrelated bets, not across "different" instruments.** ES + NQ + RTY is one trade. — *Markowitz interpreted by every macro shop*  → encoded: `risk_limits.yaml:correlated_baskets.risk_on_index`
- **Tail risk is asymmetric. Tails kill you faster than they save you.** A 2% bad day is recoverable; a 20% bad day ends the account. Size for tails, not means. — *Taleb, "Antifragile"*

## TEAM / PROCESS — how an institutional desk works

- **Every trade has an explicit thesis written before entry.** No thesis = no trade. — *Renaissance, Bridgewater process*  → encoded: `vault/_meta/pre_trade_checklist.md`
- **Risk has veto power.** PM proposes; Risk decides; nobody overrides Risk. — *Citadel, Jane Street structure*  → encoded: `agents/risk_manager.md`
- **The post-mortem is the most important document.** Every trade — winner or loser — gets reviewed. Patterns emerge from the meta-data, not from individual trades. — *Bellafiore, "One Good Trade"*  → encoded: `vault/lessons/`
- **Discipline > intelligence.** The smartest analyst with no discipline loses to the average analyst with rigorous discipline. — *recurring across Schwager + Drobny*

## WHEN IN DOUBT

If a setup doesn't fit any principle here, don't trade it. The whole point of having a canon is that ad-hoc decisions are the most expensive ones we make.
