---
type: index
---

# Sector watchlists

One note per sector. Live list of symbols currently being monitored with their state and conviction.

## Files

- `energies.md`
- `metals.md`
- `ags.md`
- `rates.md`
- `fx_futures.md`
- `index_macro.md`

## Format

Each list is a markdown table. Analysts update their own sector's list on every wake that materially changes a view.

```markdown
| Symbol | State | Conviction | Next catalyst | Last updated |
|---|---|---|---|---|
| [[CL]] | watching long | med | EIA Wed 10:30 ET | 2026-04-23 |
| [[NG]] | on standdown | n/a | winter storage data | 2026-04-20 |
```

States:
- **holding** — we have a shadow or real position
- **watching long / watching short** — waiting for trigger
- **ranging** — no view
- **on standdown** — explicitly NOT traded (e.g. pending event, liquidity issue)
- **avoid** — flagged by risk for a specific reason

Keep the list short. An analyst's watchlist should have ≤ 10 live entries. If it's longer, the analyst is watching too many names and not watching any of them well.
