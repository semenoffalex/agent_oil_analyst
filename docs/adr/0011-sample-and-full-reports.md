# 0011. Sample Reports in git, Full Reports via script

## Status

Partially superseded: a CBR Sample Report is in the corpus — [0016](0016-cbr-sample-report.md). IEA is still out. OPEC and EIA English remain the primary offline demo.

## Context

The spec allows PDFs in `/data` or a download script. Alternatives were git-only binaries, script-only (offline RAG dies), or handwritten markdown pretending to be agency reports.

Docker must retrieve *something* on a dark network. Reviewers should still be able to ingest real editions when they have net.

IEA was dropped: their PDFs often sit behind a login. A Russian sample was dropped: v1 is OPEC + EIA only.

## Decision

v1 commits two Sample Reports:

- `/data/samples/opec-momr-excerpt.pdf` — a few pages from an OPEC Monthly Oil Market Report (supply/demand tables)
- `/data/samples/eia-steo-excerpt.pdf` — a few pages from an EIA Short-Term Energy Outlook

The ingest script fetches the latest **Full** OPEC MOMR and EIA STEO PDFs into `/data/reports`. IEA is not in v1.

Chroma indexes both trees. Missing Full Reports is not a crash. Missing Sample Reports is a broken install.

Citations for samples must include title, date if known, page, and the word excerpt.

## Consequences

- The offline “answer from a Report” demo is OPEC+EIA English excerpts. Russian-only questions may Thin-retrieve and go to the web.
- Combined demos that need a dated full MOMR need a successful ingest.
- README must state: samples are short excerpts; Full Reports are downloaded by the user.
