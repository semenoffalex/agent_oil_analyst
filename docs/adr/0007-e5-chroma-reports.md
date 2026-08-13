# 0007. multilingual-e5 + Chroma for Reports

## Status

Accepted

## Context

Report retrieval needs an embedding model and a vector store. The chat LLM is DeepSeek V4 Flash ([0006](0006-deepseek-chat-llm.md)); that API does not embed PDFs.

Alternatives: OpenAI embeddings (second vendor, weaker Russian), BGE-M3 + Qdrant (extra container), multilingual-e5 + FAISS files (no metadata filters).

The corpus is a folder of PDFs in Docker, mixed RU/EN, not a search product.

## Decision

v1 embeds Report chunks with `intfloat/multilingual-e5-base` and stores them in Chroma in-process, persisted on a volume. No OpenAI embedding key. No Qdrant container.

Ingest uses the E5 passage prefix; queries use the query prefix. Chunks keep report title, date, and page as metadata.

## Consequences

- First Docker run downloads the E5 weights (or they are baked into the image).
- Date/title filters are whatever Chroma metadata filters give us; we do not get Qdrant-grade search.
- Re-ingest is required when PDFs or chunking change.
- Switching store later means a new index, not a config flag.
