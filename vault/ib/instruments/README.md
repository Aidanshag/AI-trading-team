---
type: index
purpose: Per-instrument deep-dives for IB-tradable products
---

# IB instrument library

Deep-dives on specific instruments traded through IB. Distinct from `vault/futures/product_deep_dives/` which is the Topstep futures universe.

## What goes here

- One file per instrument (or group of similar instruments)
- Sections: contract spec, typical volume, fee/commission, data subscription requirements, our strategies that target it
- Cross-link to `vault/futures/` if Topstep also trades a similar/related instrument (e.g., AAPL options here, AAPL stock on IB; ES futures on Topstep AND IB)

## Example instruments to seed (when IB Phase 2 starts pulling data)

- `AAPL.md` — Apple stock + options
- `SPY.md` — S&P 500 ETF
- `BTC.md` — Bitcoin futures + crypto
- `EUR.md` — Euro FX (Topstep has 6E; IB has spot + EUR.USD pair)
- `TLT.md` — long bond ETF (Topstep has ZN/ZB; IB has ETF version + options)
