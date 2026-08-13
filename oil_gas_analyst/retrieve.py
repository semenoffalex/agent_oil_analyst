from __future__ import annotations

from pathlib import Path

import chromadb
from oil_gas_analyst.ingest import chunk_pdf, e5_token_count, load_ingest_config
from oil_gas_analyst.types import Chunk


class E5EmbeddingFunction:
    def __init__(self, model_name: str = "intfloat/multilingual-e5-base"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._prefix = "passage: "

    def __call__(self, input):
        texts = [self._prefix + t for t in input]
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    def embed_query(self, text: str) -> list[float]:
        vec = self._model.encode(["query: " + text], normalize_embeddings=True)[0]
        return vec.tolist()


def _meta_bool(value: str | bool) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in {"1", "true", "yes"}


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
    )


class ChromaRetriever:
    def __init__(self, persist_path: str, embedding: E5EmbeddingFunction, k: int = 5):
        self._k = k
        self._embedding = embedding
        self._client = chromadb.PersistentClient(path=persist_path)
        self._col = self._client.get_or_create_collection(
            name="reports",
            metadata={"hnsw:space": "cosine"},
        )

    def is_empty(self) -> bool:
        return self._col.count() == 0

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
            }
            for c in chunks
        ]
        self._col.upsert(ids=ids, documents=docs, embeddings=embeddings, metadatas=metas)

    def retrieve(self, question: str, k: int = 5) -> list[Chunk]:
        n = min(k or self._k, max(self._col.count(), 1))
        if self._col.count() == 0:
            return []
        q = self._embedding.embed_query(question)
        got = self._col.query(query_embeddings=[q], n_results=min(n, self._col.count()))
        docs = (got.get("documents") or [[]])[0]
        metas = (got.get("metadatas") or [[]])[0]
        out: list[Chunk] = []
        for text, meta in zip(docs, metas):
            out.append(_chunk_from_meta(text, meta or {}))
        return out


def ingest_samples_and_reports(
    retriever: ChromaRetriever,
    *,
    samples_dir: Path,
    reports_dir: Path,
) -> int:
    cfg = load_ingest_config()
    total = 0
    for i, sample in enumerate(cfg.get("samples") or []):
        path = Path(sample["path"])
        if not path.exists():
            path = samples_dir / path.name
        if not path.exists():
            raise FileNotFoundError(f"Sample Report missing: {sample['path']}")
        chunks = chunk_pdf(
            path,
            agency=sample.get("agency", "OPEC"),
            excerpt=True,
            date=sample.get("date"),
            title=sample.get("title", path.stem),
            config=cfg,
            token_count=e5_token_count,
        )
        retriever.index_chunks(chunks, id_prefix=f"sample-{i}")
        total += len(chunks)
    if reports_dir.exists():
        for j, pdf in enumerate(sorted(reports_dir.glob("*.pdf"))):
            agency = "EIA" if "steo" in pdf.name.lower() or "eia" in pdf.name.lower() else "OPEC"
            chunks = chunk_pdf(
                pdf,
                agency=agency,
                excerpt=False,
                date=None,
                title=pdf.stem,
                config=cfg,
                token_count=e5_token_count,
            )
            retriever.index_chunks(chunks, id_prefix=f"full-{j}")
            total += len(chunks)
    return total
