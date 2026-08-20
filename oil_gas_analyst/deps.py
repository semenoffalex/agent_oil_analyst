from __future__ import annotations

import os
from pathlib import Path
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from oil_gas_analyst.ingest import load_ingest_config
from oil_gas_analyst.ouroboros import OuroborosLoop
from oil_gas_analyst.settings import require_deepseek_key, require_embedding_api_key

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


def build_loop() -> OuroborosLoop:
    """Wire Streamlit to the Ouroboros gateway. Missing DeepSeek or embedding key fails loudly."""

    require_deepseek_key()
    require_embedding_api_key()
    url = os.environ.get("OUROBOROS_URL", "http://127.0.0.1:8765").strip()
    timeout = float(os.environ.get("OUROBOROS_TURN_TIMEOUT_SEC", "300"))
    enable_domain_skills(url)
    return OuroborosLoop(url, timeout_sec=timeout)


def enable_domain_skills(base_url: str) -> None:
    """Owner-attest and enable playbook, retrieve, Web, and Forecast skills.

    Failures are logged; a missing enable is a broken Demo, not a silent LangGraph fallback.
    """

    import json
    import urllib.error
    import urllib.request

    root = base_url.rstrip("/")
    for name in ("oil_gas_analyst", "oil_gas_retrieve", "oil_gas_web", "oil_gas_forecast"):
        for path, body in (
            (f"/api/owner/skills/{name}/attest-review", {}),
            (f"/api/skills/{name}/toggle", {"enabled": True}),
        ):
            payload = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                root + path,
                data=payload,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    resp.read()
            except urllib.error.HTTPError as exc:
                # 409: already attested / duplicate review. 200-class success is enough.
                if exc.code == 409:
                    print(f"skill enable {name} {path}: already attested (HTTP 409)")
                else:
                    body = exc.read().decode("utf-8", errors="replace")[:300]
                    print(f"skill enable {name} {path}: HTTP {exc.code} {body}")
            except urllib.error.URLError as exc:
                print(f"skill enable {name} {path}: {exc}")


def build_deps(*, ingest_if_empty: bool = True):
    """Wire Report index deps for ingest CLI. Chat does not use this path."""

    from oil_gas_analyst.retrieve import ChromaRetriever, ensure_index, make_embedding_function

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
