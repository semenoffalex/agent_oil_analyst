# 0015. Heading-first chunks, cap 512 tokens

## Status

Accepted

## Context

Report chunks must keep title, date, and page. Alternatives were one-page-one-chunk (coarse vectors), a flat 800/150 token window (tables split mid-row), or a 400-character smash.

MOMR and STEO are sectioned publications. A layout-perfect parser is out of scope; heading regexes plus a cap is the v1 contract.

## Decision

Ingest splits Full and Sample Reports on section headings (agency-specific regexes in `config/ingest.yaml`), then caps each piece at 512 tokens using the multilingual-e5 tokenizer. Oversized sections split with a 50-token overlap. Metadata: report title, date, page range, heading.

## Consequences

- Ingest is not “pdf to splitter.” Heading patterns will miss some STEO boxes and MOMR appendices; those become leftover chunks under `heading: (untitled)`.
- Citations can name a section, not only a page.
- Changing regexes requires re-ingest.
