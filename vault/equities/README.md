---
type: index
---

# Equities desk brain

The fund cannot trade equities yet — no broker is wired. This folder is the equities desk's learning space. When `config/equities.yaml: trading.trading_enabled` flips to true and a broker is implemented, the agents operating on this knowledge base will be ready.

## Folders

- **[[watchlists/]]** — live sector watchlists curated by the four sector analysts.
- **[[theses/]]** — one note per name with a live view. Analysts write and update.
- **[[shadow_trades/]]** — the shadow-trade ledger (same format as futures side).
- **[[reviews/]]** — weekly and per-trade reviews.

## Workflow (learning mode)

1. Sector analyst picks 1–3 names per wake from their seed watchlist.
2. Writes or updates thesis under `theses/{TICKER}.md`.
3. If conviction is med or high with a clean invalidation level, proposes a shadow trade.
4. Equity PM sizes the shadow trade as if it were real.
5. Shared Risk Manager + Options Risk review and vote.
6. Equity Execution Trader writes an execution plan (but places no order).
7. Every Sunday: review the week's shadow trades, compute hit rate and R-multiples, update lessons.

## When we go live

Same flow — the only difference is that the Execution Trader calls a real broker tool. Every other step is identical. That's the point: by the time we go live, the process is practiced.
