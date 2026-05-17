---
type: index
purpose: Data pulls + dataset metadata for the IB workstream
---

# IB data store

Historical bars, snapshot logs, and dataset metadata pulled from IB's API. Distinct from `state/bars/` (which is Topstep/ProjectX bars). When IB Phase 2 (historical backfill) runs, parquets land in `state/ib_bars/<symbol>_<bar_size>_<date>.parquet` and a summary index is written here.

## What's expected here

- `index.md` — running index of pulled datasets with dates + bar counts + size
- `aapl_daily_10y_<date>.md` — sample / metadata files for noteworthy pulls
- `multi_regime_validation_<date>.md` — analysis docs that use IB data
