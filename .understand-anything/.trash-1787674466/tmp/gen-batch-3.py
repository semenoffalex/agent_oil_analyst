#!/usr/bin/env python3
import json
from pathlib import Path


def n(**kwargs):
    return kwargs


def e(source, target, typ, weight):
    return {
        "source": source,
        "target": target,
        "type": typ,
        "direction": "forward",
        "weight": weight,
    }


nodes1 = [
    n(
        id="file:oil_gas_analyst/__main__.py",
        type="file",
        name="__main__.py",
        filePath="oil_gas_analyst/__main__.py",
        summary="CLI entry point for python -m oil_gas_analyst: downloads full agency reports and force-rebuilds the Chroma report index.",
        tags=["entry-point", "cli", "ingest", "chroma"],
        complexity="simple",
        languageNotes="Package __main__ module; run as python -m oil_gas_analyst.",
    ),
    n(
        id="function:oil_gas_analyst/__main__.py:main",
        type="function",
        name="main",
        filePath="oil_gas_analyst/__main__.py",
        lineRange=[10, 22],
        summary="Downloads full reports, builds index deps without auto-ingest, then force-runs ensure_index and prints the chunk count.",
        tags=["entry-point", "cli", "ingest"],
        complexity="simple",
    ),
    n(
        id="file:oil_gas_analyst/corpus_strip.py",
        type="file",
        name="corpus_strip.py",
        filePath="oil_gas_analyst/corpus_strip.py",
        summary="Builds dashboard corpus-strip entries (agency, title, date, excerpt, URL) from ingest sample config, preferring full-report links over redundant excerpts.",
        tags=["data-model", "dashboard", "corpus", "utility"],
        complexity="moderate",
    ),
    n(
        id="class:oil_gas_analyst/corpus_strip.py:CorpusStripEntry",
        type="class",
        name="CorpusStripEntry",
        filePath="oil_gas_analyst/corpus_strip.py",
        lineRange=[14, 39],
        summary="Frozen dataclass for one corpus-strip pill, with markdown and HTML link helpers for the Streamlit dashboard.",
        tags=["data-model", "dashboard", "serialization"],
        complexity="simple",
        languageNotes="Frozen dataclass with computed label and escaped HTML links.",
    ),
    n(
        id="function:oil_gas_analyst/corpus_strip.py:corpus_strip_entries",
        type="function",
        name="corpus_strip_entries",
        filePath="oil_gas_analyst/corpus_strip.py",
        lineRange=[57, 89],
        summary="Loads ingest config, drops redundant excerpts, and returns one CorpusStripEntry per agency sample with a resolvable PDF path.",
        tags=["factory", "corpus", "dashboard"],
        complexity="moderate",
    ),
    n(
        id="file:oil_gas_analyst/deps.py",
        type="file",
        name="deps.py",
        filePath="oil_gas_analyst/deps.py",
        summary="Wires Ouroboros loop, embedding-backed Chroma retriever, and full-report downloads for CLI ingest and Streamlit chat.",
        tags=["factory", "dependency-injection", "service", "ingest"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/deps.py:build_loop",
        type="function",
        name="build_loop",
        filePath="oil_gas_analyst/deps.py",
        lineRange=[22, 30],
        summary="Requires API keys, resolves the Ouroboros URL, enables domain skills, and returns a configured OuroborosLoop.",
        tags=["factory", "ouroboros", "entry-point"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/deps.py:enable_domain_skills",
        type="function",
        name="enable_domain_skills",
        filePath="oil_gas_analyst/deps.py",
        lineRange=[33, 67],
        summary="POSTs owner attest-review and skill toggle for playbook, retrieve, web, and forecast skills on the Ouroboros gateway.",
        tags=["ouroboros", "service", "http-client"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/deps.py:build_deps",
        type="function",
        name="build_deps",
        filePath="oil_gas_analyst/deps.py",
        lineRange=[70, 92],
        summary="Constructs a ChromaRetriever with the embedding API, optionally running ensure_index when the corpus fingerprint is stale.",
        tags=["factory", "retriever", "chroma", "ingest"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/deps.py:download_full_reports",
        type="function",
        name="download_full_reports",
        filePath="oil_gas_analyst/deps.py",
        lineRange=[106, 130],
        summary="Downloads configured full-report PDFs into REPORTS_PATH using ingest config URLs and optional HTTP headers.",
        tags=["ingest", "http-client", "corpus"],
        complexity="moderate",
    ),
    n(
        id="file:oil_gas_analyst/ingest.py",
        type="file",
        name="ingest.py",
        filePath="oil_gas_analyst/ingest.py",
        summary="PDF and page chunking for agency reports: heading-aware splits, token budgets, overlap, and YAML ingest-config loading.",
        tags=["ingest", "chunking", "pdf", "nlp"],
        complexity="complex",
    ),
    n(
        id="function:oil_gas_analyst/ingest.py:_is_heading",
        type="function",
        name="_is_heading",
        filePath="oil_gas_analyst/ingest.py",
        lineRange=[36, 46],
        summary="Detects section headings via compiled agency regexes or known heading-name prefixes.",
        tags=["chunking", "parsing", "utility"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/ingest.py:_flush",
        type="function",
        name="_flush",
        filePath="oil_gas_analyst/ingest.py",
        lineRange=[96, 149],
        summary="Emits Chunk objects from a buffered heading section, splitting on token limits with overlap and attaching agency metadata.",
        tags=["chunking", "data-model", "ingest"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/ingest.py:chunk_pages",
        type="function",
        name="chunk_pages",
        filePath="oil_gas_analyst/ingest.py",
        lineRange=[152, 208],
        summary="Walks extracted PDF page texts, splits on headings, and flushes heading-bounded Chunks using ingest-config token limits.",
        tags=["chunking", "ingest", "pdf"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/ingest.py:chunk_pdf",
        type="function",
        name="chunk_pdf",
        filePath="oil_gas_analyst/ingest.py",
        lineRange=[211, 236],
        summary="Extracts text from a PDF via pypdf and delegates to chunk_pages with optional ingest config and token counter.",
        tags=["chunking", "pdf", "ingest"],
        complexity="moderate",
    ),
    n(
        id="file:oil_gas_analyst/ouroboros.py",
        type="file",
        name="ouroboros.py",
        filePath="oil_gas_analyst/ouroboros.py",
        summary="HTTP client for the Ouroboros gateway: creates a task, polls until terminal, extracts the answer, tool flags, and citations.",
        tags=["service", "http-client", "ouroboros", "adapter"],
        complexity="moderate",
        languageNotes="Polls JSON task status over urllib with retry on supervisor startup.",
    ),
    n(
        id="class:oil_gas_analyst/ouroboros.py:OuroborosLoop",
        type="class",
        name="OuroborosLoop",
        filePath="oil_gas_analyst/ouroboros.py",
        lineRange=[26, 115],
        summary="AnalystLoop implementation that drives one Ouroboros task to completion and maps the payload to LoopResult.",
        tags=["service", "adapter", "ouroboros"],
        complexity="moderate",
        languageNotes="Satisfies AnalystLoop via complete(); uses urllib rather than a third-party HTTP client.",
    ),
    n(
        id="function:oil_gas_analyst/ouroboros.py:complete",
        type="function",
        name="complete",
        filePath="oil_gas_analyst/ouroboros.py",
        lineRange=[45, 78],
        summary="POSTs a task, polls GET until terminal or timeout, and returns LoopResult with answer text, tool flags, and citations.",
        tags=["ouroboros", "api-handler", "polling"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/ouroboros.py:_request",
        type="function",
        name="_request",
        filePath="oil_gas_analyst/ouroboros.py",
        lineRange=[79, 115],
        summary="JSON HTTP helper with timeout remaining, 503 retry while the supervisor starts, and LoopError on bad payloads.",
        tags=["http-client", "retry", "ouroboros"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/ouroboros.py:_answer_text",
        type="function",
        name="_answer_text",
        filePath="oil_gas_analyst/ouroboros.py",
        lineRange=[122, 141],
        summary="Pulls the user-facing answer from nested Ouroboros result shapes (string, outcome axes, or dict text fields).",
        tags=["parsing", "ouroboros", "utility"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/ouroboros.py:_citations_from_text",
        type="function",
        name="_citations_from_text",
        filePath="oil_gas_analyst/ouroboros.py",
        lineRange=[149, 161],
        summary="Regex-extracts report tags, markdown links, and bracketed web hosts into Citation objects.",
        tags=["parsing", "citations", "regex"],
        complexity="simple",
    ),
]

edges1 = []
for src, tgts in {
    "oil_gas_analyst/__main__.py": [
        "oil_gas_analyst/deps.py",
        "oil_gas_analyst/retrieve.py",
    ],
    "oil_gas_analyst/corpus_strip.py": [
        "oil_gas_analyst/ingest.py",
        "oil_gas_analyst/retrieve.py",
    ],
    "oil_gas_analyst/deps.py": [
        "oil_gas_analyst/ingest.py",
        "oil_gas_analyst/ouroboros.py",
        "oil_gas_analyst/settings.py",
    ],
    "oil_gas_analyst/ingest.py": ["oil_gas_analyst/types.py"],
    "oil_gas_analyst/ouroboros.py": [
        "oil_gas_analyst/settings.py",
        "oil_gas_analyst/types.py",
    ],
}.items():
    for t in tgts:
        edges1.append(e(f"file:{src}", f"file:{t}", "imports", 0.7))

contains_export = [
    ("file:oil_gas_analyst/__main__.py", "function:oil_gas_analyst/__main__.py:main", True),
    (
        "file:oil_gas_analyst/corpus_strip.py",
        "class:oil_gas_analyst/corpus_strip.py:CorpusStripEntry",
        True,
    ),
    (
        "file:oil_gas_analyst/corpus_strip.py",
        "function:oil_gas_analyst/corpus_strip.py:corpus_strip_entries",
        True,
    ),
    ("file:oil_gas_analyst/deps.py", "function:oil_gas_analyst/deps.py:build_loop", True),
    (
        "file:oil_gas_analyst/deps.py",
        "function:oil_gas_analyst/deps.py:enable_domain_skills",
        True,
    ),
    ("file:oil_gas_analyst/deps.py", "function:oil_gas_analyst/deps.py:build_deps", True),
    (
        "file:oil_gas_analyst/deps.py",
        "function:oil_gas_analyst/deps.py:download_full_reports",
        True,
    ),
    ("file:oil_gas_analyst/ingest.py", "function:oil_gas_analyst/ingest.py:_is_heading", True),
    ("file:oil_gas_analyst/ingest.py", "function:oil_gas_analyst/ingest.py:_flush", True),
    ("file:oil_gas_analyst/ingest.py", "function:oil_gas_analyst/ingest.py:chunk_pages", True),
    ("file:oil_gas_analyst/ingest.py", "function:oil_gas_analyst/ingest.py:chunk_pdf", True),
    (
        "file:oil_gas_analyst/ouroboros.py",
        "class:oil_gas_analyst/ouroboros.py:OuroborosLoop",
        True,
    ),
    ("file:oil_gas_analyst/ouroboros.py", "function:oil_gas_analyst/ouroboros.py:complete", False),
    ("file:oil_gas_analyst/ouroboros.py", "function:oil_gas_analyst/ouroboros.py:_request", False),
    (
        "file:oil_gas_analyst/ouroboros.py",
        "function:oil_gas_analyst/ouroboros.py:_answer_text",
        True,
    ),
    (
        "file:oil_gas_analyst/ouroboros.py",
        "function:oil_gas_analyst/ouroboros.py:_citations_from_text",
        True,
    ),
]
for src, tgt, exported in contains_export:
    edges1.append(e(src, tgt, "contains", 1.0))
    if exported:
        edges1.append(e(src, tgt, "exports", 0.8))
edges1.append(
    e(
        "class:oil_gas_analyst/ouroboros.py:OuroborosLoop",
        "function:oil_gas_analyst/ouroboros.py:complete",
        "contains",
        1.0,
    )
)
edges1.append(
    e(
        "class:oil_gas_analyst/ouroboros.py:OuroborosLoop",
        "function:oil_gas_analyst/ouroboros.py:_request",
        "contains",
        1.0,
    )
)

edges1 += [
    e(
        "function:oil_gas_analyst/__main__.py:main",
        "function:oil_gas_analyst/deps.py:download_full_reports",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/__main__.py:main",
        "function:oil_gas_analyst/deps.py:build_deps",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/deps.py:build_loop",
        "function:oil_gas_analyst/deps.py:enable_domain_skills",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/deps.py:build_loop",
        "class:oil_gas_analyst/ouroboros.py:OuroborosLoop",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ingest.py:chunk_pages",
        "function:oil_gas_analyst/ingest.py:_is_heading",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ingest.py:chunk_pages",
        "function:oil_gas_analyst/ingest.py:_flush",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ingest.py:chunk_pdf",
        "function:oil_gas_analyst/ingest.py:chunk_pages",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ingest.py:_flush",
        "class:oil_gas_analyst/types.py:Chunk",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ouroboros.py:complete",
        "function:oil_gas_analyst/ouroboros.py:_request",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ouroboros.py:complete",
        "function:oil_gas_analyst/ouroboros.py:_answer_text",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ouroboros.py:complete",
        "function:oil_gas_analyst/ouroboros.py:_citations_from_text",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ouroboros.py:complete",
        "class:oil_gas_analyst/types.py:LoopResult",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ouroboros.py:complete",
        "class:oil_gas_analyst/types.py:LoopError",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/ouroboros.py:_citations_from_text",
        "class:oil_gas_analyst/types.py:Citation",
        "calls",
        0.8,
    ),
    e(
        "class:oil_gas_analyst/ouroboros.py:OuroborosLoop",
        "class:oil_gas_analyst/types.py:AnalystLoop",
        "implements",
        0.9,
    ),
]

nodes2 = [
    n(
        id="file:oil_gas_analyst/retrieve.py",
        type="file",
        name="retrieve.py",
        filePath="oil_gas_analyst/retrieve.py",
        summary="Chroma report index: OpenAI-compatible embeddings, ingest job planning, fingerprint/manifest sync, and retrieve_for_tool for Ouroboros skills.",
        tags=["retriever", "chroma", "embeddings", "ingest", "rag"],
        complexity="complex",
        languageNotes="Talks to an OpenAI-compatible embeddings HTTP API; Chroma persists locally.",
    ),
    n(
        id="class:oil_gas_analyst/retrieve.py:OpenAICompatibleEmbeddingFunction",
        type="class",
        name="OpenAICompatibleEmbeddingFunction",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[60, 140],
        summary="Chroma embedding function that batches texts to an OpenAI-compatible /embeddings endpoint, with optional E5 prefixes and IPv4 preference.",
        tags=["embeddings", "http-client", "chroma"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:_request_headers",
        type="function",
        name="_request_headers",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[83, 95],
        summary="Builds Authorization and JSON headers for the embeddings API, omitting Bearer when the key is empty.",
        tags=["embeddings", "http-client", "auth"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:_embed_batch",
        type="function",
        name="_embed_batch",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[109, 135],
        summary="POSTs one embedding batch and returns vectors in input order, raising RuntimeError on HTTP or shape errors.",
        tags=["embeddings", "http-client", "batch"],
        complexity="moderate",
    ),
    n(
        id="class:oil_gas_analyst/retrieve.py:ChromaRetriever",
        type="class",
        name="ChromaRetriever",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[237, 372],
        summary="Persistent Chroma collection wrapper: fingerprint/manifest, prefix deletes, chunk indexing, and similarity retrieve mapped to Chunk.",
        tags=["retriever", "chroma", "rag"],
        complexity="complex",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:index_chunks",
        type="function",
        name="index_chunks",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[315, 344],
        summary="Upserts Chunk texts and metadata into Chroma under a document-id prefix.",
        tags=["chroma", "ingest", "indexing"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:retrieve",
        type="function",
        name="retrieve",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[345, 372],
        summary="Queries the collection for the question and reconstructs Chunk objects from stored metadata.",
        tags=["retriever", "rag", "chroma"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:_prefer_ipv4",
        type="function",
        name="_prefer_ipv4",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[38, 57],
        summary="Rewrites an embeddings base URL hostname to a resolved IPv4 address to avoid IPv6 connection issues.",
        tags=["networking", "embeddings", "utility"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:make_embedding_function",
        type="function",
        name="make_embedding_function",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[162, 184],
        summary="Reads embedding env vars and returns OpenAICompatibleEmbeddingFunction, failing loudly when no API key is set.",
        tags=["factory", "embeddings", "config"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:drop_redundant_excerpts",
        type="function",
        name="drop_redundant_excerpts",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[193, 218],
        summary="Drops sample excerpt PDFs when a full report for the same agency is already listed in ingest config.",
        tags=["ingest", "corpus", "deduplication"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:_chunk_from_meta",
        type="function",
        name="_chunk_from_meta",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[221, 234],
        summary="Rebuilds a Chunk dataclass from Chroma document text and metadata fields.",
        tags=["data-model", "retriever", "deserialization"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:_date_from_name",
        type="function",
        name="_date_from_name",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[375, 398],
        summary="Parses a report date from a PDF filename using ISO-like and month-name patterns.",
        tags=["parsing", "ingest", "utility"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:_url_for_agency",
        type="function",
        name="_url_for_agency",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[412, 421],
        summary="Resolves a canonical agency URL from explicit metadata or ingest-config agency_urls.",
        tags=["ingest", "citations", "utility"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:iter_ingest_jobs",
        type="function",
        name="iter_ingest_jobs",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[431, 508],
        summary="Yields ingest jobs for sample and full-report PDFs, resolving paths, agencies, dates, and skipping redundant excerpts.",
        tags=["ingest", "corpus", "generator"],
        complexity="complex",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:corpus_fingerprint",
        type="function",
        name="corpus_fingerprint",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[536, 551],
        summary="Hashes the corpus manifest (paths, sizes, embedding model) so ensure_index can skip unchanged indexes.",
        tags=["ingest", "cache", "fingerprint"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:plan_corpus_index",
        type="function",
        name="plan_corpus_index",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[554, 610],
        summary="Compares stored vs current corpus fingerprint/manifest and returns an IndexPlan (skip, sync new PDFs, or full rebuild).",
        tags=["ingest", "planning", "chroma"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:ingest_jobs",
        type="function",
        name="ingest_jobs",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[613, 632],
        summary="Chunks each job PDF and indexes the resulting Chunks on the retriever, returning total chunk count.",
        tags=["ingest", "chunking", "indexing"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:ensure_index",
        type="function",
        name="ensure_index",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[635, 693],
        summary="Plans corpus indexing, optionally resets/deletes prefixes, runs ingest_jobs, and writes the new fingerprint and manifest.",
        tags=["ingest", "chroma", "entry-point"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:ingest_samples_and_reports",
        type="function",
        name="ingest_samples_and_reports",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[696, 717],
        summary="Always rebuilds the index from current ingest jobs (used when force or empty collection requires a full pass).",
        tags=["ingest", "chroma", "indexing"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:_default_retriever",
        type="function",
        name="_default_retriever",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[723, 735],
        summary="Builds a default ChromaRetriever from env paths and runs ensure_index for retrieve_for_tool.",
        tags=["factory", "retriever", "ingest"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/retrieve.py:retrieve_for_tool",
        type="function",
        name="retrieve_for_tool",
        filePath="oil_gas_analyst/retrieve.py",
        lineRange=[739, 759],
        summary="Ouroboros retrieve skill: searches the report index and formats hits with report_citation markdown.",
        tags=["rag", "tool", "ouroboros"],
        complexity="moderate",
    ),
    n(
        id="file:oil_gas_analyst/settings.py",
        type="file",
        name="settings.py",
        filePath="oil_gas_analyst/settings.py",
        summary="Environment-driven model slots, API-key gates, LangSmith maybe_traceable wrapper, and Ouroboros URL/process env for Docker vs local.",
        tags=["configuration", "environment", "ouroboros", "llm"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/settings.py:require_deepseek_key",
        type="function",
        name="require_deepseek_key",
        filePath="oil_gas_analyst/settings.py",
        lineRange=[25, 37],
        summary="Returns the DeepSeek/OpenAI-compatible API key or raises RuntimeError if unset (OpenRouter is not a silent fallback).",
        tags=["validation", "auth", "configuration"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/settings.py:require_embedding_api_key",
        type="function",
        name="require_embedding_api_key",
        filePath="oil_gas_analyst/settings.py",
        lineRange=[40, 52],
        summary="Requires EMBEDDING_API_KEY or OPENROUTER_API_KEY for the embeddings HTTP API.",
        tags=["validation", "auth", "embeddings"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/settings.py:maybe_traceable",
        type="function",
        name="maybe_traceable",
        filePath="oil_gas_analyst/settings.py",
        lineRange=[65, 79],
        summary="Returns langsmith.traceable when tracing is configured, otherwise a no-op decorator so run_turn stays callable.",
        tags=["observability", "decorator", "langsmith"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/settings.py:normalize_chat_model",
        type="function",
        name="normalize_chat_model",
        filePath="oil_gas_analyst/settings.py",
        lineRange=[82, 95],
        summary="Normalizes chat model ids to OpenAI-compatible prefixes expected by the Ouroboros/DeepSeek stack.",
        tags=["llm", "configuration", "normalization"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/settings.py:resolve_model_slots",
        type="function",
        name="resolve_model_slots",
        filePath="oil_gas_analyst/settings.py",
        lineRange=[98, 123],
        summary="Builds ModelSlots from env (main/heavy/light/eval/skill_review) with DeepSeek-flash defaults and no vendor fallback list.",
        tags=["llm", "configuration", "factory"],
        complexity="moderate",
    ),
    n(
        id="function:oil_gas_analyst/settings.py:resolve_ouroboros_url",
        type="function",
        name="resolve_ouroboros_url",
        filePath="oil_gas_analyst/settings.py",
        lineRange=[135, 148],
        summary="Resolves OUROBOROS_URL for host vs Docker (localhost vs compose service, rewriting loopback inside containers).",
        tags=["ouroboros", "docker", "configuration"],
        complexity="simple",
    ),
    n(
        id="function:oil_gas_analyst/settings.py:ouroboros_process_env",
        type="function",
        name="ouroboros_process_env",
        filePath="oil_gas_analyst/settings.py",
        lineRange=[151, 175],
        summary="Environment mapping for the Ouroboros subprocess: API base, model slots, light mode, and thinking-off flags.",
        tags=["ouroboros", "configuration", "process"],
        complexity="moderate",
    ),
]

ti = [
    (
        "test_heading_split_assigns_world_oil_demand",
        4,
        32,
        "Checks MOMR-style heading splits assign World oil demand chunks from synthetic pages.",
    ),
    (
        "test_sample_momr_pdf_yields_demand_chunk",
        35,
        46,
        "Chunks the sample MOMR PDF and asserts a demand-related heading chunk exists.",
    ),
    (
        "test_sample_cbr_pdf_keeps_oil_mention_and_bulletin_heading",
        49,
        67,
        "Chunks the CBR sample PDF and keeps oil mentions under bulletin headings.",
    ),
    (
        "test_cbr_heading_split_assigns_oil_section",
        70,
        89,
        "Synthetic CBR pages split so the oil section is assigned to the correct heading.",
    ),
    (
        "test_drop_redundant_excerpts_skips_steo_excerpt_when_full_listed",
        92,
        120,
        "Asserts STEO excerpt samples are dropped when a full STEO report is listed.",
    ),
    (
        "test_drop_redundant_excerpts_keeps_excerpt_without_full",
        123,
        137,
        "Keeps an excerpt sample when no matching full report is configured.",
    ),
    (
        "test_corpus_fingerprint_omits_steo_excerpt_when_full_exists",
        140,
        152,
        "Fingerprint/job listing omits the STEO excerpt when the full PDF exists.",
    ),
    (
        "test_ensure_index_rebuilds_stale_volume_then_skips",
        155,
        205,
        "Fake retriever: stale fingerprint triggers ingest, a matching fingerprint then skips.",
    ),
    (
        "test_ensure_index_force_rebuilds_matching_fingerprint",
        208,
        254,
        "force=True rebuilds even when the stored fingerprint already matches.",
    ),
    (
        "test_plan_corpus_index_skips_when_fingerprint_matches",
        257,
        284,
        "plan_corpus_index returns skip when on-disk fingerprint matches the corpus.",
    ),
    (
        "test_plan_corpus_index_syncs_only_new_pdf",
        287,
        320,
        "Adding a new PDF yields a sync plan for only that file.",
    ),
    (
        "test_make_embedding_function_uses_openrouter_nemotron",
        329,
        346,
        "With OpenRouter key set, make_embedding_function uses the Nemotron embedding model.",
    ),
    (
        "test_make_embedding_function_raises_without_key",
        349,
        359,
        "make_embedding_function raises when embedding and OpenRouter keys are unset.",
    ),
    (
        "test_missing_sample_report_breaks_ingest",
        362,
        382,
        "iter_ingest_jobs raises when a configured sample PDF path is missing.",
    ),
]
nodes2.append(
    n(
        id="file:tests/test_ingest.py",
        type="file",
        name="test_ingest.py",
        filePath="tests/test_ingest.py",
        summary="Pytest coverage for heading chunking, sample PDFs, excerpt dropping, corpus fingerprints, ensure_index planning, and embedding factory.",
        tags=["test", "ingest", "chroma", "embeddings"],
        complexity="complex",
    )
)
for name, a, b, summary in ti:
    nodes2.append(
        n(
            id=f"function:tests/test_ingest.py:{name}",
            type="function",
            name=name,
            filePath="tests/test_ingest.py",
            lineRange=[a, b],
            summary=summary,
            tags=["test", "ingest", "chunking"],
            complexity="moderate" if (b - a + 1) >= 25 else "simple",
        )
    )

to = [
    (
        "test_gateway_turn_returns_task_answer",
        45,
        69,
        "Stubbed HTTP gateway: run_turn returns the task answer text from OuroborosLoop.",
    ),
    (
        "test_gateway_reads_answer_from_outcome_axes",
        72,
        89,
        "Answer is read from nested outcome axes when the top-level text is absent.",
    ),
    (
        "test_gateway_marks_retrieve_when_tool_name_is_in_the_task_record",
        92,
        116,
        "Retrieve tool in the task record sets grounded-report flags on the reply.",
    ),
    (
        "test_gateway_marks_web_when_search_tool_is_in_the_task_record",
        119,
        143,
        "Web search tool in the task record is reflected in the reply text/flags.",
    ),
    (
        "test_gateway_marks_forecast_when_tool_is_in_the_task_record",
        146,
        170,
        "Forecast tool in the task record is marked on the LoopResult/reply.",
    ),
    (
        "test_gateway_retries_while_supervisor_is_starting",
        173,
        192,
        "Gateway retries while the supervisor returns startup/503 responses.",
    ),
]
nodes2.append(
    n(
        id="file:tests/test_ouroboros.py",
        type="file",
        name="test_ouroboros.py",
        filePath="tests/test_ouroboros.py",
        summary="Gateway tests with scripted urllib stubs: answer extraction, retrieve/web/forecast tool flags, and supervisor-start retries.",
        tags=["test", "ouroboros", "http-client"],
        complexity="moderate",
    )
)
nodes2.append(
    n(
        id="class:tests/test_ouroboros.py:_Http",
        type="class",
        name="_Http",
        filePath="tests/test_ouroboros.py",
        lineRange=[12, 28],
        summary="Callable urllib stub that scripts JSON HTTP responses (and optional HTTPError) for OuroborosLoop._request.",
        tags=["test", "stub", "http-client"],
        complexity="simple",
    )
)
nodes2.append(
    n(
        id="class:tests/test_ouroboros.py:_Resp",
        type="class",
        name="_Resp",
        filePath="tests/test_ouroboros.py",
        lineRange=[31, 42],
        summary="Context-manager response stub exposing read() for urlopen patches.",
        tags=["test", "stub", "http-client"],
        complexity="simple",
    )
)
for name, a, b, summary in to:
    nodes2.append(
        n(
            id=f"function:tests/test_ouroboros.py:{name}",
            type="function",
            name=name,
            filePath="tests/test_ouroboros.py",
            lineRange=[a, b],
            summary=summary,
            tags=["test", "ouroboros", "gateway"],
            complexity="moderate",
        )
    )

ts = [
    (
        "test_unset_slots_use_main_deepseek_flash_with_no_vendor_fallback",
        42,
        60,
        "Unset slot env vars default to DeepSeek-flash-style main with empty vendor fallbacks.",
    ),
    (
        "test_env_overrides_heavy_and_eval_only",
        68,
        77,
        "HEAVY and EVAL env vars override only those ModelSlots without changing others.",
    ),
    (
        "test_ouroboros_process_env_pins_light_mode_and_thinking_off",
        80,
        95,
        "ouroboros_process_env pins light mode and disables thinking flags.",
    ),
    (
        "test_local_requirements_do_not_pull_legacy_langgraph_stack",
        98,
        108,
        "requirements.txt does not pull the legacy LangGraph stack.",
    ),
    (
        "test_readme_names_ouroboros_adapter_evolve_off_and_port_8000",
        111,
        123,
        "README names the Ouroboros adapter, evolve-off, and Streamlit port 8000.",
    ),
    (
        "test_compose_publishes_streamlit_only_and_pins_light_mode",
        137,
        164,
        "Compose/Dockerfile pin Streamlit publish and Ouroboros light mode.",
    ),
]
nodes2.append(
    n(
        id="file:tests/test_settings.py",
        type="file",
        name="test_settings.py",
        filePath="tests/test_settings.py",
        summary="Tests API-key gates, model-slot defaults, Ouroboros URL in/out of Docker, process env, and README/compose contracts.",
        tags=["test", "configuration", "ouroboros"],
        complexity="moderate",
    )
)
for name, a, b, summary in ts:
    nodes2.append(
        n(
            id=f"function:tests/test_settings.py:{name}",
            type="function",
            name=name,
            filePath="tests/test_settings.py",
            lineRange=[a, b],
            summary=summary,
            tags=["test", "configuration", "settings"],
            complexity="simple" if (b - a + 1) < 20 else "moderate",
        )
    )

edges2 = []
for src, tgts in {
    "oil_gas_analyst/retrieve.py": [
        "oil_gas_analyst/ingest.py",
        "oil_gas_analyst/settings.py",
        "oil_gas_analyst/types.py",
    ],
    "oil_gas_analyst/settings.py": [],
    "tests/test_ingest.py": ["oil_gas_analyst/ingest.py"],
    "tests/test_ouroboros.py": ["oil_gas_analyst/ouroboros.py", "oil_gas_analyst/turn.py"],
    "tests/test_settings.py": ["oil_gas_analyst/settings.py"],
}.items():
    for t in tgts:
        edges2.append(e(f"file:{src}", f"file:{t}", "imports", 0.7))

ce2 = [
    (
        "file:oil_gas_analyst/retrieve.py",
        "class:oil_gas_analyst/retrieve.py:OpenAICompatibleEmbeddingFunction",
        True,
    ),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:_request_headers", False),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:_embed_batch", False),
    ("file:oil_gas_analyst/retrieve.py", "class:oil_gas_analyst/retrieve.py:ChromaRetriever", True),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:index_chunks", False),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:retrieve", False),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:_prefer_ipv4", True),
    (
        "file:oil_gas_analyst/retrieve.py",
        "function:oil_gas_analyst/retrieve.py:make_embedding_function",
        True,
    ),
    (
        "file:oil_gas_analyst/retrieve.py",
        "function:oil_gas_analyst/retrieve.py:drop_redundant_excerpts",
        True,
    ),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:_chunk_from_meta", True),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:_date_from_name", True),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:_url_for_agency", True),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:iter_ingest_jobs", True),
    (
        "file:oil_gas_analyst/retrieve.py",
        "function:oil_gas_analyst/retrieve.py:corpus_fingerprint",
        True,
    ),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:plan_corpus_index", True),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:ingest_jobs", True),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:ensure_index", True),
    (
        "file:oil_gas_analyst/retrieve.py",
        "function:oil_gas_analyst/retrieve.py:ingest_samples_and_reports",
        True,
    ),
    (
        "file:oil_gas_analyst/retrieve.py",
        "function:oil_gas_analyst/retrieve.py:_default_retriever",
        True,
    ),
    ("file:oil_gas_analyst/retrieve.py", "function:oil_gas_analyst/retrieve.py:retrieve_for_tool", True),
    (
        "file:oil_gas_analyst/settings.py",
        "function:oil_gas_analyst/settings.py:require_deepseek_key",
        True,
    ),
    (
        "file:oil_gas_analyst/settings.py",
        "function:oil_gas_analyst/settings.py:require_embedding_api_key",
        True,
    ),
    ("file:oil_gas_analyst/settings.py", "function:oil_gas_analyst/settings.py:maybe_traceable", True),
    (
        "file:oil_gas_analyst/settings.py",
        "function:oil_gas_analyst/settings.py:normalize_chat_model",
        True,
    ),
    (
        "file:oil_gas_analyst/settings.py",
        "function:oil_gas_analyst/settings.py:resolve_model_slots",
        True,
    ),
    (
        "file:oil_gas_analyst/settings.py",
        "function:oil_gas_analyst/settings.py:resolve_ouroboros_url",
        True,
    ),
    (
        "file:oil_gas_analyst/settings.py",
        "function:oil_gas_analyst/settings.py:ouroboros_process_env",
        True,
    ),
]
for src, tgt, exported in ce2:
    edges2.append(e(src, tgt, "contains", 1.0))
    if exported:
        edges2.append(e(src, tgt, "exports", 0.8))
edges2.append(
    e(
        "class:oil_gas_analyst/retrieve.py:OpenAICompatibleEmbeddingFunction",
        "function:oil_gas_analyst/retrieve.py:_request_headers",
        "contains",
        1.0,
    )
)
edges2.append(
    e(
        "class:oil_gas_analyst/retrieve.py:OpenAICompatibleEmbeddingFunction",
        "function:oil_gas_analyst/retrieve.py:_embed_batch",
        "contains",
        1.0,
    )
)
edges2.append(
    e(
        "class:oil_gas_analyst/retrieve.py:ChromaRetriever",
        "function:oil_gas_analyst/retrieve.py:index_chunks",
        "contains",
        1.0,
    )
)
edges2.append(
    e(
        "class:oil_gas_analyst/retrieve.py:ChromaRetriever",
        "function:oil_gas_analyst/retrieve.py:retrieve",
        "contains",
        1.0,
    )
)

for name, a, b, summary in ti:
    edges2.append(e("file:tests/test_ingest.py", f"function:tests/test_ingest.py:{name}", "contains", 1.0))
    edges2.append(e("file:tests/test_ingest.py", f"function:tests/test_ingest.py:{name}", "exports", 0.8))
edges2.append(e("file:tests/test_ouroboros.py", "class:tests/test_ouroboros.py:_Http", "contains", 1.0))
edges2.append(e("file:tests/test_ouroboros.py", "class:tests/test_ouroboros.py:_Http", "exports", 0.8))
edges2.append(e("file:tests/test_ouroboros.py", "class:tests/test_ouroboros.py:_Resp", "contains", 1.0))
edges2.append(e("file:tests/test_ouroboros.py", "class:tests/test_ouroboros.py:_Resp", "exports", 0.8))
for name, a, b, summary in to:
    edges2.append(
        e("file:tests/test_ouroboros.py", f"function:tests/test_ouroboros.py:{name}", "contains", 1.0)
    )
    edges2.append(
        e("file:tests/test_ouroboros.py", f"function:tests/test_ouroboros.py:{name}", "exports", 0.8)
    )
for name, a, b, summary in ts:
    edges2.append(
        e("file:tests/test_settings.py", f"function:tests/test_settings.py:{name}", "contains", 1.0)
    )
    edges2.append(
        e("file:tests/test_settings.py", f"function:tests/test_settings.py:{name}", "exports", 0.8)
    )

edges2 += [
    e(
        "function:oil_gas_analyst/retrieve.py:make_embedding_function",
        "class:oil_gas_analyst/retrieve.py:OpenAICompatibleEmbeddingFunction",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:_chunk_from_meta",
        "class:oil_gas_analyst/types.py:Chunk",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:iter_ingest_jobs",
        "function:oil_gas_analyst/retrieve.py:drop_redundant_excerpts",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:iter_ingest_jobs",
        "function:oil_gas_analyst/retrieve.py:_date_from_name",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:iter_ingest_jobs",
        "function:oil_gas_analyst/retrieve.py:_url_for_agency",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:plan_corpus_index",
        "function:oil_gas_analyst/retrieve.py:corpus_fingerprint",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:ensure_index",
        "function:oil_gas_analyst/retrieve.py:plan_corpus_index",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:ensure_index",
        "function:oil_gas_analyst/retrieve.py:ingest_jobs",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:ensure_index",
        "function:oil_gas_analyst/retrieve.py:ingest_samples_and_reports",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:_default_retriever",
        "function:oil_gas_analyst/retrieve.py:make_embedding_function",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:_default_retriever",
        "class:oil_gas_analyst/retrieve.py:ChromaRetriever",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:_default_retriever",
        "function:oil_gas_analyst/retrieve.py:ensure_index",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:retrieve_for_tool",
        "function:oil_gas_analyst/retrieve.py:_default_retriever",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:retrieve_for_tool",
        "function:oil_gas_analyst/turn.py:report_citation",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/settings.py:resolve_model_slots",
        "function:oil_gas_analyst/settings.py:normalize_chat_model",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/settings.py:ouroboros_process_env",
        "function:oil_gas_analyst/settings.py:require_deepseek_key",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/settings.py:ouroboros_process_env",
        "function:oil_gas_analyst/settings.py:resolve_model_slots",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_drop_redundant_excerpts_skips_steo_excerpt_when_full_listed",
        "function:oil_gas_analyst/retrieve.py:drop_redundant_excerpts",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_drop_redundant_excerpts_keeps_excerpt_without_full",
        "function:oil_gas_analyst/retrieve.py:drop_redundant_excerpts",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_corpus_fingerprint_omits_steo_excerpt_when_full_exists",
        "function:oil_gas_analyst/retrieve.py:corpus_fingerprint",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_corpus_fingerprint_omits_steo_excerpt_when_full_exists",
        "function:oil_gas_analyst/retrieve.py:iter_ingest_jobs",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_ensure_index_rebuilds_stale_volume_then_skips",
        "function:oil_gas_analyst/retrieve.py:ensure_index",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_ensure_index_force_rebuilds_matching_fingerprint",
        "function:oil_gas_analyst/retrieve.py:ensure_index",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_plan_corpus_index_skips_when_fingerprint_matches",
        "function:oil_gas_analyst/retrieve.py:plan_corpus_index",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_plan_corpus_index_syncs_only_new_pdf",
        "function:oil_gas_analyst/retrieve.py:plan_corpus_index",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_make_embedding_function_uses_openrouter_nemotron",
        "function:oil_gas_analyst/retrieve.py:make_embedding_function",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_make_embedding_function_raises_without_key",
        "function:oil_gas_analyst/retrieve.py:make_embedding_function",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ingest.py:test_missing_sample_report_breaks_ingest",
        "function:oil_gas_analyst/retrieve.py:iter_ingest_jobs",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ouroboros.py:test_gateway_turn_returns_task_answer",
        "function:oil_gas_analyst/turn.py:run_turn",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ouroboros.py:test_gateway_reads_answer_from_outcome_axes",
        "function:oil_gas_analyst/turn.py:run_turn",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ouroboros.py:test_gateway_marks_retrieve_when_tool_name_is_in_the_task_record",
        "function:oil_gas_analyst/turn.py:run_turn",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ouroboros.py:test_gateway_marks_retrieve_when_tool_name_is_in_the_task_record",
        "function:oil_gas_analyst/turn.py:has_grounded_report",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ouroboros.py:test_gateway_marks_web_when_search_tool_is_in_the_task_record",
        "function:oil_gas_analyst/turn.py:run_turn",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ouroboros.py:test_gateway_marks_forecast_when_tool_is_in_the_task_record",
        "function:oil_gas_analyst/turn.py:run_turn",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_ouroboros.py:test_gateway_retries_while_supervisor_is_starting",
        "function:oil_gas_analyst/turn.py:run_turn",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_settings.py:test_unset_slots_use_main_deepseek_flash_with_no_vendor_fallback",
        "function:oil_gas_analyst/settings.py:resolve_model_slots",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_settings.py:test_env_overrides_heavy_and_eval_only",
        "function:oil_gas_analyst/settings.py:resolve_model_slots",
        "calls",
        0.8,
    ),
    e(
        "function:tests/test_settings.py:test_ouroboros_process_env_pins_light_mode_and_thinking_off",
        "function:oil_gas_analyst/settings.py:ouroboros_process_env",
        "calls",
        0.8,
    ),
    e("file:tests/test_ingest.py", "file:oil_gas_analyst/ingest.py", "tested_by", 0.5),
    e("file:tests/test_ingest.py", "file:oil_gas_analyst/retrieve.py", "tested_by", 0.5),
    e("file:tests/test_ouroboros.py", "file:oil_gas_analyst/ouroboros.py", "tested_by", 0.5),
    e("file:tests/test_settings.py", "file:oil_gas_analyst/settings.py", "tested_by", 0.5),
    e(
        "class:oil_gas_analyst/retrieve.py:ChromaRetriever",
        "class:oil_gas_analyst/types.py:Retriever",
        "implements",
        0.9,
    ),
    e(
        "class:oil_gas_analyst/retrieve.py:OpenAICompatibleEmbeddingFunction",
        "function:oil_gas_analyst/retrieve.py:_prefer_ipv4",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:_embed_batch",
        "function:oil_gas_analyst/retrieve.py:_request_headers",
        "calls",
        0.8,
    ),
    e(
        "function:oil_gas_analyst/retrieve.py:retrieve",
        "function:oil_gas_analyst/retrieve.py:_chunk_from_meta",
        "calls",
        0.8,
    ),
]

print("nodes1", len(nodes1), "nodes2", len(nodes2), "total", len(nodes1) + len(nodes2))
print("edges1", len(edges1), "edges2", len(edges2), "total", len(edges1) + len(edges2))
ids1 = [x["id"] for x in nodes1]
ids2 = [x["id"] for x in nodes2]
assert len(ids1) == len(set(ids1))
assert len(ids2) == len(set(ids2))
assert not set(ids1) & set(ids2)

batch_import = {
    "oil_gas_analyst/__main__.py": [
        "oil_gas_analyst/deps.py",
        "oil_gas_analyst/retrieve.py",
    ],
    "oil_gas_analyst/corpus_strip.py": [
        "oil_gas_analyst/ingest.py",
        "oil_gas_analyst/retrieve.py",
    ],
    "oil_gas_analyst/deps.py": [
        "oil_gas_analyst/ingest.py",
        "oil_gas_analyst/ouroboros.py",
        "oil_gas_analyst/settings.py",
    ],
    "oil_gas_analyst/ingest.py": ["oil_gas_analyst/types.py"],
    "oil_gas_analyst/ouroboros.py": [
        "oil_gas_analyst/settings.py",
        "oil_gas_analyst/types.py",
    ],
    "oil_gas_analyst/retrieve.py": [
        "oil_gas_analyst/ingest.py",
        "oil_gas_analyst/settings.py",
        "oil_gas_analyst/types.py",
    ],
    "oil_gas_analyst/settings.py": [],
    "tests/test_ingest.py": ["oil_gas_analyst/ingest.py"],
    "tests/test_ouroboros.py": ["oil_gas_analyst/ouroboros.py", "oil_gas_analyst/turn.py"],
    "tests/test_settings.py": ["oil_gas_analyst/settings.py"],
}
import_paths = set()
for k, vs in batch_import.items():
    import_paths.add(k)
    import_paths.update(vs)
neighbor_files = {
    "oil_gas_analyst/dashboard.py",
    "tests/test_dashboard_layout.py",
    "oil_gas_analyst/app.py",
    "oil_gas_analyst/chat_ui.py",
    "oil_gas_analyst/types.py",
    "oil_gas_analyst/consensus_price.py",
    "oil_gas_analyst/render.py",
    "oil_gas_analyst/turn.py",
    "oil_gas_analyst/forecast.py",
    "oil_gas_analyst/web.py",
}
neighbor_symbols = {
    ("oil_gas_analyst/types.py", s)
    for s in (
        "Chunk WebHit MethodForecast MethodPathForecast ForecastPlotPayload "
        "ForecastResult Citation LoopResult LoopError AnalystLoop Reply "
        "CompetenceClassifier Retriever ChunkDropper WebSearch ForecastModule Composer"
    ).split()
} | {
    ("oil_gas_analyst/turn.py", s)
    for s in (
        "drop_listing footer_flags _agency_of _agency_urls _report_url report_citation "
        "web_citation forecast_citations has_grounded_report _trim_memory_content "
        "format_chat_memory prompt_with_chat_memory build_turn_prompt _safety_net "
        "run_turn markdown_cite apply_citation_links"
    ).split()
}


def validate(part_nodes, part_edges, label):
    ids = {x["id"] for x in part_nodes}
    bad = []
    for ed in part_edges:
        for end in (ed["source"], ed["target"]):
            if end in ids:
                continue
            if end.startswith("file:"):
                p = end[5:]
                if p in import_paths or p in neighbor_files:
                    continue
                bad.append((end, "file not in import/neighbor"))
            elif end.startswith("function:") or end.startswith("class:"):
                rest = end.split(":", 1)[1]
                path, _, sym = rest.rpartition(":")
                if (path, sym) in neighbor_symbols:
                    continue
                bad.append((end, "symbol not in neighborMap and not in this part"))
            else:
                bad.append((end, "unknown"))
    print(label, "bad", len(bad))
    for b in bad[:30]:
        print(" ", b)
    return bad


for nodes in (nodes1, nodes2):
    for nd in nodes:
        assert 3 <= len(nd["tags"]) <= 5, (nd["id"], nd["tags"])
        assert nd["summary"]
        assert nd["complexity"] in ("simple", "moderate", "complex")

import_edge_count = sum(1 for x in edges1 + edges2 if x["type"] == "imports")
expected_imports = sum(len(v) for v in batch_import.values())
print("imports", import_edge_count, "expected", expected_imports)
assert import_edge_count == expected_imports

bad1 = validate(nodes1, edges1, "part1")
bad2 = validate(nodes2, edges2, "part2")

out = Path("/Users/semenoffalex/Cursor/sber/.understand-anything/intermediate")
(out / "batch-3-part-1.json").write_text(json.dumps({"nodes": nodes1, "edges": edges1}, indent=2) + "\n")
(out / "batch-3-part-2.json").write_text(json.dumps({"nodes": nodes2, "edges": edges2}, indent=2) + "\n")
print("wrote ok")
if bad1 or bad2:
    raise SystemExit(1)
