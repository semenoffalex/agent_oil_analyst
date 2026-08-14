from __future__ import annotations

from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
from typing import Literal

from oil_gas_analyst.types import Chunk, ForecastResult, WebHit

CLASSIFY_SYSTEM = (
    "You classify user questions for a senior oil-and-gas market Analyst. "
    "Competence is only: upstream, midstream, downstream, Brent/WTI/Urals, OPEC+, "
    "sanctions as they affect the oil market, supply and demand. "
    "Weather, software, sports, uranium, medicine, and general trivia are out. "
    "Reply with label in or out only."
)

DROP_SYSTEM = (
    "You are given Retrieved Report chunks. Return the 0-based indices of chunks "
    "that can support the answer: oil prices, demand, supply, OPEC/EIA outlooks, "
    "or the same crude — including English chunks for a Russian question and a nearby "
    "horizon if the exact month is missing. Drop only off-topic chunks "
    "(tankers, electricity, coal, unrelated appendices) unless the question is about those. "
    "If the question is about oil prices or outlooks, prefer keeping a Crude Oil Price "
    "Movements / Global oil prices / World Oil Demand chunk over an empty list."
)

COMPOSE_SYSTEM = (
    "You are a senior oil-and-gas market Analyst. Answer in the user's language. "
    "Reports are the primary source. If Report chunks are provided, the answer MUST "
    "lead with their figures and tag those claims with the [Отчёт …] labels. "
    "Web sources are a supplement only for facts that are not in the Reports "
    "(live quotes, new statements). Do not write a web-only answer when Reports "
    "are present. Structured, with figures only if they appear in the provided Report "
    "chunks, Web sources, or Forecast. Never invent prices or volumes. "
    "If data is missing, say so. Tag every material claim with the exact citation labels "
    "listed in the user message. Do not mention being an AI."
)


class CompetenceLabel(BaseModel):
    label: Literal["in", "out"]


class KeepIndices(BaseModel):
    indices: list[int] = Field(default_factory=list)


def make_chat(api_key: str, base_url: str, model: str) -> ChatOpenAI:
    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url,
        model=model,
        temperature=0,
        timeout=120,
        extra_body={"thinking": {"type": "disabled"}},
    )


class DeepSeekClassifier:
    def __init__(self, llm: ChatOpenAI):
        # DeepSeek rejects json_schema / json_object response_format (HTTP 400).
        self._llm = llm.with_structured_output(CompetenceLabel, method="function_calling")

    def classify(self, question: str) -> Literal["in", "out"]:
        try:
            out = self._llm.invoke(
                [
                    {"role": "system", "content": CLASSIFY_SYSTEM},
                    {"role": "user", "content": question},
                ]
            )
            return out.label
        except Exception:
            return "out"


class DeepSeekDropper:
    def __init__(self, llm: ChatOpenAI):
        self._llm = llm.with_structured_output(KeepIndices, method="function_calling")

    def keep(self, question: str, chunks: list[Chunk]) -> list[Chunk]:
        if not chunks:
            return []
        listed = "\n".join(f"[{i}] {c.heading}: {c.text[:800]}" for i, c in enumerate(chunks))
        try:
            out = self._llm.invoke(
                [
                    {"role": "system", "content": DROP_SYSTEM},
                    {"role": "user", "content": f"Question: {question}\n\nChunks:\n{listed}"},
                ]
            )
            idxs = [i for i in out.indices if 0 <= i < len(chunks)]
            return [chunks[i] for i in idxs]
        except Exception:
            return list(chunks)


class DeepSeekComposer:
    def __init__(self, llm: ChatOpenAI):
        self._llm = llm

    def compose(self, question: str, **kwargs) -> str:
        kept: list[Chunk] = kwargs.get("kept") or []
        web: list[WebHit] = kwargs.get("web") or []
        forecast: ForecastResult | None = kwargs.get("forecast")
        citations = kwargs.get("citations") or []
        cite_blob = "\n".join(getattr(c, "label", str(c)) for c in citations) or "(none)"
        reports = "\n".join(
            f"- {c.title} {c.heading} p.{c.page_start}: {c.text[:1200]}" for c in kept
        ) or "(none)"
        webs = "\n".join(f"- {h.title} {h.url}: {h.snippet}" for h in web) or "(none)"
        fc = "(none)"
        if forecast is not None:
            if forecast.unavailable_reason:
                fc = f"{forecast.symbol}: {forecast.unavailable_reason}"
            else:
                fc = "\n".join(
                    f"{m.name}: point={m.point} low={m.low} high={m.high} ({m.interpretation})"
                    for m in forecast.methods
                )
        try:
            msg = self._llm.invoke(
                [
                    {"role": "system", "content": COMPOSE_SYSTEM},
                    {
                        "role": "user",
                        "content": (
                            f"Question: {question}\n\n"
                            "Use Report chunks first. Cite [Отчёт …] for those claims. "
                            "Use Web sources only for facts not in Reports.\n\n"
                            f"Reports:\n{reports}\n\n"
                            f"Web sources:\n{webs}\n\nForecast:\n{fc}\n\n"
                            f"Citation labels (use verbatim):\n{cite_blob}\n"
                        ),
                    },
                ]
            )
            return str(msg.content)
        except Exception:
            return "I could not compose a full answer. See citations. I will not invent figures."
