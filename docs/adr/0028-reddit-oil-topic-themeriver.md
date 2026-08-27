# 0028. Reddit oil-topic ThemeRiver on the Dashboard

## Status

Accepted

## Context

The Demo Dashboard ([0026](0026-streamlit-dashboard-is-the-demo.md)) framed chat with same-day Yandex headlines and a Brent Forecast chart. The customer asked for **topic modelling** of oil narratives over the last month as a graph, using [semenoffalex/reddit-llm](https://github.com/semenoffalex/reddit-llm) as the sample.

Yandex/ddgs cannot supply a dated 30-day news archive. Reddit's official JSON API is geo-blocked from Russian IPs; the sample already pages **Arctic Shift** with `before`. The sample's dashboard is a treemap over a full-corpus re-fit, not a time graph. Postgres and Kestra stay out of this Demo cut ([0026](0026-streamlit-dashboard-is-the-demo.md)). Local Torch stays out ([0025](0025-openrouter-embeddings-no-local-torch.md)).

## Decision

The Dashboard shows an Altair **ThemeRiver** (centered stack) of oil-related Reddit discussion for the last **30 Moscow calendar days**, full width under chat | Brent. Stream **width is the sum of `num_comments`** on posts in that topic that day — not 100% shares and not fetched comment bodies.

Corpus: Arctic Shift posts from `r/oil`, `r/energy`, `r/CrudeOil`, `r/commodities`, keyword-filtered, dropping NSFW / stickied / removed. Clustering reuses the sample's **precomputed-embedding HDBSCAN** (UMAP when n ≥ 15) without importing BERTopic or Torch. Embeddings are OpenRouter Nemotron; labels are short Russian strings from DeepSeek. The chart shows the top six clusters plus **«Прочее»**. One fit per cache generation (TTL 6 hours, or an explicit refresh). Click a stream to list up to 20 posts in that topic for the whole window, sorted by comments.

Storage is a **JSON cache** on a shared Docker volume so the Ouroboros skill `oil_gas_topics` can read the same payload. The skill returns an overview (labels, rose/fell, 2–3 headlines). It is model-chosen, not injected into every turn.

## Consequences

- Analyst image gains `hdbscan` and `umap-learn` (no SentenceTransformer / Torch).
- Axis is independent of the Brent Forecast chart (no shared x, no forecast overlay).
- Arctic Shift or embedding failures yield an empty chart / empty skill payload — no invented topics.
- [0026](0026-streamlit-dashboard-is-the-demo.md) layout C is extended, not replaced.
