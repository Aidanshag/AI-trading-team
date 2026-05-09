---
type: social_watchlist
platform: twitter
updated: 2026-04-23
---

# Twitter / X — account watchlist

Accounts the fund polls when the X API is enabled. Curated by the user; high-signal-to-noise bias.

## Format

Grouped by beat. Each line: `@handle — what they're best at — priority (high|med|low)`.

## Macro / Fed

- @NickTimiraos — WSJ Fed reporter; closest thing to a Fed leak — high
- @LizAnnSonders — Charles Schwab CIO; macro data commentary — med
- @federalreserve — official Fed account — high
- @ECB — official ECB — med
- @BOJ_Bloomberg — BOJ reporter list — low

## Equities / Flow

- @jasongoepfert — sentiment & positioning data — med
- @charliebilello — chart-driven macro context — med

## Commodities / Energy

- @JavierBlas — Bloomberg commodities — high
- @ANAS_ALHAJJI — oil markets — high
- @SStapczynski — Bloomberg LNG — med

## Rates / Credit

- @michaelx_chen — rates flow color — med
- @petereavis — credit & IB — low

## Options / Vol

- @CorroCapital — single-name options and flows — med
- @SqueezeMetrics — dealer gamma / positioning — med

## Geopolitics

- @RaghuramRajan — economic geopolitics — med
- @AnthonyMKreis — policy/law — low
- @ForeignPolicy — med

## General news

- @Reuters — med (filter aggressively; much noise)
- @business (Bloomberg) — med
- @WSJMarkets — high

## User's own additions (edit freely)

*(leave blank; fill in as the user finds signal sources)*

---

## Polling rules (enforced by news tool when twitter is enabled)

- **Priority high**: poll every 5 min during market hours.
- **Priority med**: poll every 15 min during market hours.
- **Priority low**: poll every 60 min.
- Off-hours / weekends: halve all frequencies.
- Any tweet with >1,000 likes AND <30 min old from a high-priority account → immediate CIO wake with the tweet content as context.

## Ingestion

Each polled batch of tweets becomes a dated note under `vault/social/twitter_ingest/YYYY-MM-DD/HHMM_handle.md` and a row in `news_items` with source=`twitter`. Agents query this as part of their wake read.
