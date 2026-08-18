# 10 — Grounded Report retrieve

**What to build:** On a corpus-covered demand question (OPEC 2026 world oil demand), the Analyst retrieves Reports this turn and the visible answer includes a grounded `[Отчёт …]` tag (title, date if known, pages, excerpt when the Chunk is a Sample Report). A live reply that omits the tag is not host-patched. Sample Reports ship in git; missing samples break install. Extra Web tags beside the Report tag are allowed.

**Blocked by:** 09 — Chainlit talks to Ouroboros

**Status:** resolved

- [x] Report retrieve is a reviewed extension tool in the Ouroboros loop (e5 + Chroma, heading-then-512 Chunks, metadata preserved).
- [x] Corpus-covered demand outlook: `[Отчёт …]` present and backed by retrieve this turn; tag without retrieve fails the seam test.
- [x] Live successful compose is not appended a Report block because the prose lacked «Отчёт».
- [x] Sample citations say excerpt; Full Report ingest remains optional, loud, non-fatal; IEA stays out; OPEC, EIA, CBR remain.
- [x] Russian demand questions can still retrieve English Chunks; the Analyst may answer in the user’s language without inventing figures.

## Answer

Retrieve is the `oil_gas_retrieve` extension (`retrieve_reports`) inside the Ouroboros tool loop, not a Chainlit waterfall. Grounding is `[Отчёт` **and** `retrieved` this turn; a live reply without the tag is left as-is. Sample labels still say excerpt; missing samples still break ingest. English chunks may answer a Russian question.
