---
type: macro_brief
date: 2026-05-06
generated_at: 2026-05-06T23:55:00Z
generated_by: Cowork (Claude)
applies_to: [CIO, Risk Manager, Quant Researcher, Edge Hunter, all analysts]
read_on_first_wake: true
---

# Macro brief — 2026-05-06 (Wed)

> Daily situational awareness for the front-office. Cross-checks against the live `gap_fill` Treasury edge: anything that shifts gaps from flow-driven (fade works) toward information-driven (fade fails).

## Headline market levels

| Series | Level | Context |
|---|---:|---|
| 10Y Treasury yield (DGS10) | **4.42%** | Edged down today after rising +6bp on 5/5 to highest level since July 2025. Implies ZN/ZB selling off into yield rise overnight, then bid back today. |
| 30Y Treasury yield | ~ (verify) | Watch for repricing into 5/13 30Y auction (see below). |
| DXY (US Dollar Index) | **98.49 / ~98.5** | Up 0.12% on 5/5; supported by safe-haven demand on Middle East tension. |
| VIX | ~mid-teens (April 16.89) | Equity vol benign — gap_fill mechanic prefers benign vol. |

(Real yield / 10Y TIPS, 2s10s, Move index — not pulled in this manual brief; the FRED fetcher script will populate next iteration.)

## This week's known catalysts

### Treasury supply (ZN / ZB / ZT / ZF directly relevant)

- **Tue 2026-05-12 13:00 ET** — 10Y note auction, $42B, maturing 2036-05-15.
- **Wed 2026-05-13 13:00 ET** — 30Y bond auction, $25B, maturing 2056-05-15.
- Settlement Friday 2026-05-15.

**Implication for `gap_fill`**: pre-auction concession days (typically Mon 5/11 + Tue 5/12 morning before the 10Y; Tue 5/12 afternoon + Wed 5/13 morning before the 30Y) historically see directional drift. Per [[ZN]] thesis "What would kill it" — auction concession days can produce sustained directional moves that don't fade. Recommend treating Mon 5/11 → Wed 5/13 as elevated-risk window for ZN/ZB long fades specifically.

### FOMC

- **Last meeting**: 2026-04-28/29 (concluded, no blackout currently active)
- **Next meeting**: **2026-06-16/17** — well outside this week. No FOMC blackout in effect.
- Speakers can speak freely this week (verify live calendar — fetcher script will replace this manual check).

### Geopolitical

- Middle East violence threatening 4-week US-Iran ceasefire was the cited driver of safe-haven flows on 5/5.
- Oil dropped ~4% on 5/6 (counterintuitive vs Middle East risk — possibly demand-side weakness or specific OPEC headlines).
- **Implication**: cross-asset noise. Bond moves driven by safe-haven flows (rather than yield-curve flow) tend to be more sustained and less mean-reverting → gap_fill caution.

## Regime read for the locked-in edge

**Current state for `gap_fill` on ZN/ZB/ZT/ZF:**

- 10Y at multi-month high yield (4.42%, just off the 5/5 highest-since-July 2025 print). Sustained yield uptrend means rates futures are in a directional regime, not a chop/range regime. **Gap-fill works best in chop/range; risk that overnight gaps extend rather than fade is elevated.**
- DXY at 98.5 — neither a clear strong-dollar regime nor a weak-dollar one.
- Equity vol benign (mid-teens). Supportive — gap_fill assumes orderly flows.
- Geopolitical risk-on/off oscillation (Iran ceasefire wobbling) means safe-haven flows can spike unpredictably.

**Net read**: cautiously favorable, but the rates uptrend is the main risk. Recommend the Risk Manager lean toward `allow_with_modifications` (smaller size) on any gap_fill long signal during a session that opens with a fresh yield jump.

## Things to verify in the live data path before the next fire

1. The high-impact economic calendar at `vault/economic_calendar/today.json` includes the 5/12 and 5/13 auctions. If not, the blackout gate won't catch them.
2. `state/strategy_validation.json:live_strategies_filter` is still locked to gap_fill on ZN/ZT/ZB/ZF (verified 22:24 UTC yesterday).
3. The auto_trader's `_audit_risk_config_drift` has not flagged any disabled gates today.

## What to watch tomorrow (5/7 Thu)

- Initial jobless claims, 8:30 ET — labor market read; surprises move the front end (ZT especially).
- Any unscheduled Fed-speaker news (verify via fetcher once built).
- 30Y bond outright direction into the 5/13 auction.

---

**Note on this brief:** Generated manually via web search as a worked example (2026-05-06 23:55 UTC). The structural fetchers (`scripts/fetch_treasury_auctions.py`, `scripts/fetch_fed_speakers.py`, `scripts/fetch_fred_macro_levels.py`, `scripts/generate_macro_brief.py`) will produce this automatically going forward — see `vault/_meta/cowork_session_log.md`. Recommended schedule: daily 06:00 ET pre-RTH, autosent to vault.

Sources used (manual):
- TreasuryDirect refunding announcement & auction schedule for May 2026
- federalreserve.gov FOMC calendar
- FRED DGS10 / DTWEXBGS series pages
- Trading Economics for current 10Y level + market context
