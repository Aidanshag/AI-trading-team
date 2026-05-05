---
type: backtest
date: 2026-05-04T21:26:40.929469+00:00
strategies: [fair_value_gap, order_block, liquidity_sweep]
symbols: ['MES', 'MNQ', 'NG', 'MCL', 'GC', 'ZN', '6E']
timeframe: 5m
period: 30d
data_source: yfinance
---

# Price-action strategy backtest — 30d intraday

## Per-symbol-per-strategy results

| Strategy | Symbol | Trades | Hit% | Avg R | Exp R |
|---|---|---:|---:|---:|---:|
| fair_value_gap | MES | 372 | 32.0% | -0.05 | -0.05 |
| fair_value_gap | MNQ | 392 | 35.5% | +0.06 | +0.06 |
| fair_value_gap | NG | 305 | 38.0% | +0.14 | +0.14 |
| fair_value_gap | MCL | 353 | 26.9% | -0.20 | -0.20 |
| fair_value_gap | GC | 426 | 32.9% | -0.02 | -0.02 |
| fair_value_gap | ZN | 211 | 31.3% | -0.06 | -0.06 |
| fair_value_gap | 6E | 460 | 33.5% | +0.00 | +0.00 |
| order_block | MES | 108 | 35.2% | +0.06 | +0.06 |
| order_block | MNQ | 105 | 34.3% | +0.03 | +0.03 |
| order_block | NG | 126 | 29.4% | -0.12 | -0.12 |
| order_block | MCL | 96 | 32.3% | -0.03 | -0.03 |
| order_block | GC | 114 | 27.2% | -0.18 | -0.18 |
| order_block | ZN | 86 | 30.2% | -0.09 | -0.09 |
| order_block | 6E | 128 | 39.8% | +0.20 | +0.20 |
| liquidity_sweep | MES | 414 | 29.5% | -0.12 | -0.12 |
| liquidity_sweep | MNQ | 451 | 32.8% | -0.01 | -0.01 |
| liquidity_sweep | NG | 53 | 37.7% | +0.15 | +0.15 |
| liquidity_sweep | MCL | 381 | 38.3% | +0.15 | +0.15 |
| liquidity_sweep | GC | 472 | 32.8% | -0.02 | -0.02 |
| liquidity_sweep | ZN | 161 | 28.0% | -0.16 | -0.16 |
| liquidity_sweep | 6E | 379 | 34.3% | +0.03 | +0.03 |

## Per-strategy aggregate (across all symbols)

| Strategy | n | Hit% | Weighted E[R] |
|---|---:|---:|---:|
| fair_value_gap | 2519 | 32.9% | -0.02R |
| order_block | 763 | 32.8% | -0.02R |
| liquidity_sweep | 2311 | 33.1% | -0.01R |
