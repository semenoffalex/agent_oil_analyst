from __future__ import annotations

import json
import os
import re
import socket
from pathlib import Path
from urllib.parse import urlparse, urlunparse
from urllib.request import Request, urlopen

from oil_gas_analyst.ingest import chunk_pdf, e5_token_count, e5_tokenizer_name, load_ingest_config
from oil_gas_analyst.types import Chunk

_PASSAGE = "passage: "
_QUERY = "query: "
_EMBED_BATCH = 32


def _prefer_ipv4(url: str) -> str:
    """Resolve host.docker.internal (and similar) to IPv4 so urllib does not hang on IPv6."""
    parsed = urlparse(url)
    host = parsed.hostname
    if not host:
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


class E5EmbeddingFunction:
    def __init__(self, model_name: str | None = None):
        import os

        from sentence_transformers import SentenceTransformer

        model_name = model_name or os.environ.get(
            "EMBEDDING_MODEL", "intfloat/multilingual-e5-base"
        )
        from pathlib import Path

        local = Path(model_name)
        offline = os.environ.get("HF_HUB_OFFLINE", "").strip().lower() in {
            "1",
            "true",
            "yes",
        } or os.environ.get("TRANSFORMERS_OFFLINE", "").strip().lower() in {
            "1",
            "true",
            "yes",
        } or local.is_dir()
        try:
            self._model = SentenceTransformer(
                str(local) if local.is_dir() else model_name,
                local_files_only=offline,
            )
        except TypeError:
            self._model = SentenceTransformer(
                str(local) if local.is_dir() else model_name
            )
        self._prefix = _PASSAGE

    def __call__(self, input):
        texts = [self._prefix + t for t in input]
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def embed_query(self, text: str) -> list[float]:
        vec = self._model.encode([_QUERY + text], normalize_embeddings=True)[0]
        return vec.tolist()


class OpenAICompatibleEmbeddingFunction:
    """OpenAI-compatible /v1/embeddings (LM Studio). Same e5 query/passage prefixes."""

    def __init__(
        self,
        base_url: str,
        model_name: str,
        api_key: str = "lm-studio",
        timeout: float = 15,
    ):
        base = base_url.rstrip("/")
        if not base.endswith("/v1"):
            base = f"{base}/v1"
        self._url = _prefer_ipv4(f"{base}/embeddings")
        self._model = model_name
        self._api_key = api_key or "lm-studio"
        self._timeout = timeout

    def _embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), _EMBED_BATCH):
            out.extend(self._embed_batch(texts[i : i + _EMBED_BATCH]))
        return out

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"model": self._model, "input": texts}).encode("utf-8")
        req = Request(
            self._url,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
            method="POST",
        )
        with urlopen(req, timeout=self._timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        rows = sorted(data.get("data") or [], key=lambda row: int(row.get("index", 0)))
        vecs = [row["embedding"] for row in rows]
        if len(vecs) != len(texts):
            raise RuntimeError(
                f"Embedding endpoint returned {len(vecs)} vectors for {len(texts)} inputs"
            )
        return vecs

    def __call__(self, input):
        return self._embed([_PASSAGE + t for t in input])

    def embed_query(self, text: str) -> list[float]:
        return self._embed([_QUERY + text])[0]


class FallbackEmbeddingFunction:
    """Try remote OpenAI-compatible embeddings; on connection errors use local e5."""

    def __init__(self, primary, fallback_factory):
        self._primary = primary
        self._fallback_factory = fallback_factory
        self._fallback = None
        self._active = primary

    def _switch(self, exc: BaseException) -> None:
        if self._fallback is None:
            print(f"remote embeddings failed ({exc}); falling back to local e5")
            self._fallback = self._fallback_factory()
        self._active = self._fallback

    def __call__(self, input):
        try:
            return self._active(input)
        except Exception as exc:
            if self._active is not self._primary:
                raise
            self._switch(exc)
            return self._active(input)

    def embed_query(self, text: str) -> list[float]:
        try:
            return self._active.embed_query(text)
        except Exception as exc:
            if self._active is not self._primary:
                raise
            self._switch(exc)
            return self._active.embed_query(text)


def local_embedding_model_name() -> str:
    return e5_tokenizer_name()


def make_embedding_function():
    base = os.environ.get("EMBEDDING_BASE_URL", "").strip()
    model = os.environ.get("EMBEDDING_MODEL", "intfloat/multilingual-e5-base")
    if base:
        remote = OpenAICompatibleEmbeddingFunction(
            base,
            model,
            api_key=os.environ.get("EMBEDDING_API_KEY", "lm-studio"),
        )
        return FallbackEmbeddingFunction(remote, lambda: E5EmbeddingFunction(local_embedding_model_name()))
    local = Path(model)
    return E5EmbeddingFunction(str(local) if local.is_dir() else model)


def _meta_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


_OUTLOOK_HEADINGS = (
    "crude oil price",
    "world oil demand",
    "world oil supply",
    "balance of supply and demand",
    "global oil price",
    "global oil market",
    "global liquid fuel",
    "нефть",
)
_OFFTOPIC_HEADINGS = (
    "tanker",
    "electricity",
    "coal",
    "appendix",
    "product markets",
    "refined products trade",
)


def _date_key(date: str | None) -> str:
    return (date or "").strip() or "0000"


def _heading_rank(question: str, heading: str) -> int:
    h = (heading or "").casefold()
    q = question.casefold()
    if any(word in q for word in ("tanker", "танкер", "фрахт", "vlcc")):
        return 2 if "tanker" in h else 0
    if any(word in q for word in ("electric", "электрич")):
        return 2 if "electric" in h else 0
    if "coal" in q or "угол" in q:
        return 2 if "coal" in h else 0
    if any(marker in h for marker in _OUTLOOK_HEADINGS):
        return 2
    if any(marker in h for marker in _OFFTOPIC_HEADINGS):
        return -1
    return 0


def select_report_chunks(question: str, chunks: list[Chunk], k: int = 5) -> list[Chunk]:
    """Prefer outlook sections and newer Report dates, then cut to k."""
    if not chunks:
        return []
    ranked = sorted(
        chunks,
        key=lambda chunk: (_heading_rank(question, chunk.heading), _date_key(chunk.date)),
        reverse=True,
    )
    return ranked[: max(k, 0)]


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
    def __init__(self, persist_path: str, embedding: E5EmbeddingFunction, k: int = 10):
        import chromadb

        self._k = k
        self._embedding = embedding
        self._client = chromadb.PersistentClient(path=persist_path)
        self._col = self._client.get_or_create_collection(
            name="reports",
            metadata={"hnsw:space": "cosine"},
        )

    def is_empty(self) -> bool:
        return self._col.count() == 0

    def reset(self) -> None:
        self._client.delete_collection("reports")
        self._col = self._client.get_or_create_collection(
            name="reports",
            metadata={"hnsw:space": "cosine"},
        )

    def index_chunks(self, chunks: list[Chunk], id_prefix: str) -> None:
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
        k = k or self._k
        total = self._col.count()
        if total == 0:
            return []
        pool = min(max(k * 3, 10), total)
        q = self._embedding.embed_query(question)
        got = self._col.query(query_embeddings=[q], n_results=pool)
        docs = (got.get("documents") or [[]])[0]
        metas = (got.get("metadatas") or [[]])[0]
        out: list[Chunk] = []
        for text, meta in zip(docs, metas):
            out.append(_chunk_from_meta(text, meta or {}))
        return select_report_chunks(question, out, k=k)


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


def ingest_samples_and_reports(
    retriever: ChromaRetriever,
    *,
    samples_dir: Path,
    reports_dir: Path,
) -> int:
    cfg = load_ingest_config()
    total = 0
    seen: set[Path] = set()
    for i, sample in enumerate(cfg.get("samples") or []):
        path = Path(sample["path"])
        if not path.exists():
            path = samples_dir / path.name
        if not path.exists():
            raise FileNotFoundError(f"Sample Report missing: {sample['path']}")
        seen.add(path.resolve())
        excerpt = bool(sample.get("excerpt", True))
        agency = sample.get("agency") or _agency_from_name(path.name)
        chunks = chunk_pdf(
            path,
            agency=agency,
            excerpt=excerpt,
            date=sample.get("date") or _date_from_name(path.name),
            title=sample.get("title", path.stem),
            config=cfg,
            token_count=e5_token_count,
            url=_url_for_agency(agency, cfg, sample.get("url")),
        )
        retriever.index_chunks(chunks, id_prefix=f"sample-{i}")
        total += len(chunks)
        print(f"indexed {path.name}: {len(chunks)} chunks")
    extra = 0
    if samples_dir.exists():
        for pdf in sorted(samples_dir.glob("*.pdf")):
            if pdf.resolve() in seen:
                continue
            agency = _agency_from_name(pdf.name)
            chunks = chunk_pdf(
                pdf,
                agency=agency,
                excerpt=False,
                date=_date_from_name(pdf.name),
                title=pdf.stem,
                config=cfg,
                token_count=e5_token_count,
                url=_url_for_agency(agency, cfg),
            )
            retriever.index_chunks(chunks, id_prefix=f"sample-extra-{extra}")
            total += len(chunks)
            extra += 1
            print(f"indexed {pdf.name}: {len(chunks)} chunks")
    if reports_dir.exists():
        for j, pdf in enumerate(sorted(reports_dir.glob("*.pdf"))):
            agency = _agency_from_name(pdf.name)
            chunks = chunk_pdf(
                pdf,
                agency=agency,
                excerpt=False,
                date=_date_from_name(pdf.name),
                title=pdf.stem,
                config=cfg,
                token_count=e5_token_count,
                url=_url_for_agency(agency, cfg),
            )
            retriever.index_chunks(chunks, id_prefix=f"full-{j}")
            total += len(chunks)
            print(f"indexed {pdf.name}: {len(chunks)} chunks")
    return total
