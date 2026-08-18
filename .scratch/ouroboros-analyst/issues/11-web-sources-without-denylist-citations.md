# 11 — Web sources without denylist citations

**What to build:** On a freshness or live-quote question, the Analyst may search the Web; the reply tags `[Источник: …, web]`. Yellow-press denylist domains (kp.ru, dailymail.co.uk, and the rest of the list) do not appear as citations. The host does not strip those URLs from raw hits; citing one is a prompt failure. Unlisted tabloids may still leak.

**Blocked by:** 09 — Chainlit talks to Ouroboros

**Status:** ready-for-agent

- [ ] Web search is a tool in the Ouroboros loop (DuckDuckGo or equivalent); the model chooses when to call it (no Route-list host gate).
- [ ] Visible citations never include denylist domains; there is no required host drop of those hits before the model sees them.
- [ ] Empty Web results surface as uncertainty, not invented news.
- [ ] A latest-statement or Brent-today question can carry Web tags; combined Report + Web is allowed when retrieve also ran.
