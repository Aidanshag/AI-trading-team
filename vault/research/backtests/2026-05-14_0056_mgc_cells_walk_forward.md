---
type: walk_forward_mgc_cells
date: 2026-05-14T00:56:56.317994+00:00
bar_source: GC=F yfinance proxy
cutoff: 2026-04-26 03:48:45-04:00
---

# MGC walk-forward validation

4 MGC cells added 2026-05-13 evening as shadow mirrors of GC parents.
Walk-forward uses GC=F bars as proxy (microstructure differences
acknowledged).

Bars: 13658 | OOS cutoff: 2026-04-26 03:48 ET

| Strategy | Session | Side | Train | OOS | Pass | Action |
|---|---|---|---|---|---|---|
| narrow_range_break | Asian | long | n= 120 hit= 31.7% E=-0.02R t=-0.16 | n=  47 hit= 48.9% E=+0.47R t=+1.99 | ✓ | PROMOTE → experimental=false |
| narrow_range_break | Asian | short | n= 124 hit= 43.5% E=+0.32R t=+2.29 | n=  35 hit= 51.4% E=+0.56R t=+2.03 | ✓ | PROMOTE → experimental=false |
| fair_value_gap_tuned | Asian | short | n=  79 hit= 27.8% E=-0.03R t=-0.14 | n=  30 hit= 46.7% E=+0.63R t=+1.95 | ✓ | PROMOTE → experimental=false |
| inside_bar_break | PostClose | long | n=  50 hit= 50.0% E=+0.31R t=+1.55 | n=  25 hit= 52.0% E=+0.48R t=+1.52 | ✓ | PROMOTE → experimental=false |

## Promotion summary

**Promoted to live (experimental=false candidates):**
- `narrow_range_break|MGC|Asian|long`
- `narrow_range_break|MGC|Asian|short`
- `fair_value_gap_tuned|MGC|Asian|short`
- `inside_bar_break|MGC|PostClose|long`

## Note on bar source

GC=F was used as the bar proxy because yfinance does not surface
an MGC-specific micro-contract series with sufficient history.
This is a known limitation. Live shadow_trade fills will provide
the MGC-specific microstructure validation over the next 2-5
sessions; this walk-forward serves only as the cold-start prior.
