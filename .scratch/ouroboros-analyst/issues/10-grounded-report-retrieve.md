# 10 — Grounded Report retrieve

**What to build:** On a corpus-covered demand question (OPEC 2026 world oil demand), the Analyst retrieves Reports this turn and the visible answer includes a grounded `[Отчёт …]` tag (title, date if known, pages, excerpt when the Chunk is a Sample Report). A live reply that omits the tag is not host-patched. Sample Reports ship in git; missing samples break install. Extra Web tags beside the Report tag are allowed.

**Blocked by:** 09 — Chainlit talks to Ouroboros

**Status:** ready-for-agent

- [ ] Report retrieve is a reviewed extension tool in the Ouroboros loop (e5 + Chroma, heading-then-512 Chunks, metadata preserved).
- [ ] Corpus-covered demand outlook: `[Отчёт …]` present and backed by retrieve this turn; tag without retrieve fails the seam test.
- [ ] Live successful compose is not appended a Report block because the prose lacked «Отчёт».
- [ ] Sample citations say excerpt; Full Report ingest remains optional, loud, non-fatal; IEA stays out; OPEC, EIA, CBR remain.
- [ ] Russian demand questions can still retrieve English Chunks; the Analyst may answer in the user’s language without inventing figures.
