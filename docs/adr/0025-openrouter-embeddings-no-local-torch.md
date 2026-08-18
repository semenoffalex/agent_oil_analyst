# 0025. Report embeddings via remote API; no local Torch

## Status

Accepted

## Context

[0007](0007-e5-chroma-reports.md) baked `multilingual-e5-base` into the image so retrieve needed no embedding API. On ARM Docker that path pulls PyTorch (often CUDA/cuDNN wheels) and Hugging Face weights, which stalls Demo builds. The product owner required this stage to cover compute with external APIs and **not** download CUDA or Torch.

Chat still goes through OpenRouter ([0023](0023-main-openrouter-glm52-free.md)). Embeddings are a separate OpenAI-compatible host.

## Decision

Retrieve embeds chunks and queries through an OpenAI-compatible `/v1/embeddings` endpoint. Default is the LAN LM Studio at `http://192.168.0.55:1234/v1`, model `text-embedding-multilingual-e5-base`, API key `lm-studio` (dummy). Override with `EMBEDDING_BASE_URL`, `EMBEDDING_MODEL`, `EMBEDDING_API_KEY`. Chroma still stores vectors in-process.

E5 query/passage prefixes are applied when the model id contains `e5` (or `EMBEDDING_USE_E5_PREFIXES` is set).

There is **no** local SentenceTransformer, **no** baked e5 weights, and **no** silent fallback to Torch. A dead embedding HTTP call fails loudly. Embeddings do **not** require `OPENROUTER_API_KEY`.

Chunk size still uses heading-then-cap ([0015](0015-heading-chunks.md)); the cap counts whitespace tokens so ingest does not load `transformers`.

## Consequences

- First retrieve/ingest needs network to the embedding host. Docker must reach the LAN IP (or `host.docker.internal`).
- Switching embedding model requires a Chroma rebuild (fingerprint includes the model id).
- Image builds no longer download Torch or Hugging Face weights.
- [0007](0007-e5-chroma-reports.md) remains for Chroma-in-process; its “no second embedding API / bake e5” clause is superseded here. [0017](0017-next-cycle-is-public-demo.md) “use image e5” is superseded the same way.
