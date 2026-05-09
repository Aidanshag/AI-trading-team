---
type: playbook
category: trading_strategies
applies_to: [analyst_energies, portfolio_manager, risk_manager]
symbols: [CL, MCL, BZ]
updated: 2026-04-23
---

# Crude oil — trading strategies

Products: [[CL]] WTI, [[MCL]] micro WTI, [[BZ]] Brent. See the [[CL]] product deep-dive.

## 1. EIA inventory-surprise continuation

**One-liner**: After an EIA Petroleum Status surprise > 2M barrels from consensus, wait 30 min and trade the continuation with 1.5× ATR stop and 2R target.

**Thesis**: EIA's Weekly Petroleum Status Report (Wednesdays 10:30 ET) is the most-watched weekly release for crude. Surprises > 2M (either draw or build) produce tradeable one-session and multi-session moves. The 30-min-post-release filter removes algo-driven reversal noise and captures the durable directional flow.

**Trigger**:
- EIA headline crude surprise > 2M vs consensus.
- 30 min post-release, price has held direction within 25% of the post-release extreme.
- No concurrent major geopolitical shock that overrides the inventory signal.

**Invalidation**:
- Price retraces > 60% of the 0–30 min move within the next hour.
- Products (gasoline, distillate) contradict the crude story (e.g., bullish crude draw + big product builds = mixed).

**Structure**:
- Outright [[CL]] or [[MCL]] (micro for tighter sizing).
- Size: 50 bps of equity.
- Stop: 1.5× 20-bar 5-min ATR.
- Target: 2R.

**Exit rules**:
- Scale out half at 2R, trail remainder on 15-min lows/highs.
- Full exit by end of day + 1.

**Calibration**:
- Expected hit rate: 55–60%.
- Expected average R: +0.8 to +1.2.
- Historical: best setups are clean surprises without product contradiction (pure crude draw or pure crude build).

**Common traps**:
- Trading the first 15 min — algos front-run and reverse.
- Ignoring product data — crude often moves opposite of products on the same release.
- Chasing the next day — most of the R has been taken by session close.

---

## 2. OPEC+ decision directional

**One-liner**: After an OPEC+ production decision surprises the expected policy path, trade in the direction of the surprise for 3–5 sessions.

**Thesis**: OPEC+ decisions (JMMC and full ministerial meetings) on production quotas are the single largest supply-side catalyst for crude. When the decision surprises (cut when hold expected, or vice versa), the market reprices over 3–5 sessions as refiners, traders, and hedgers adjust. The trend is most durable when accompanied by statements about compliance or extensions.

**Trigger**:
- OPEC+ announces a production change that differs from pre-meeting consensus.
- The announcement includes enforcement language or duration detail (not just headline).
- Post-announcement first-session closes in direction of the surprise.

**Invalidation**:
- Compliance concerns emerge (e.g., UAE-Saudi tension headlines) in the days after.
- A concurrent demand shock (recession data, China PMI) overrides the supply signal.

**Structure**:
- Outright CL front-month.
- Size: 50 bps of equity.
- Stop: below the last session's low (long) / above high (short) pre-announcement.
- Target: 2–3R, held 3–5 sessions.

**Exit rules**:
- Target 2R on session+1, 3R by session+5.
- Stop: reverse of pre-announcement level.
- Time stop: 5 sessions.

**Calibration**:
- Expected hit rate: 55%.
- Expected average R: +1.5 when it hits.
- Historical: 2022 OPEC+ 2M cut (+3R over 4 sessions), 2023 Saudi unilateral cut (+2R over 3 sessions), 2018 Qatar withdrawal (−2R — a hard reversal, atypical).

**Common traps**:
- Fading on session+1 — the move extends before it doesn't.
- Ignoring compliance headlines — statements vs actual production are different trades.
- Holding past 5 sessions — secondary drivers take over.

---

## 3. Brent–WTI arb mean reversion

**One-liner**: Fade the Brent-WTI spread when it's ≥ 1.5σ from the 60-day mean, targeting mean reversion to the 30-day mean.

**Thesis**: Brent and WTI are both light-sweet crude benchmarks but price differently because of location (Brent is seaborne/Europe, WTI is land-locked Cushing). Spread drivers include Cushing storage, Gulf export capacity, Middle East tension (affects Brent more), and US shale production. Extreme spread values tend to mean-revert within 15–25 sessions absent structural change.

**Trigger**:
- Front-month BZ − CL spread > 1.5σ from 60-day rolling mean.
- No structural shock in the transmission infrastructure (pipeline outages, SPR release announcements).
- Cushing storage capacity and Gulf export data do not justify the extreme.

**Invalidation**:
- Pipeline shutdown or export bottleneck announcement.
- SPR release/refill announcement.
- Middle East geopolitical escalation.

**Structure**:
- Paired position: long the cheap benchmark + short the rich benchmark in a 1:1 contract ratio.
- Size: 50 bps of equity on spread P&L.

**Exit rules**:
- Target: spread returns to 30-day mean.
- Stop: spread extends to 2.5σ — treat as new regime.
- Time stop: 25 sessions.

**Calibration**:
- Expected hit rate: 60–65%.
- Expected average R: +0.8.
- Historical: reliable in balanced supply regimes; fails during extreme Cushing glut (2020 April) or acute Middle East events.

**Common traps**:
- Legging in — get both contracts within minutes or abandon.
- Fading a shock-driven spread — geopolitics can push spreads past 2.5σ and stay there.
- Over-sizing — the spread looks mean-reverting but carries hidden curve risk.

---

## 4. Storage-term-structure shift

**One-liner**: When front-month CL moves from contango into backwardation, go long the front-month calendar spread (near − next).

**Thesis**: The term structure of crude (contango = forward > spot, backwardation = forward < spot) signals physical tightness. A shift from contango to backwardation is a structural signal that near-term supply has tightened. Front-month calendar spreads (buy near-month, sell next-month) express this with lower directional risk than outright price.

**Trigger**:
- Front-month spread (near − next) crosses from negative (contango) to positive (backwardation).
- Cushing or Gulf storage data confirms physical tightening.
- Volume in front calendar spread is elevated (speculator positioning shift).

**Invalidation**:
- Spread reverses back into contango > 0.30 within 5 sessions.
- SPR release or storage-build announcement.

**Structure**:
- Long front / short next calendar spread, 1:1.
- Size: 50 bps of equity on spread P&L.
- Stop: spread reverses into contango by 0.30.

**Exit rules**:
- Target: spread widens to +1.50 or the 90-day-high in backwardation.
- Stop: re-enters contango.
- Time stop: 20 sessions.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +1.2.
- Historical: reliable signal; caught the 2021 post-pandemic backwardation shift (+3R over 12 sessions).

**Common traps**:
- Entering on a single day's flip — wait for 2 sessions of confirmation.
- Ignoring physical data — term structure can flip on speculative flow without real tightening.
- Holding past the back-month roll — rolls reset the spread.

---

## 5. Geopolitical risk-premium decay

**One-liner**: After a Middle East headline drives a crude spike, fade the move via defined-risk short structure 2 sessions later if no escalation.

**Thesis**: Geopolitical shocks (Hormuz incidents, Saudi/Iran tensions, Israel-Iran exchanges) produce immediate risk premium in crude — typically 2–5% intraday. But actual supply disruption requires follow-through. Historically, ~60% of these spikes decay within 5 sessions as the market resolves whether the incident translates to real supply shock. The decay is tradeable with defined-risk short structure.

**Trigger**:
- Confirmed Middle East geopolitical headline drives 2%+ spike day 1.
- Day 2 does not see escalation (no follow-up military action, tanker attack, etc.).
- No OPEC+ or US policy response announced.

**Invalidation**:
- Escalation headline (military strike, tanker attack, production facility hit).
- OPEC+ emergency meeting called.
- Confirmed supply disruption (production cut, export shutdown).

**Structure**:
- Bear call spread on CL, DTE 15–30, strikes above day-2 close.
- Size: 50 bps of equity max-loss.

**Exit rules**:
- Target: 50% retrace of the spike.
- Stop: new high above day-2 peak.
- Time stop: 10 sessions.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +1.0.
- Historical: worked on most 2019–23 Hormuz-area incidents; failed on 2022 Russia-Ukraine invasion (real supply shock, not headline-only).

**Common traps**:
- Fading an actual supply-disruption event — this is not a headline, it's a shock.
- Structuring as outright short (firm forbids).
- Ignoring escalation-signal news after entry.

---

## 6. SPR-release fade

**One-liner**: After a US government announces an SPR release, fade the 1–2 session rally (or buy the dip) as the supply arrives and prices adjust.

**Thesis**: US Strategic Petroleum Reserve releases are a political-economic signal as much as a supply event. The announcement typically causes an immediate dip in crude (1–2%) which often retraces within 2–4 sessions as (a) the market absorbs that the release is finite and small vs global demand, and (b) fundamental drivers reassert.

**Trigger**:
- SPR release announcement by US Dept of Energy or White House.
- Day-1 drop of 1%+ in front-month CL.
- No concurrent bearish fundamental catalyst (recession data, OPEC+ pause, etc.).

**Invalidation**:
- Announced release is > 100M barrels (large enough to be structurally bearish).
- Concurrent OPEC+ production increase or demand-destruction data.

**Structure**:
- Long CL or bull call spread, DTE 21–45.
- Size: 50 bps of equity.

**Exit rules**:
- Target: return to pre-announcement level + 1R.
- Stop: new cycle low.
- Time stop: 10 sessions.

**Calibration**:
- Expected hit rate: 60%.
- Expected average R: +1.0.
- Historical: 2022 mega-SPR release (180M barrels over 6 months) was bearish for months — not tradeable as a fade; size appropriately.

**Common traps**:
- Fading a mega-release (> 100M barrels).
- Chasing the dip too early — wait for day-1 close.
- Ignoring concurrent data releases.
