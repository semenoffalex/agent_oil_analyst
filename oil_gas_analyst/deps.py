from __future__ import annotations

import os
from pathlib import Path
from urllib.request import Request, urlopen

from dotenv import load_dotenv

from oil_gas_analyst.denylist import load_denylist
from oil_gas_analyst.forecast import run_forecast
from oil_gas_analyst.ingest import load_ingest_config
from oil_gas_analyst.llm import DeepSeekClassifier, DeepSeekComposer, DeepSeekDropper, make_chat
from oil_gas_analyst.retrieve import ChromaRetriever, ingest_samples_and_reports, make_embedding_function
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


def build_deps(*, ingest_if_empty: bool = True) -> AnalystDeps:
    llm = make_chat(
        api_key=_require_key(),
        base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        model=os.environ.get("DEEPSEEK_MODEL", "deepseek-v4-flash"),
    )
    persist = os.environ.get("CHROMA_PATH", str(ROOT / "data" / "chroma"))
    samples = Path(os.environ.get("SAMPLES_PATH", str(ROOT / "data" / "samples")))
    reports = Path(os.environ.get("REPORTS_PATH", str(ROOT / "data" / "reports")))
    embedding = make_embedding_function()
    try:
        embedding.embed_query("warmup")
    except Exception as exc:
        print(f"embedding warmup failed: {exc}")
    retriever = ChromaRetriever(persist, embedding)
    if ingest_if_empty and retriever.is_empty():
        ingest_samples_and_reports(retriever, samples_dir=samples, reports_dir=reports)
    return AnalystDeps(
        classifier=DeepSeekClassifier(llm),
        retriever=retriever,
        dropper=DeepSeekDropper(llm),
        web=DuckDuckGoWeb(),
        forecast=YFinanceForecast(),
        composer=DeepSeekComposer(llm),
        denied_domains=list(load_denylist()),
        retrieve_k=int(os.environ.get("RETRIEVE_K", "5")),
    )


def download_full_reports() -> list[Path]:
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
