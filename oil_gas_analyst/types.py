from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Protocol


CitationKind = Literal["report", "web", "forecast"]


@dataclass(frozen=True)
class Chunk:
    text: str
    title: str
    date: str | None
    page_start: int | None
    page_end: int | None
    heading: str
    excerpt: bool = False
    agency: str = ""
    url: str | None = None


@dataclass(frozen=True)
class WebHit:
    title: str
    url: str
    snippet: str = ""


@dataclass(frozen=True)
class MethodForecast:
    name: str
    point: float | None
    low: float | None
    high: float | None
    interpretation: str


@dataclass(frozen=True)
class ForecastResult:
    symbol: str
    methods: list[MethodForecast]
    unavailable_reason: str | None = None
    horizon_days: int | None = None


@dataclass(frozen=True)
class Citation:
    kind: CitationKind
    label: str
    url: str | None = None


@dataclass(frozen=True)
class LoopResult:
    """What the Ouroboros loop returned for one question (the Analyst-turn seam)."""

    text: str
    citations: list[Citation] = field(default_factory=list)
    retrieved: bool = False
    web_ran: bool = False
    forecast_ran: bool = False
    forecast_failed: bool = False
    web_reason: str | None = None


class LoopError(RuntimeError):
    """Timeout, HTTP 500, or empty completion — not a live model reply."""


class AnalystLoop(Protocol):
    def complete(self, question: str) -> LoopResult: ...


@dataclass(frozen=True)
class Reply:
    text: str
    citations: list[Citation] = field(default_factory=list)
    retrieved: bool = False
    web_ran: bool = False
    forecast_ran: bool = False
    forecast_failed: bool = False
    refused: bool = False
    steps: list[str] = field(default_factory=list)
    web_reason: str | None = None


class CompetenceClassifier(Protocol):
    def classify(self, question: str) -> Literal["in", "out"]: ...


class Retriever(Protocol):
    def retrieve(self, question: str, k: int = 10) -> list[Chunk]: ...


class ChunkDropper(Protocol):
    def keep(self, question: str, chunks: list[Chunk]) -> list[Chunk]: ...


class WebSearch(Protocol):
    def search(self, question: str) -> list[WebHit]: ...


class ForecastModule(Protocol):
    def forecast(self, question: str) -> ForecastResult: ...


class Composer(Protocol):
    def compose(self, question: str, **kwargs) -> str: ...
