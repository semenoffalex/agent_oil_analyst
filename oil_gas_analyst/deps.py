from __future__ import annotations

import os
from pathlib import Path
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from oil_gas_analyst.denylist import load_denylist
from oil_gas_analyst.forecast import run_forecast
from oil_gas_analyst.ingest import load_ingest_config
from oil_gas_analyst.llm import DeepSeekClassifier, DeepSeekComposer, DeepSeekDropper, make_chat
from oil_gas_analyst.retrieve import ChromaRetriever, ensure_index, make_embedding_function
from oil_gas_analyst.turn import AnalystDeps
from oil_gas_analyst.web import DuckDuckGoWeb

load_dotenv()

ROOT = Path(__file__).resolve().parent.parent


class YFinanceForecast:
    def forecast(self, question: str):
        return run_forecast(question)


def _require_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not key:
        raise RuntimeError("DEEPSEEK_API_KEY is missing. Copy .env.example to .env.")
    return key


def _analyst_deps(llm, *, ingest_if_empty: bool) -> AnalystDeps:
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
    return AnalystDeps(
        classifier=DeepSeekClassifier(llm),
        retriever=retriever,
        dropper=DeepSeekDropper(llm),
        web=DuckDuckGoWeb(),
        forecast=YFinanceForecast(),
        composer=DeepSeekComposer(llm),
        denied_domains=list(load_denylist()),
        retrieve_k=retrieve_k,
    )


def build_deps(*, ingest_if_empty: bool = True) -> AnalystDeps:
    """Wire production classifier, retriever, web, forecast, and composer.

    Args:
        ingest_if_empty: When True, call ``ensure_index`` if Chroma is stale or empty.

    Returns:
        ``AnalystDeps`` ready for ``run_turn`` or ``invoke_analyst``.

    Example:
        >>> deps = build_deps()
        >>> deps.retrieve_k
        10
    """
    llm = make_chat(
        api_key=_require_key(),
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
        extra_body={"thinking": {"type": "disabled"}},
    )
    return _analyst_deps(llm, ingest_if_empty=ingest_if_empty)


def _require_eval_chat() -> tuple[str, str, str]:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    model = os.environ.get("EVAL_CHAT_MODEL", "").strip()
    base_url = os.environ.get("OPENROUTER_BASE_URL", "").strip()
    missing = [
        name
        for name, value in (
            ("OPENROUTER_API_KEY", key),
            ("OPENROUTER_BASE_URL", base_url),
            ("EVAL_CHAT_MODEL", model),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(
            "Live Eval env is incomplete: " + ", ".join(missing) + ". Copy .env.example to .env."
        )
    return key, base_url, model


def build_eval_deps(*, ingest_if_empty: bool = True) -> AnalystDeps:
    """Wire live Eval deps: same graph, OpenRouter chat from ``.env`` (ADR 0018)."""
    key, base_url, model = _require_eval_chat()
    llm = make_chat(
        api_key=key,
        base_url=base_url,
        model=model,
        default_headers={
            "HTTP-Referer": os.environ.get(
                "OPENROUTER_HTTP_REFERER",
                "https://github.com/semenoffalex/agent_oil_analyst",
            ),
            "X-Title": os.environ.get("OPENROUTER_APP_TITLE", "oil-gas-analyst-eval"),
        },
    )
    return _analyst_deps(llm, ingest_if_empty=ingest_if_empty)


def download_full_reports() -> list[Path]:
    """Fetch configured Full Report PDFs into ``REPORTS_PATH``.

    Returns:
        Paths successfully saved; failures are logged and skipped.

    Example:
        >>> paths = download_full_reports()
        >>> all(p.suffix == ".pdf" for p in paths)
        True
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
