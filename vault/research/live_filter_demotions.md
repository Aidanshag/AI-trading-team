# Live-filter demotion log

Audit trail of cells demoted from `live_allowlist` by `scripts/validate_live_filter.py`. Each entry is a structural breakdown (negative exec_mirror, target below first tier, or friction-poisoned).

## 2026-05-12T17:24:22.179840+00:00 — validate_live_filter demoted 6 cells

- `fair_value_gap/MNQ/Asian/long` — target=$79 < $80 first-tier floor AND exec_avg negative
- `order_block_d1/6B/London/long` — exec_avg_r=-0.32R < floor -0.30R (n=16)
- `inside_bar_break/NG/London/short` — exec_avg_r=-0.45R < floor -0.30R (n=82)
- `pivot_reversal/MES/Asian/short` — exec_avg_r=-0.48R < floor -0.30R (n=51)
- `fair_value_gap_tuned/6E/Asian/short` — exec_avg_r=-0.78R < floor -0.30R (n=34)
- `liquidity_sweep_tuned/6E/London/long` — exec_avg_r=-0.35R < floor -0.30R (n=41)
