---
type: meta
status: active
updated: 2026-04-23
claim_key: "(YYYY-MM-DD HH:MM UTC — {agent name})"
---

# Idle-work backlog (ACTIVE)

`config/fund.yaml:idle_work_enabled: true` AND `status: active` — agents may claim items below during their idle cycles, subject to the rules in [[idle_protocol]].

See `vault/_meta/idle_protocol.md` for the full protocol. The short version: one item per wake, mark `- [.]` to claim with a timestamp, `- [x]` when done, `- [~]` if partial.

**Priorities:** P1 = do first; P2 = do after P1 exhausted; P3 = when everything else is done.

---

## Energies Analyst

### Product deep-dives — priority P1
- [x] P1 NG — Natural Gas (Henry Hub). File: `vault/futures/product_deep_dives/NG.md`. (2026-04-25 06:20 UTC — Fund Engineer)
- [ ] P1 MCL — Micro Crude (mirror of CL with size caveats). File: `vault/futures/product_deep_dives/MCL.md`.
- [x] P1 RB — RBOB Gasoline. File: `vault/futures/product_deep_dives/RB.md`. (2026-04-25 07:00 UTC — Fund Engineer)
- [x] P1 **HO — NY ULSD (Diesel)**. File: `vault/futures/product_deep_dives/HO.md`. (2026-04-25 01:30 UTC — Fund Engineer)  ← the diesel contract
- [x] P1 MCL — Micro Crude (mirror of CL with size caveats). File: `vault/futures/product_deep_dives/MCL.md`. (2026-04-25 08:15 UTC — Fund Engineer)
- [x] P1 BZ — Brent Crude. File: `vault/futures/product_deep_dives/BZ.md`. (2026-04-25 09:15 UTC — Fund Engineer)
- [x] P2 QG — E-mini Natural Gas. File: `vault/futures/product_deep_dives/QG.md`. (2026-04-25 12:35 UTC — Fund Engineer)
- [ ] P3 EH — Ethanol. File: `vault/futures/product_deep_dives/EH.md`.

### Playbooks — priority P2
- [ ] P2 Seasonal energies patterns (winter storage, driving season, hurricane season). File: `vault/playbooks/energies_seasonality.md`.
- [ ] P2 OPEC+ meeting playbook (what to do the day of, week of, month after). File: `vault/playbooks/opec_meetings.md`.
- [ ] P3 Refining-crack spread primer (long RB/HO short CL). File: `vault/playbooks/refining_cracks.md`.

### Pattern library — priority P2
- [ ] P2 Energies pattern note — top 3 recurring setups with triggers. File: `vault/futures/patterns/energies_playbook.md`.

---

## Metals Analyst

### Product deep-dives — priority P1
- [x] P1 SI — Silver. File: `vault/futures/product_deep_dives/SI.md`. (2026-04-25 15:30 UTC — Fund Engineer)
- [x] P1 HG — Copper. File: `vault/futures/product_deep_dives/HG.md`. (2026-04-25 22:45 UTC — Fund Engineer)
- [x] P1 PA — Palladium. File: `vault/futures/product_deep_dives/PA.md`. (2026-04-25 18:45 UTC — Fund Engineer)
- [ ] P2 PL — Platinum. File: `vault/futures/product_deep_dives/PL.md`.
- [ ] P2 ALI — Aluminum. File: `vault/futures/product_deep_dives/ALI.md`.
- [ ] P2 MGC — Micro Gold. File: `vault/futures/product_deep_dives/MGC.md`.
- [ ] P2 SIL — Micro Silver. File: `vault/futures/product_deep_dives/SIL.md`.

### Playbooks — priority P2
- [ ] P2 Real-yield framework for metals (10Y TIPS, breakevens, gold reaction function). File: `vault/playbooks/metals_real_yields.md`.
- [ ] P2 Gold-silver ratio mean-reversion playbook. File: `vault/playbooks/gold_silver_ratio.md`.
- [ ] P3 Central-bank gold buying structural narrative. File: `vault/playbooks/cb_gold_buying.md`.

### Pattern library — priority P2
- [ ] P2 Metals pattern note — top recurring setups. File: `vault/futures/patterns/metals_playbook.md`.

---

## Grains Analyst

### Product deep-dives — priority P1
- [x] P1 ZC — Corn. File: `vault/futures/product_deep_dives/ZC.md`. (2026-04-25 19:45 UTC — Fund Engineer)
- [x] P1 ZS — Soybeans. File: `vault/futures/product_deep_dives/ZS.md`. (2026-04-25 23:35 UTC — Fund Engineer)
- [x] P1 ZW — Wheat (CBOT SRW) (2026-04-25 04:45 UTC — Fund Engineer). File: `vault/futures/product_deep_dives/ZW.md`.
- [ ] P2 ZL — Soybean Oil. File: `vault/futures/product_deep_dives/ZL.md`.
- [ ] P2 ZM — Soybean Meal. File: `vault/futures/product_deep_dives/ZM.md`.
- [ ] P3 ZO — Oats. File: `vault/futures/product_deep_dives/ZO.md`.
- [ ] P3 ZR — Rough Rice. File: `vault/futures/product_deep_dives/ZR.md`.

### Playbooks & patterns — priority P2
- [ ] P2 WASDE reaction playbook (expanded). File: `vault/playbooks/wasde_expanded.md`.
- [ ] P2 Brazilian / Argentine weather season (Dec–Mar). File: `vault/playbooks/south_america_growing.md`.
- [ ] P2 Crush spreads (ZS vs ZL+ZM) primer. File: `vault/playbooks/crush_spreads.md`.
- [ ] P2 Grains pattern note — top setups. File: `vault/futures/patterns/grains_playbook.md`.

---

## Softs Analyst

### Product deep-dives — priority P1
- [x] P1 KC — Coffee. File: `vault/futures/product_deep_dives/KC.md`. (2026-04-25 23:50 UTC — Fund Engineer)
- [x] P1 CT — Cotton. File: `vault/futures/product_deep_dives/CT.md`. (2026-04-25 14:35 UTC — Fund Engineer)
- [x] P1 SB — Sugar. File: `vault/futures/product_deep_dives/SB.md`. (2026-04-25 12:50 UTC — Fund Engineer)
- [ ] P1 CC — Cocoa. File: `vault/futures/product_deep_dives/CC.md`.
- [ ] P2 OJ — Orange Juice. File: `vault/futures/product_deep_dives/OJ.md`.
- [ ] P2 LBR — Lumber. File: `vault/futures/product_deep_dives/LBR.md`.

### Playbooks & patterns — priority P2
- [ ] P2 Softs pattern note. File: `vault/futures/patterns/softs_playbook.md`.
- [ ] P2 Ethanol–sugar pivot (cross-asset, with energies analyst). File: `vault/playbooks/ethanol_sugar_pivot.md`.
- [ ] P3 Ivory Coast cocoa concentration risk primer. File: `vault/playbooks/cocoa_concentration.md`.
- [ ] P3 Lumber–housing-cycle playbook. File: `vault/playbooks/lumber_housing.md`.

---

## Livestock Analyst

### Product deep-dives — priority P1
- [x] P1 LE — Live Cattle. File: `vault/futures/product_deep_dives/LE.md`. (2026-04-25 23:55 UTC — Fund Engineer)
- [ ] P1 GF — Feeder Cattle. File: `vault/futures/product_deep_dives/GF.md`.
- [ ] P1 HE — Lean Hogs. File: `vault/futures/product_deep_dives/HE.md`.

### Playbooks & patterns — priority P2
- [ ] P2 Feed-cost transmission (grains → feeder-cattle breakeven). File: `vault/playbooks/feed_cost_transmission.md`.
- [ ] P2 Cattle-on-feed reaction playbook. File: `vault/playbooks/cattle_on_feed.md`.
- [ ] P2 Livestock limit-move sizing rules. File: `vault/playbooks/livestock_limit_moves.md`.
- [ ] P2 Livestock pattern note. File: `vault/futures/patterns/livestock_playbook.md`.

---

## Rates Analyst

### Priority 0 from 2026-04-23 backtest review
- [ ] P1 Add catalyst-required filter to rates entry rules. Rates Donchian lost −3.9R on 7 trades without a catalyst gate.

### Product deep-dives — priority P1
- [x] P1 ZT — 2Y T-Note. File: `vault/futures/product_deep_dives/ZT.md`. (2026-04-25 21:45 UTC — Fund Engineer)
- [ ] P1 ZF — 5Y T-Note. File: `vault/futures/product_deep_dives/ZF.md`.
- [ ] P1 ZB — 30Y T-Bond. File: `vault/futures/product_deep_dives/ZB.md`.
- [ ] P2 UB — Ultra Bond. File: `vault/futures/product_deep_dives/UB.md`.

### Playbooks — priority P2
- [ ] P2 Auction playbook (concession, takedown, post-auction setups). File: `vault/playbooks/treasury_auctions.md`.
- [ ] P2 Curve trading primer (2s10s, 5s30s) — DV01 sizing. File: `vault/playbooks/curve_trades.md`.
- [ ] P3 Fed-speak reaction playbook (Chair, Vice Chair, NY Fed president). File: `vault/playbooks/fed_speak.md`.

### Pattern library — priority P2
- [ ] P2 Rates pattern note. File: `vault/futures/patterns/rates_playbook.md`.

---

## FX Futures Analyst

### Product deep-dives — priority P1
- [x] P1 6B — British Pound. File: `vault/futures/product_deep_dives/6B.md`. (2026-04-25 23:58 UTC — Fund Engineer)
- [x] P1 6J — Japanese Yen. File: `vault/futures/product_deep_dives/6J.md`. (2026-04-25 04:15 UTC — Fund Engineer)
- [ ] P1 6A — Australian Dollar. File: `vault/futures/product_deep_dives/6A.md`.
- [ ] P2 6C — Canadian Dollar. File: `vault/futures/product_deep_dives/6C.md`.
- [ ] P2 6S — Swiss Franc. File: `vault/futures/product_deep_dives/6S.md`.
- [ ] P2 M6E — Micro Euro. File: `vault/futures/product_deep_dives/M6E.md`.

### Playbooks — priority P2
- [ ] P2 Rate-differential framework for G10 FX. File: `vault/playbooks/fx_rate_differentials.md`.
- [ ] P2 Carry-trade playbook (sizing, stop-at-fund-cost). File: `vault/playbooks/carry_trades.md`.
- [ ] P3 BOJ intervention history and asymmetry warning. File: `vault/playbooks/boj_intervention_risk.md`.

### Pattern library — priority P2
- [ ] P2 FX pattern note — session-handoff patterns, London-NY overlap. File: `vault/futures/patterns/fx_playbook.md`.

---

## Index/Macro Analyst

### Product deep-dives — priority P1
- [x] P1 NQ — Nasdaq-100. File: `vault/futures/product_deep_dives/NQ.md`. (2026-04-25 02:15 UTC — Fund Engineer)
- [x] P1 RTY — Russell 2000. File: `vault/futures/product_deep_dives/RTY.md`. (2026-04-25 01:20 UTC — Fund Engineer)
- [ ] P2 YM — Dow. File: `vault/futures/product_deep_dives/YM.md`.
- [ ] P2 MES/MNQ/M2K/MYM — Micro index family (one consolidated note). File: `vault/futures/product_deep_dives/index_micros.md`.

### Playbooks — priority P1
- [x] P1 Regime transition playbook (how to recognize & trade regime pivots). File: `vault/playbooks/regime_transitions.md`. (2026-04-25 16:25 UTC — Fund Engineer)
- [ ] P2 Dealer gamma / positioning playbook (opex, put walls, call walls). File: `vault/playbooks/dealer_gamma.md`.
- [ ] P2 Cross-asset transmission map (DXY → commodities → equities → rates). File: `vault/playbooks/cross_asset_transmission.md`.
- [ ] P3 VIX term structure playbook. File: `vault/playbooks/vix_term_structure.md`.

### Pattern library — priority P2
- [ ] P2 Index pattern note. File: `vault/futures/patterns/index_playbook.md`.
- [ ] P2 Macro trend-state weekly snapshot template. File: `vault/futures/patterns/trend_state.md`.

---

## Portfolio Manager

- [x] P1 Correlation matrix note — expected correlations across our tradeable symbols by regime. File: `vault/_meta/correlation_matrix.md`. (2026-04-25 20:35 UTC — Fund Engineer)
- [ ] P1 Size NG via options only (addendum to PM prompt). From 2026-04-23 backtest review.
- [ ] P2 Topstep Combine consistency-rule simulator doc (math + walk-through). File: `vault/_meta/topstep_consistency.md`.
- [ ] P2 Position sizing worked examples across 5 scenarios. File: `vault/playbooks/sizing_examples.md`.

---

## Risk Manager

- [x] P1 Risk-regime playbook: what to do when the book is in each of five states (flat-to-+5%, +5 to +20%, drawdown 0 to −5%, drawdown −5 to −10%, > −10%). File: `vault/playbooks/book_state_playbook.md` (2026-04-25 01:45 UTC — Fund Engineer).
- [ ] P2 Blow-up case studies — LTCM, Amaranth, Archegos, MF Global — what the risk officer missed. File: `vault/playbooks/blowup_case_studies.md`.
- [ ] P2 Stress-test scenarios for our current book under 5σ moves by sector. File: `vault/_meta/stress_scenarios.md`.

---

## Options Risk

- [ ] P1 Options structure primer — one-pager per allowed structure (long call, long put, debit spreads, credit spreads, iron condor, iron fly, calendar, diagonal) with Greeks profile, IV regime fit, typical DTE. File: `vault/playbooks/options_structures.md`.
- [ ] P2 IV-regime fit matrix: which structures fit which IV rank percentile. File: `vault/playbooks/iv_regime_fit.md`.
- [ ] P2 Pin-risk and assignment-risk protocols. File: `vault/playbooks/pin_and_assignment.md`.

---

## Compliance

- [ ] P1 Audit-trail checklist — what to verify weekly, monthly, quarterly. File: `vault/_meta/audit_checklist.md`.
- [ ] P2 Topstep rule-compliance walkthrough (DLL, TDD, consistency, scaling). File: `vault/_meta/topstep_compliance.md`.

---

## CIO

- [ ] P1 Daily brief template expansion — what a gold-standard brief looks like vs a minimal one. File: `vault/_templates/daily_brief_gold_standard.md`.
- [ ] P2 Regime-check template. File: `vault/_templates/regime_check.md`.

---

## Equity desk (learning mode — pick these during the equity idle window)

- [ ] P2 Growth/Tech watchlist curation (first 15 names with rationale). File: `vault/equities/watchlists/growth_tech.md`.
- [ ] P2 Defensive watchlist curation. File: `vault/equities/watchlists/defensive.md`.
- [ ] P2 Cyclicals watchlist curation. File: `vault/equities/watchlists/cyclicals.md`.
- [ ] P2 Financials watchlist curation. File: `vault/equities/watchlists/financials.md`.
- [ ] P3 Earnings-calendar ingestion playbook. File: `vault/playbooks/earnings_calendar.md`.
- [ ] P3 FDA/biotech binary-event calendar template. File: `vault/playbooks/biotech_binary_events.md`.
- [ ] P3 M&A window playbook. File: `vault/playbooks/ma_windows.md`.

---

## When this backlog is exhausted

If all P1/P2/P3 items are complete and agents are still idle:

- Revisit existing product deep-dives, add a "recent changes" appendix noting anything that's shifted since the seed version.
- Update `vault/regime/current.md` with a fresh weekly read.
- Update watchlists.
- Review the last month of journal entries and extract any recurring patterns — propose them as additions to `vault/playbooks/lessons_learned.md`.
- Flag items to the user via a `## Refinement ask` journal note.
