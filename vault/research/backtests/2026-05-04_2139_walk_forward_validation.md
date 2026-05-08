---
type: walk_forward_validation
date: 2026-05-04T21:39:35.492954+00:00
cutoff: 2026-04-17 00:56:15-04:00
---

# Walk-forward validation of gap_fill ZN edge

Splits 60d of 5m bars into 45d train + 15d held-out test.
Edge HOLDS if BOTH train and OOS E>0 AND OOS t>1.5.

## Results

| Label | n_train | E_train | t_train | n_oos | E_oos | t_oos | Holds |
|---|---:|---:|---:|---:|---:|---:|---|
| gap_fill on ZN — ALL sessions | 600 | +0.86R if tr else 0 | +15.29 if tr else 0 | 259 | +1.20R if te else 0 | +10.88 if te else 0 | ✓ HOLDS |
| gap_fill on ZN — Asian only | 490 | +0.87R if tr else 0 | +14.08 if tr else 0 | 197 | +1.04R if te else 0 | +10.19 if te else 0 | ✓ HOLDS |
| gap_fill on ZN — PostClose only | 95 | +0.82R if tr else 0 | +5.74 if tr else 0 | 59 | +1.29R if te else 0 | +6.26 if te else 0 | ✓ HOLDS |
| gap_fill on ZN — Asian+PostClose combined | 585 | +0.87R if tr else 0 | +15.21 if tr else 0 | 256 | +1.10R if te else 0 | +11.95 if te else 0 | ✓ HOLDS |
| gap_fill on MES — all | 36 | -0.16R if tr else 0 | -0.67 if tr else 0 | 9 | +1.49R if te else 0 | +0.90 if te else 0 | ✗ fails |
| gap_fill on MNQ — all | 26 | -0.39R if tr else 0 | -1.54 if tr else 0 | 9 | +3.18R if te else 0 | +1.49 if te else 0 | ✗ fails |
| gap_fill on NG — all | 72 | +0.64R if tr else 0 | +2.86 if tr else 0 | 38 | +0.83R if te else 0 | +1.53 if te else 0 | ✓ HOLDS |
| gap_fill on 6E — all | 37 | +1.50R if tr else 0 | +2.44 if tr else 0 | 17 | +2.65R if te else 0 | +3.63 if te else 0 | ✓ HOLDS |
| inside_bar_break MES — RTH only | 192 | -0.04R if tr else 0 | -0.39 if tr else 0 | 53 | +0.28R if te else 0 | +1.45 if te else 0 | ✗ fails |
| vwap_reversion MES — all sessions | 304 | -0.12R if tr else 0 | -0.45 if tr else 0 | 46 | -0.76R if te else 0 | -3.11 if te else 0 | ✗ fails |
| vwap_reversion MNQ — all sessions | 341 | +0.02R if tr else 0 | +0.08 if tr else 0 | 44 | -0.80R if te else 0 | -3.98 if te else 0 | ✗ fails |
