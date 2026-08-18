from __future__ import annotations

import os
from pathlib import Path
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from oil_gas_analyst.ingest import load_ingest_config
from oil_gas_analyst.ouroboros import OuroborosLoop
from oil_gas_analyst.retrieve import ChromaRetriever, ensure_index, make_embedding_function
from oil_gas_analyst.settings import require_openrouter_key

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def build_loop() -> OuroborosLoop:
    """Wire Chainlit to the Ouroboros gateway. Missing OpenRouter key fails loudly."""

    require_openrouter_key()
    url = os.environ.get("OUROBOROS_URL", "http://127.0.0.1:8765").strip()
    timeout = float(os.environ.get("OUROBOROS_TURN_TIMEOUT_SEC", "180"))
    return OuroborosLoop(url, timeout_sec=timeout)


def build_deps(*, ingest_if_empty: bool = True):
    """Wire Report index deps for ingest CLI. Chat does not use this path."""

    persist = os.environ.get("CHROMA_PATH", str(ROOT / "data" / "chroma"))
    samples = Path(os.environ.get("SAMPLES_PATH", str(ROOT / "data" / "samples")))
    reports = Path(os.environ.get("REPORTS_PATH", str(ROOT / "data" / "reports")))
    embedding = make_embedding_function()
    try:
        embedding.embed_query("warmup")
    except Exception as exc:
        print(f"embedding warmup failed: {exc}")
    retrieve_k = int(os.environ.get("RETRIEVE_K", "10"))
    retriever = ChromaRetriever(persist, embedding, k=retrieve_k)
    if ingest_if_empty:
        ensure_index(retriever, samples_dir=samples, reports_dir=reports)
    return _IndexDeps(retriever=retriever)


class _IndexDeps:
    def __init__(self, retriever):
        self.retriever = retriever


def build_eval_deps(*, ingest_if_empty: bool = True) -> OuroborosLoop:
    """Live Eval uses the same Ouroboros loop as Demo. Model pin is Main unless EVAL_CHAT_MODEL is set."""

    return build_loop()


def download_full_reports() -> list[Path]:
    """Fetch configured Full Report PDFs into ``REPORTS_PATH``.

    Returns:
        Paths successfully saved; failures are logged and skipped.
    """
    cfg = load_ingest_config()
    dest = Path(os.environ.get("REPORTS_PATH", str(ROOT / "data" / "reports")))
    dest.mkdir(parents=True, exist_ok=True)
    saved: list[Path] = []
    for item in cfg.get("full_reports") or []:
        url = item["url"]
        if item.get("id") == "opec-momr":
            url = os.environ.get("OPEC_MOMR_URL", item["url"])
        name = f"{item['id']}.pdf"
        path = dest / name
        req = Request(url, headers={"User-Agent": "OilGasAnalyst/1.0"})
        try:
            with urlopen(req, timeout=60) as resp:
                path.write_bytes(resp.read())
            saved.append(path)
            print(f"saved {path}")
        except Exception as exc:
            print(f"Full Report download failed for {item.get('id')}: {exc}")
    return saved
