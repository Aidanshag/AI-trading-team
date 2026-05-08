---
type: live_vs_oos_tracker
date: 2026-05-07T20:37:50.093709+00:00
trades_evaluated: 13
unique_cells: 8
---

# Live R-multiple vs OOS prediction — 2026-05-07

Tracks 14-day rolling live performance per cell. 
Compare live mean R against the OOS-predicted E to detect 
edge decay or unexpected outperformance.

## Per-cell comparison

| Cell | n_live | mean_live_R | total_$ | OOS_E | gap | flag |
|---|---:|---:|---:|---:|---:|---|
| inside_bar_break|NG|London|short | 1 | -10.03 | $-702.12 | +0.33 | -10.36 | ok |
| narrow_range_break|GC|Asian|short | 3 | -0.08 | $-94.14 | +0.52 | -0.60 | ⚠ UNDERPERFORM |
| narrow_range_break|MCL|Asian|long | 4 | -0.49 | $-54.56 | +0.41 | -0.90 | ⚠ UNDERPERFORM |
| narrow_range_break|MCL|Asian|short | 1 | +52.08 | $+1,197.88 | -0.03 | +52.11 | — |
| narrow_range_break|MES|Asian|long | 1 | -15.51 | $-368.48 | -0.25 | -15.27 | — |
| narrow_range_break|MES|PostClose|short | 1 | -0.09 | $-2.74 | -0.80 | +0.71 | — |
| narrow_range_break|MNQ|PostClose|short | 1 | -0.21 | $-2.74 | -0.29 | +0.08 | — |
| narrow_range_break|NG|PostClose|long | 1 | +3.97 | $+277.88 | +0.25 | +3.72 | ok |

## Summary

- **Cells with edge holding (live ~ OOS)**: 2
- **Underperforming or decaying** (consider demotion): 2
- **Overperforming** (sample-size luck or real): 0

### Cells flagged for review

- `narrow_range_break|GC|Asian|short` — n=3, live_R=-0.08 vs OOS_E=+0.52
- `narrow_range_break|MCL|Asian|long` — n=4, live_R=-0.49 vs OOS_E=+0.41
