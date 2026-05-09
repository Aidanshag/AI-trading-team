---
type: index
---

# Pattern library

Recurring setups, per sector and cross-sector. Each pattern is one note with a **name, trigger, invalidation, exit, hit-rate target, and realized hit rate**.

## Rules

- **One note per pattern.** If a pattern has two variants, two notes.
- **Pattern must be testable.** If you can't write the trigger as a specific, measurable condition, it's a vibe, not a pattern — don't add it.
- **Realized hit rate** is updated from the shadow-trade ledger and real trades. When a pattern's rolling-100 hit rate drops below the target + buffer, flag for review.

## Categories

- `trend_state.md` — weekly snapshot of trend state (20/50/200 MA) for every tradeable symbol.
- Sector-specific: `energies_playbook.md`, `metals_playbook.md`, etc.
- Cross-sector: `event_window_fade.md`, `post_auction_bounce.md`, etc.

## Template

```yaml
---
type: pattern
sector: {{sector or cross}}
symbols: [list]
---
```

Body:

### Name and one-line description

### Trigger (specific, measurable)

### Invalidation level

### Entry and sizing

### Exit rules

### Historical hit rate target

### Realized hit rate (rolling 100)

### Notes and caveats
