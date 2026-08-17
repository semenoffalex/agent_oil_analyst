# 0012. Always retrieve k=10; DeepSeek drops irrelevant chunks

## Status

Accepted

## Context

Thin retrieval in [0003](0003-thin-or-fresh-web.md) needed a mechanical bar (chunk count and/or score). Count-only lets junk count as “enough.” Score cutoffs on e5+Chroma are poorly calibrated. Empty-only almost never fires.

The remaining option was: always retrieve, let the chat model drop irrelevant chunks.

That is not a search policy for the web. It is a citation policy for Reports. Using DeepSeek as a pre-search classifier was rejected in [0005](0005-closed-route-lists.md); this decision is **after** retrieval, on chunks already in hand.

## Decision

Every question retrieves `k=10` Report chunks. DeepSeek may Drop chunks and must not cite them. There is no count or cosine bar that opens the web.

The Time-sensitive Route list still opens the web ([0003](0003-thin-or-fresh-web.md)). Whether the Analyst may call web after Dropping every chunk is still open.

## Consequences

- The graph always pays for Report retrieval, including “what’s the weather.”
- A scripted “corpus missed it → web” demo no longer follows from Thin. It needs either a Time-sensitive marker or a later decision that zero kept chunks may call web.
- Citations only from chunks that were not Dropped, plus Web sources when that path ran.
