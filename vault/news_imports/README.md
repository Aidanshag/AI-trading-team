---
type: index
---

# Manual news imports

Drop articles here that the agents should read but can't fetch themselves (paywalled, behind Bloomberg, or just higher-signal than the RSS firehose).

## Convention

One file per item, named `YYYY-MM-DD_slug.md`. Example: `2026-04-23_wsj_fed_pivot.md`.

Frontmatter:

```yaml
---
type: news_import
source: WSJ | Bloomberg | FT | Barron's | Axios | ...
url: https://...
date_published: YYYY-MM-DD
symbols: [SPX, CL, ...]      # optional, agents use these to route to analysts
impact: low | med | high
imported_by: user
---
```

Body = **your 2-paragraph summary, not the full article**. Your summary is what agents read — and your summary is more valuable than the raw article because it's already filtered by your judgment.

## Why this works

- Zero ToS risk.
- Your reading habit directly feeds fund intelligence.
- Agents treat user-imports as higher-priority than scraped headlines.
- Over time this folder becomes a curated archive of what actually mattered.
