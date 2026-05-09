---
name: News subscription ToS caveats
description: WSJ / Bloomberg / Barron's / FT consumer subs cannot be programmatically scraped; user's manual summaries are the legitimate paywall path
type: feedback
originSessionId: 0fb1ece1-0ed0-47f7-9c25-6b7ec073a6ec
---
User has consumer subscriptions to WSJ, Bloomberg, CNBC, and is active on X/Twitter. They asked for the agents to have "full access" to these. Honest answer to remember:

- **WSJ, Bloomberg.com, Barron's, FT** — consumer subscriptions explicitly forbid programmatic access. Scraping risks the user's personal account being banned. This is a real risk, not a theoretical one. Do NOT wire agent tools to scrape these sites.
- **Legitimate paths**:
  - RSS headlines (free, public, allowed) — wired in `config/news_sources.yaml`.
  - The user's own 2-paragraph summaries to `vault/news_imports/` — the legit, high-signal path for paywalled content.
  - Dow Jones Newswires API for enterprise WSJ — expensive, enterprise tier.
  - BLPAPI for Bloomberg — only if Terminal is logged in on the host machine; academic licenses have redistribution limits.
  - CNBC is mostly not paywalled; agents can `fetch_url` CNBC article URLs directly.
- **Twitter/X**: official API. Basic tier ~$100/mo sufficient for agent polling of a curated watchlist + keyword queries. Free tier (10 reads/month) is unusable for this purpose. Scraping Twitter = ban risk.

**Why:** The user is building a real-money operation. Losing their personal WSJ/Bloomberg subscriptions due to automated-access ToS violations would be a self-inflicted wound and a recurring cost to re-provision. Keeping it clean is a risk-management decision, not a compliance-pedantry decision.

**How to apply:**
- Never add a tool or script that scrapes bloomberg.com, wsj.com, ft.com, barrons.com, economist.com, seekingalpha.com with the user's cookies. `config/news_sources.yaml:tos_guardrails.never_fetch_hosts` already blocks these at the fetch layer.
- When the user wants Bloomberg data, offer the two paths: BLPAPI (if available locally) or manual imports.
- When the user asks to "just scrape WSJ," push back with the ToS + account-ban argument, and offer the manual-import workflow as the alternative.
- The X API at Basic tier IS a legitimate path; budget for it when the user wants real-time social signal.
