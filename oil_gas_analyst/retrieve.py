from __future__ import annotations

import hashlib
import json
import os
import re
import socket
from dataclasses import dataclass
from pathlib import Path
import urllib.error
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen
from typing import Literal

from oil_gas_analyst.ingest import chunk_pdf, e5_token_count, load_ingest_config
from oil_gas_analyst.settings import maybe_traceable
from oil_gas_analyst.types import Chunk

_PASSAGE = "passage: "
_QUERY = "query: "
_EMBED_BATCH = 32
_INDEX_SCHEMA = "openrouter-nemotron-embed-v1"
_FINGERPRINT_NAME = "corpus_fingerprint.txt"
_MANIFEST_NAME = "corpus_manifest.json"
DEFAULT_EMBEDDING_BASE = "https://openrouter.ai/api/v1"
DEFAULT_EMBEDDING_MODEL = "nvidia/nemotron-3-embed-1b:free"


@dataclass(frozen=True)
class IndexPlan:
    action: Literal["skip", "rebuild", "sync"]
    reason: str
    manifest: dict
    jobs: tuple[dict, ...]
    delete_prefixes: tuple[str, ...]


def _prefer_ipv4(url: str) -> str:
    """Rewrite Docker DNS names to IPv4. Do not rewrite public HTTPS hosts (breaks TLS)."""
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
        return url
    if host not in {"host.docker.internal", "localhost"} and not host.endswith(".internal"):
        return url
    try:
        ipv4 = socket.getaddrinfo(host, parsed.port or 80, socket.AF_INET)[0][4][0]
    except OSError:
        return url
    if ipv4 == host:
        return url
    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth += f":{parsed.password}"
        auth += "@"
    port = f":{parsed.port}" if parsed.port else ""
    return urlunparse(parsed._replace(netloc=f"{auth}{ipv4}{port}"))


class OpenAICompatibleEmbeddingFunction:
    """OpenAI-compatible /v1/embeddings (OpenRouter Nemotron by default). No local Torch."""

    def __init__(
        self,
        base_url: str,
        model_name: str,
        api_key: str,
        timeout: float = 60,
        *,
        e5_prefixes: bool = False,
        nemotron_input_type: bool = False,
    ):
        base = base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        self._url = _prefer_ipv4(f"{base}/embeddings")
        self._model = model_name
        self._api_key = api_key
        self._timeout = timeout
        self._e5_prefixes = e5_prefixes
        self._nemotron_input_type = nemotron_input_type

    def _request_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "User-Agent": "oil-gas-analyst/0.1",
        }
        if "openrouter.ai" in self._url:
            headers["HTTP-Referer"] = os.environ.get(
                "OPENROUTER_HTTP_REFERER",
                "https://github.com/semenoffalex/agent_oil_analyst",
            )
            headers["X-Title"] = os.environ.get("OPENROUTER_APP_TITLE", "Oil Gas Analyst")
        return headers

    def _prefixed(self, texts: list[str], kind: str) -> list[str]:
        if not self._e5_prefixes:
            return texts
        prefix = _QUERY if kind == "query" else _PASSAGE
        return [prefix + t for t in texts]

    def _embed(self, texts: list[str], *, kind: str) -> list[list[float]]:
        prepared = self._prefixed(texts, kind)
        out: list[list[float]] = []
        for i in range(0, len(prepared), _EMBED_BATCH):
            out.extend(self._embed_batch(prepared[i : i + _EMBED_BATCH], kind=kind))
        return out

    def _embed_batch(self, texts: list[str], *, kind: str) -> list[list[float]]:
        body: dict[str, object] = {"model": self._model, "input": texts}
        if self._nemotron_input_type:
            body["input_type"] = "query" if kind == "query" else "passage"
        payload = json.dumps(body).encode("utf-8")
        req = Request(
            self._url,
            data=payload,
            headers=self._request_headers(),
            method="POST",
        )
        try:
            with urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Embedding HTTP {exc.code}: {body or exc}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"cannot reach embedding API at {self._url}: {exc}") from exc
        rows = sorted(data.get("data") or [], key=lambda row: int(row.get("index", 0)))
        vecs = [row["embedding"] for row in rows]
        if len(vecs) != len(texts):
            raise RuntimeError(
                f"Embedding endpoint returned {len(vecs)} vectors for {len(texts)} inputs"
            )
        return vecs

    def __call__(self, input):
        return self._embed(list(input), kind="passage")

    def embed_query(self, text: str) -> list[float]:
        return self._embed([text], kind="query")[0]


def embedding_model_name() -> str:
    return os.environ.get("EMBEDDING_MODEL", "").strip() or DEFAULT_EMBEDDING_MODEL


def embedding_base_url() -> str:
    return (
        os.environ.get("EMBEDDING_BASE_URL", "").strip()
        or os.environ.get("OPENROUTER_BASE_URL", "").strip()
        or DEFAULT_EMBEDDING_BASE
    )


def embedding_api_key() -> str:
    return (
        os.environ.get("EMBEDDING_API_KEY", "").strip()
        or os.environ.get("OPENROUTER_API_KEY", "").strip()
    )


def make_embedding_function():
    """Remote embeddings only (ADR 0025). Dead HTTP fails loudly; no local Torch."""

    key = embedding_api_key()
    if not key:
        raise RuntimeError(
            "EMBEDDING_API_KEY or OPENROUTER_API_KEY is required for remote embeddings."
        )
    base = embedding_base_url()
    model = embedding_model_name()
    e5_prefixes = os.environ.get("EMBEDDING_USE_E5_PREFIXES", "").strip().lower() in {
        "1",
        "true",
        "yes",
    } or "e5" in model.lower()
    nemotron_input_type = "nemotron" in model.lower() and "embed" in model.lower()
    return OpenAICompatibleEmbeddingFunction(
        base,
        model,
        api_key=key,
        e5_prefixes=e5_prefixes,
        nemotron_input_type=nemotron_input_type,
    )


def _meta_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


def drop_redundant_excerpts(samples: list[dict]) -> list[dict]:
    """Skip a Sample excerpt when a full Report of the same agency and date is listed.

    Args:
        samples: Ingest config entries with ``agency``, ``date``, and ``excerpt``.

    Returns:
        Filtered list; e.g. STEO excerpt drops when August 2026 full STEO is present.

    Example:
        >>> drop_redundant_excerpts([excerpt_steo, full_steo])
        [full_steo]
    """
    full_keys = {
        (str(sample.get("agency") or ""), str(sample.get("date") or ""))
        for sample in samples
        if not bool(sample.get("excerpt", False))
    }
    kept: list[dict] = []
    for sample in samples:
        excerpt = bool(sample.get("excerpt", False))
        key = (str(sample.get("agency") or ""), str(sample.get("date") or ""))
        if excerpt and key in full_keys:
            continue
        kept.append(sample)
    return kept


def _chunk_from_meta(text: str, meta: dict) -> Chunk:
    ps = meta.get("page_start")
    pe = meta.get("page_end")
    return Chunk(
        text=text,
        title=str(meta.get("title") or ""),
        date=meta.get("date") or None,
        page_start=int(ps) if ps not in (None, "", "None") else None,
        page_end=int(pe) if pe not in (None, "", "None") else None,
        heading=str(meta.get("heading") or "(untitled)"),
        excerpt=_meta_bool(meta.get("excerpt", False)),
        agency=str(meta.get("agency") or ""),
        url=str(meta.get("url") or "").strip() or None,
    )


class ChromaRetriever:
    """E5 + Chroma retrieval over persisted Report chunks."""

    def __init__(self, persist_path: str, embedding, k: int = 10):
        """Open or create the ``reports`` collection on disk.

        Args:
            persist_path: Chroma persistence directory (``CHROMA_PATH``).
            embedding: Callable with ``embed_query`` and batch ``__call__``.
            k: Default ``retrieve`` pool size when ``k`` is not passed.

        Example:
            >>> retriever = ChromaRetriever("data/chroma", embedding, k=10)
            >>> retriever.is_empty()
            True
        """
        import chromadb

        self._k = k
        self._embedding = embedding
        self._persist_path = persist_path
        self._client = chromadb.PersistentClient(path=persist_path)
        self._col = self._client.get_or_create_collection(
            name="reports",
            metadata={"hnsw:space": "cosine"},
        )

    def is_empty(self) -> bool:
        """Return True when the collection has no indexed chunks."""
        return self._col.count() == 0

    def reset(self) -> None:
        """Delete and recreate the ``reports`` collection (full re-index)."""
        self._client.delete_collection("reports")
        self._col = self._client.get_or_create_collection(
            name="reports",
            metadata={"hnsw:space": "cosine"},
        )

    def stored_fingerprint(self) -> str | None:
        """Read the last ``corpus_fingerprint`` written after ingest, if any."""
        path = Path(self._persist_path) / _FINGERPRINT_NAME
        if not path.is_file():
            return None
        return path.read_text(encoding="utf-8").strip() or None

    def write_fingerprint(self, fp: str) -> None:
        """Persist ``fp`` beside the Chroma files for ``ensure_index`` checks."""
        path = Path(self._persist_path)
        path.mkdir(parents=True, exist_ok=True)
        (path / _FINGERPRINT_NAME).write_text(fp + "\n", encoding="utf-8")

    def stored_manifest(self) -> dict | None:
        path = Path(self._persist_path) / _MANIFEST_NAME
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def write_manifest(self, manifest: dict) -> None:
        path = Path(self._persist_path)
        path.mkdir(parents=True, exist_ok=True)
        (path / _MANIFEST_NAME).write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def delete_by_id_prefix(self, id_prefix: str) -> int:
        """Remove all chunk ids that start with ``{id_prefix}-``."""
        batch = self._col.get(include=[])
        ids = batch.get("ids") or []
        to_delete = [chunk_id for chunk_id in ids if chunk_id.startswith(f"{id_prefix}-")]
        if to_delete:
            self._col.delete(ids=to_delete)
        return len(to_delete)

    def index_chunks(self, chunks: list[Chunk], id_prefix: str) -> None:
        """Embed and upsert chunks with Report metadata.

        Args:
            chunks: Heading-bounded pieces from ``chunk_pdf``.
            id_prefix: Stable id stem, e.g. ``sample-0`` or ``full-1``.

        Example:
            >>> retriever.index_chunks(chunks, id_prefix="sample-0")
        """
        if not chunks:
            return
        ids = [f"{id_prefix}-{i}" for i in range(len(chunks))]
        docs = [c.text for c in chunks]
        embeddings = self._embedding(docs)
        metas = [
            {
                "title": c.title,
                "date": c.date or "",
                "page_start": "" if c.page_start is None else str(c.page_start),
                "page_end": "" if c.page_end is None else str(c.page_end),
                "heading": c.heading,
                "excerpt": str(c.excerpt),
                "agency": c.agency or "",
                "url": c.url or "",
            }
            for c in chunks
        ]
        self._col.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)

    def retrieve(self, question: str, k: int = 10) -> list[Chunk]:
        """Vector-search Reports and return up to ``k`` chunks (no heading-rank).

        Args:
            question: User question.
            k: Number of chunks to return; defaults to constructor ``k``.

        Returns:
            Ranked chunks with title, date, page, heading, and excerpt metadata.

        Example:
            >>> chunks = retriever.retrieve("OPEC 2026 oil demand", k=10)
            >>> len(chunks) <= 10
            True
        """
        k = k or self._k
        total = self._col.count()
        if total == 0:
            return []
        pool = min(max(k, 1), total)
        q = self._embedding.embed_query(question)
        got = self._col.query(query_embeddings=[q], n_results=pool)
        docs = (got.get("documents") or [[]])[0]
        metas = (got.get("metadatas") or [[]])[0]
        out: list[Chunk] = []
        for text, meta in zip(docs, metas):
            out.append(_chunk_from_meta(text, meta or {}))
        return out


def _date_from_name(name: str) -> str | None:
    stem = Path(name).stem.lower()
    m = re.search(r"(20\d{2})[-_.](\d{2})", stem)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    months = {
        "january": "01",
        "february": "02",
        "march": "03",
        "april": "04",
        "may": "05",
        "june": "06",
        "july": "07",
        "august": "08",
        "september": "09",
        "october": "10",
        "november": "11",
        "december": "12",
    }
    for month, num in months.items():
        m = re.search(rf"{month}[-_ ]?(20\d{{2}})", stem)
        if m:
            return f"{m.group(1)}-{num}"
    return None


def _agency_from_name(name: str, default: str = "OPEC") -> str:
    n = name.lower()
    if "cbr" in n:
        return "CBR"
    if "steo" in n or "eia" in n:
        return "EIA"
    if "momr" in n or "opec" in n:
        return "OPEC"
    return default


def _url_for_agency(agency: str, cfg: dict, explicit: str | None = None) -> str | None:
    if explicit and str(explicit).strip():
        return str(explicit).strip()
    mapped = (cfg.get("agency_urls") or {}).get(agency)
    if mapped:
        return str(mapped).strip()
    for item in cfg.get("full_reports") or []:
        if item.get("agency") == agency and item.get("url"):
            return str(item["url"]).strip()
    return None


def _resolve_sample_path(sample: dict, samples_dir: Path) -> Path:
    path = Path(sample["path"])
    if path.exists():
        return path
    return samples_dir / path.name


def iter_ingest_jobs(samples_dir: Path, reports_dir: Path, cfg: dict | None = None) -> list[dict]:
    """List PDF ingest jobs from config, extra samples, and full reports.

    Args:
        samples_dir: Directory with committed Sample Reports.
        reports_dir: Directory with downloaded Full Reports.
        cfg: Ingest config; defaults to ``config/ingest.yaml``.

    Returns:
        Job dicts with ``path``, ``excerpt``, ``agency``, ``date``, ``title``,
        ``url``, and ``id_prefix`` for Chroma upsert keys.

    Example:
        >>> jobs = iter_ingest_jobs(Path("data/samples"), Path("data/reports"))
        >>> any(j["path"].name == "steo_full.pdf" for j in jobs)
        True
        >>> any(j["path"].name == "eia-steo-excerpt.pdf" for j in jobs)
        False
    """
    cfg = cfg or load_ingest_config()
    jobs: list[dict] = []
    seen: set[Path] = set()
    listed = list(cfg.get("samples") or [])
    samples = drop_redundant_excerpts(listed)
    for sample in listed:
        path = _resolve_sample_path(sample, samples_dir)
        if path.exists():
            seen.add(path.resolve())
    for i, sample in enumerate(samples):
        path = _resolve_sample_path(sample, samples_dir)
        if not path.exists():
            raise FileNotFoundError(f"Sample Report missing: {sample['path']}")
        seen.add(path.resolve())
        agency = sample.get("agency") or _agency_from_name(path.name)
        jobs.append(
            {
                "path": path,
                "excerpt": bool(sample.get("excerpt", True)),
                "agency": agency,
                "date": sample.get("date") or _date_from_name(path.name),
                "title": sample.get("title", path.stem),
                "url": sample.get("url"),
                "id_prefix": f"sample-{i}",
            }
        )
    extra = 0
    if samples_dir.exists():
        for pdf in sorted(samples_dir.glob("*.pdf")):
            if pdf.resolve() in seen:
                continue
            agency = _agency_from_name(pdf.name)
            jobs.append(
                {
                    "path": pdf,
                    "excerpt": False,
                    "agency": agency,
                    "date": _date_from_name(pdf.name),
                    "title": pdf.stem,
                    "url": None,
                    "id_prefix": f"sample-extra-{pdf.stem}",
                }
            )
            extra += 1
    if reports_dir.exists():
        for pdf in sorted(reports_dir.glob("*.pdf")):
            agency = _agency_from_name(pdf.name)
            jobs.append(
                {
                    "path": pdf,
                    "excerpt": False,
                    "agency": agency,
                    "date": _date_from_name(pdf.name),
                    "title": pdf.stem,
                    "url": None,
                    "id_prefix": f"full-{pdf.stem}",
                }
            )
    return jobs


def _job_manifest_entry(job: dict) -> dict:
    path: Path = job["path"]
    return {
        "id_prefix": job["id_prefix"],
        "name": path.name,
        "size": path.stat().st_size,
        "excerpt": bool(job["excerpt"]),
    }


def build_corpus_manifest(samples_dir: Path, reports_dir: Path, cfg: dict | None = None) -> dict:
    jobs = iter_ingest_jobs(samples_dir, reports_dir, cfg)
    return {
        "schema": _INDEX_SCHEMA,
        "embedding_model": embedding_model_name(),
        "jobs": [_job_manifest_entry(job) for job in jobs],
    }


def corpus_fingerprint_from_manifest(manifest: dict) -> str:
    digest = hashlib.sha256()
    digest.update(json.dumps(manifest, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


def corpus_fingerprint(samples_dir: Path, reports_dir: Path) -> str:
    """Hash the planned ingest corpus so stale Chroma volumes can be detected.

    Args:
        samples_dir: Sample Reports directory.
        reports_dir: Full Reports directory.

    Returns:
        SHA-256 hex digest over schema version, embedding model, and PDF metadata.

    Example:
        >>> fp = corpus_fingerprint(Path("data/samples"), Path("data/reports"))
        >>> len(fp)
        64
    """
    return corpus_fingerprint_from_manifest(build_corpus_manifest(samples_dir, reports_dir))


def plan_corpus_index(
    retriever,
    *,
    samples_dir: Path,
    reports_dir: Path,
    force: bool = False,
) -> IndexPlan:
    """Decide whether to skip, rebuild, or incrementally sync the Chroma index."""
    manifest = build_corpus_manifest(samples_dir, reports_dir)
    fingerprint = corpus_fingerprint_from_manifest(manifest)
    stored_manifest = (
        retriever.stored_manifest() if hasattr(retriever, "stored_manifest") else None
    )
    stored_fp = retriever.stored_fingerprint() if hasattr(retriever, "stored_fingerprint") else None
    empty = retriever.is_empty()
    jobs = tuple(iter_ingest_jobs(samples_dir, reports_dir))

    if force:
        return IndexPlan("rebuild", "force", manifest, jobs, ())

    if not empty and stored_fp == fingerprint:
        return IndexPlan("skip", "up_to_date", manifest, (), ())

    if empty or stored_manifest is None or stored_fp is None:
        return IndexPlan("rebuild", "empty_or_legacy", manifest, jobs, ())

    if (
        stored_manifest.get("schema") != manifest["schema"]
        or stored_manifest.get("embedding_model") != manifest["embedding_model"]
    ):
        return IndexPlan("rebuild", "schema_or_model_change", manifest, jobs, ())

    stored_jobs = {row["id_prefix"]: row for row in stored_manifest.get("jobs") or []}
    current_jobs = {row["id_prefix"]: row for row in manifest["jobs"]}
    delete_prefixes: list[str] = [
        prefix for prefix in stored_jobs if prefix not in current_jobs
    ]
    jobs_to_index: list[dict] = []
    for job in jobs:
        entry = _job_manifest_entry(job)
        previous = stored_jobs.get(job["id_prefix"])
        if previous == entry:
            continue
        if job["id_prefix"] not in delete_prefixes:
            delete_prefixes.append(job["id_prefix"])
        jobs_to_index.append(job)

    if not jobs_to_index and not delete_prefixes:
        return IndexPlan("skip", "manifest_unchanged", manifest, (), ())

    return IndexPlan(
        "sync",
        "corpus_delta",
        manifest,
        tuple(jobs_to_index),
        tuple(delete_prefixes),
    )


def ingest_jobs(retriever: ChromaRetriever, jobs: list[dict] | tuple[dict, ...]) -> int:
    """Chunk and upsert a subset (or all) ingest jobs."""
    cfg = load_ingest_config()
    total = 0
    for job in jobs:
        agency = job["agency"]
        chunks = chunk_pdf(
            job["path"],
            agency=agency,
            excerpt=job["excerpt"],
            date=job["date"],
            title=job["title"],
            config=cfg,
            token_count=e5_token_count,
            url=_url_for_agency(agency, cfg, job.get("url")),
        )
        retriever.index_chunks(chunks, id_prefix=job["id_prefix"])
        total += len(chunks)
        print(f"indexed {job['path'].name}: {len(chunks)} chunks")
    return total


def ensure_index(
    retriever,
    *,
    samples_dir: Path,
    reports_dir: Path,
    force: bool = False,
) -> int:
    """Ensure Chroma matches the corpus; skip when the on-disk index is current.

    Args:
        retriever: Object with ``is_empty``, ``reset``, fingerprint I/O, and indexing.
        samples_dir: Sample Reports directory.
        reports_dir: Full Reports directory.
        force: When True, reset and re-ingest even if the fingerprint matches.

    Returns:
        Number of chunks indexed; ``0`` when the stored fingerprint is current.

    Example:
        >>> ensure_index(retriever, samples_dir=samples, reports_dir=reports)
        0  # index already matches corpus
        >>> ensure_index(retriever, samples_dir=samples, reports_dir=reports, force=True)
        142
    """
    plan = plan_corpus_index(
        retriever,
        samples_dir=samples_dir,
        reports_dir=reports_dir,
        force=force,
    )
    if plan.action == "skip":
        print(f"Chroma index up to date ({plan.reason}); skipping re-index.")
        return 0

    if plan.action == "rebuild":
        if not retriever.is_empty():
            reset = getattr(retriever, "reset", None)
            if callable(reset):
                reset()
        print(f"Chroma full re-index ({plan.reason}).")
        total = ingest_jobs(retriever, plan.jobs)
    else:
        print(f"Chroma incremental sync ({plan.reason}).")
        for prefix in plan.delete_prefixes:
            delete = getattr(retriever, "delete_by_id_prefix", None)
            if callable(delete):
                removed = delete(prefix)
                if removed:
                    print(f"removed {removed} chunks for {prefix}")
        total = ingest_jobs(retriever, plan.jobs)

    fingerprint = corpus_fingerprint_from_manifest(plan.manifest)
    write_fp = getattr(retriever, "write_fingerprint", None)
    write_manifest = getattr(retriever, "write_manifest", None)
    if callable(write_fp):
        write_fp(fingerprint)
    if callable(write_manifest):
        write_manifest(plan.manifest)
    return total


def ingest_samples_and_reports(
    retriever: ChromaRetriever,
    *,
    samples_dir: Path,
    reports_dir: Path,
) -> int:
    """Chunk every ingest job PDF and upsert embeddings into Chroma.

    Args:
        retriever: ``ChromaRetriever`` (or compatible) to receive chunks.
        samples_dir: Sample Reports directory.
        reports_dir: Full Reports directory.

    Returns:
        Total number of chunks indexed.

    Example:
        >>> n = ingest_samples_and_reports(retriever, samples_dir=samples, reports_dir=reports)
        >>> n > 0
        True
    """
    return ingest_jobs(retriever, iter_ingest_jobs(samples_dir, reports_dir))


_RETRIEVER = None


def _default_retriever():
    global _RETRIEVER
    if _RETRIEVER is not None:
        return _RETRIEVER
    root = Path(__file__).resolve().parent.parent
    persist = os.environ.get("CHROMA_PATH", str(root / "data" / "chroma"))
    samples = Path(os.environ.get("SAMPLES_PATH", str(root / "data" / "samples")))
    reports = Path(os.environ.get("REPORTS_PATH", str(root / "data" / "reports")))
    embedding = make_embedding_function()
    retriever = ChromaRetriever(persist, embedding, k=int(os.environ.get("RETRIEVE_K", "10")))
    ensure_index(retriever, samples_dir=samples, reports_dir=reports)
    _RETRIEVER = retriever
    return retriever


@maybe_traceable("analyst.retrieve_reports", run_type="retriever")
def retrieve_for_tool(query: str, retriever=None, k: int = 10) -> dict:
    """Report retrieve for the Ouroboros extension tool (no heading-rank)."""

    from oil_gas_analyst.turn import report_citation

    hits = (retriever or _default_retriever()).retrieve(query, k=k)
    chunks = []
    for chunk in hits:
        cite = report_citation(chunk)
        chunks.append(
            {
                "citation": cite.label,
                "text": chunk.text,
                "title": chunk.title,
                "heading": chunk.heading,
                "date": chunk.date,
                "excerpt": chunk.excerpt,
                "url": cite.url,
            }
        )
    return {"chunks": chunks, "count": len(chunks)}
