# 0016. CBR trends bulletin is a Sample Report

## Status

Accepted

## Context

Story 31 and [0011](0011-sample-and-full-reports.md) kept v1 to OPEC + EIA English so ingest would not depend on IEA login. A Russian sample was dropped in that decision.

`data/samples/cbr_ec_research_mb_bulletin_26-05.pdf` (Банк России, «О чем говорят тренды») was added anyway. Russian oil-price questions can cite it; heading regexes are weaker than MOMR/STEO because the bulletin is a short macro note, not a sectioned oil report.

Alternatives: delete the PDF to match 0011, or accept it as a third Sample Report.

## Decision

v1 keeps the CBR bulletin as a Sample Report. Competence is still the oil market: Drop may discard inflation- and rates-only chunks. IEA stays out. OPEC and EIA remain the English backbone.

Ingest uses CBR heading patterns and known titles in `config/ingest.yaml` / `oil_gas_analyst/ingest.py`, same heading-then-512-token cap as other agencies ([0015](0015-heading-chunks.md)).

## Consequences

- A Russian question can retrieve a CBR Chunk without opening Web.
- Oil mentions often sit inside the bulletin title chunk, not a dedicated «Нефть» section.
- Citations may name Банк России. That is a Report, not a Web source.
- Re-ingest after heading regex changes.
