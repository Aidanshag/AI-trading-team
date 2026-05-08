---
type: live_vs_oos_tracker
date: 2026-05-08T04:41:41.289726+00:00
trades_evaluated: 13
unique_cells: 8
---

# Live R-multiple vs OOS prediction — 2026-05-08

Tracks 14-day rolling live performance per cell. 
Compare live mean R against the OOS-predicted E to detect 
edge decay or unexpected outperformance.

## Per-cell comparison

| Cell | n_live | mean_live_R | total_$ | OOS_E | gap | flag |
|---|---:|---:|---:|---:|---:|---|
| inside_bar_break|NG|London|short | 1 | -10.03 | $-702.12 | +0.26 | -10.29 | ok |
| narrow_range_break|GC|Asian|short | 3 | -0.08 | $-94.14 | +0.48 | -0.56 | ⚠ UNDERPERFORM |
| narrow_range_break|MCL|Asian|long | 4 | -0.49 | $-54.56 | +0.41 | -0.90 | ⚠ UNDERPERFORM |
| narrow_range_break|MCL|Asian|short | 1 | +52.08 | $+1,197.88 | +0.00 | +52.08 | — |
| narrow_range_break|MES|Asian|long | 1 | -15.51 | $-368.48 | -0.23 | -15.29 | — |
| narrow_range_break|MES|PostClose|short | 1 | -0.09 | $-2.74 | -0.68 | +0.59 | — |
| narrow_range_break|MNQ|PostClose|short | 1 | -0.21 | $-2.74 | -0.21 | -0.00 | — |
| narrow_range_break|NG|PostClose|long | 1 | +3.97 | $+277.88 | +0.15 | +3.82 | ok |

## Summary

- **Cells with edge holding (live ~ OOS)**: 2
- **Underperforming or decaying** (consider demotion): 2
- **Overperforming** (sample-size luck or real): 0

### Cells flagged for review

- `narrow_range_break|GC|Asian|short` — n=3, live_R=-0.08 vs OOS_E=+0.48
- `narrow_range_break|MCL|Asian|long` — n=4, live_R=-0.49 vs OOS_E=+0.41
