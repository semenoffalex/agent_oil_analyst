from oil_gas_analyst.turn import AnalystDeps, run_turn
from oil_gas_analyst.types import Chunk, ForecastResult, MethodForecast, WebHit


class _FixedClassifier:
    def __init__(self, label: str):
        self.label = label

    def classify(self, question: str) -> str:
        return self.label


class _Retr:
    def __init__(self, chunks: list[Chunk] | None = None):
        self.chunks = chunks or []

    def retrieve(self, question: str, k: int = 5) -> list[Chunk]:
        return list(self.chunks[:k])


class _Drop:
    def __init__(self, keep_all: bool = True):
        self.keep_all = keep_all

    def keep(self, question: str, chunks: list[Chunk]) -> list[Chunk]:
        return list(chunks) if self.keep_all else []


class _Web:
    def __init__(self, hits: list[WebHit] | None = None, error: Exception | None = None):
        self.hits = hits or []
        self.error = error

    def search(self, question: str) -> list[WebHit]:
        if self.error:
            raise self.error
        return list(self.hits)


class _Forecast:
    def __init__(self, result: ForecastResult | None = None, error: Exception | None = None):
        self.result = result
        self.error = error

    def forecast(self, question: str) -> ForecastResult:
        if self.error:
            raise self.error
        if self.result is None:
            raise AssertionError("forecast should not run")
        return self.result


class _Composer:
    def compose(self, question: str, **kwargs) -> str:
        if kwargs.get("refused"):
            return "This is outside my Competence as an oil and gas Analyst."
        return "Analyst reply."


def _deps(**kwargs) -> AnalystDeps:
    return AnalystDeps(
        classifier=kwargs.get("classifier", _FixedClassifier("in")),
        retriever=kwargs.get("retriever", _Retr()),
        dropper=kwargs.get("dropper", _Drop()),
        web=kwargs.get("web", _Web()),
        forecast=kwargs.get("forecast", _Forecast()),
        composer=kwargs.get("composer", _Composer()),
        denied_domains=kwargs.get("denied_domains", ["kp.ru", "dailymail.co.uk"]),
    )


def test_out_of_competence_refuses_without_tools():
    reply = run_turn(
        "what's the weather today?",
        _deps(classifier=_FixedClassifier("out")),
    )
    assert reply.refused is True
    assert reply.retrieved is False
    assert reply.web_ran is False
    assert reply.forecast_ran is False
    assert reply.citations == []
    assert "outside" in reply.text.lower()


def test_out_of_competence_python_refuses():
    reply = run_turn("write a Python sort", _deps(classifier=_FixedClassifier("out")))
    assert reply.refused is True
    assert reply.web_ran is False
    assert reply.forecast_ran is False


MOMR = Chunk(
    text="The global oil demand growth forecast for 2026 remains at 1.4 mb/d.",
    title="OPEC Monthly Oil Market Report — March 2026 (excerpt, World Oil Demand)",
    date="2026-03",
    page_start=42,
    page_end=46,
    heading="World Oil Demand",
    excerpt=True,
)

TANKER = Chunk(
    text="VLCC freight rates on the Middle East-to-Asia route rose.",
    title="OPEC Monthly Oil Market Report — March 2026 (Tanker Market)",
    date="2026-03",
    page_start=80,
    page_end=82,
    heading="Tanker Market",
    excerpt=True,
)

REUTERS = WebHit(
    title="Brent rises on OPEC statement",
    url="https://www.reuters.com/markets/brent",
    snippet="Brent crude rose.",
)

TABLOID = WebHit(title="Shock oil", url="https://www.kp.ru/oil", snippet="...")

TWO_METHODS = ForecastResult(
    symbol="BZ=F",
    methods=[
        MethodForecast(name="sarima", point=80.0, low=70.0, high=90.0, interpretation="SARIMA path"),
        MethodForecast(
            name="holt_winters", point=81.0, low=72.0, high=91.0, interpretation="Holt-Winters path"
        ),
    ],
)


def test_report_covered_question_cites_excerpt_and_skips_web():
    reply = run_turn(
        "What is OPEC's 2026 world oil demand outlook?",
        _deps(retriever=_Retr([MOMR])),
    )
    assert reply.refused is False
    assert reply.retrieved is True
    assert reply.web_ran is False
    assert reply.forecast_ran is False
    assert any(c.kind == "report" and "excerpt" in c.label.lower() and "OPEC" in c.label for c in reply.citations)


def test_outlook_in_published_forecasts_stays_on_reports():
    reply = run_turn(
        "Какой тренд в прогнозах цен на нефть на ближайший месяц?",
        _deps(retriever=_Retr([MOMR])),
    )
    assert reply.forecast_ran is False
    assert reply.web_ran is False
    assert any(c.kind == "report" for c in reply.citations)


def test_compose_without_report_tag_appends_report_block():
    reply = run_turn(
        "What is OPEC's 2026 world oil demand outlook?",
        _deps(retriever=_Retr([MOMR])),
    )
    assert "[Отчёт" in reply.text
    assert "1.4 mb/d" in reply.text


class _TaggedComposer:
    def compose(self, question: str, **kwargs) -> str:
        cites = kwargs.get("citations") or []
        report = next(c.label for c in cites if c.kind == "report")
        return f"Demand stays at 1.4 mb/d {report}."


def test_compose_that_already_tags_report_is_not_duplicated():
    reply = run_turn(
        "What is OPEC's 2026 world oil demand outlook?",
        _deps(retriever=_Retr([MOMR]), composer=_TaggedComposer()),
    )
    assert reply.text.count("[Отчёт") == 1
    assert "1.4 mb/d" in reply.text


def test_dropped_off_topic_chunks_open_web():
    reply = run_turn(
        "What is happening on European gas pipelines?",
        _deps(retriever=_Retr([TANKER]), dropper=_Drop(keep_all=False), web=_Web([REUTERS])),
    )
    assert not any(c.kind == "report" for c in reply.citations)
    assert reply.web_ran is True
    assert any(c.kind == "web" for c in reply.citations)


def test_overdrop_of_on_topic_chunks_stays_on_reports():
    reply = run_turn(
        "What is OPEC's 2026 world oil demand outlook?",
        _deps(retriever=_Retr([MOMR]), dropper=_Drop(keep_all=False), web=_Web([REUTERS])),
    )
    assert reply.web_ran is False
    assert any(c.kind == "report" and "OPEC" in c.label for c in reply.citations)
    assert not any(c.kind == "web" for c in reply.citations)


def test_overdrop_restores_demand_not_tanker():
    reply = run_turn(
        "What is OPEC's 2026 world oil demand outlook?",
        _deps(
            retriever=_Retr([TANKER, MOMR]),
            dropper=_Drop(keep_all=False),
            web=_Web([REUTERS]),
        ),
    )
    assert reply.web_ran is False
    labels = " ".join(c.label for c in reply.citations if c.kind == "report")
    assert "World Oil Demand" in labels
    assert "Tanker Market" not in labels
    assert not any(c.kind == "web" for c in reply.citations)


def test_time_sensitive_runs_web_and_keeps_report_tags():
    reply = run_turn(
        "What's Brent today given OPEC demand?",
        _deps(retriever=_Retr([MOMR]), web=_Web([REUTERS])),
    )
    assert reply.web_ran is True
    kinds = {c.kind for c in reply.citations}
    assert "report" in kinds
    assert "web" in kinds
    assert any("web" in c.label.lower() for c in reply.citations if c.kind == "web")
    web = next(c for c in reply.citations if c.kind == "web")
    assert web.url == REUTERS.url
    from oil_gas_analyst.turn import markdown_cite

    linked = markdown_cite(web)
    assert REUTERS.url in linked
    assert linked.startswith("[Источник:")


def test_denylist_domain_never_cited():
    reply = run_turn(
        "What's Brent today?",
            _deps(retriever=_Retr([MOMR]), dropper=_Drop(keep_all=False), web=_Web([TABLOID, REUTERS])),
    )
    labels = " ".join(c.label.lower() for c in reply.citations)
    assert "kp.ru" not in labels
    assert any(c.kind == "web" for c in reply.citations)


def test_forecast_verb_runs_both_methods_not_average():
    reply = run_turn(
        "спрогнозируй цену Brent на 3 месяца",
        _deps(retriever=_Retr([MOMR]), forecast=_Forecast(TWO_METHODS)),
    )
    assert reply.forecast_ran is True
    names = [c.label.lower() for c in reply.citations if c.kind == "forecast"]
    blob = " ".join(names)
    assert "sarima" in blob
    assert "holt" in blob
    assert "average" not in blob


def test_no_forecast_without_verb():
    reply = run_turn("What's Brent?", _deps(retriever=_Retr([MOMR]), web=_Web([REUTERS])))
    assert reply.forecast_ran is False


def test_horizon_without_verb_does_not_forecast():
    reply = run_turn("Brent in 3 months", _deps(retriever=_Retr([MOMR])))
    assert reply.forecast_ran is False


def test_urals_forecast_does_not_invent_series():
    urals = ForecastResult(symbol="Urals", methods=[], unavailable_reason="no Yahoo series in v1")
    reply = run_turn(
        "спрогнозируй Urals на 3 месяца",
        _deps(forecast=_Forecast(urals)),
    )
    assert reply.forecast_ran is True
    assert any(c.kind == "forecast" and "no" in c.label.lower() for c in reply.citations)
    assert not any(c.kind == "forecast" and "80" in c.label for c in reply.citations)


def test_forecast_failure_is_uncertainty_not_invented_price():
    reply = run_turn(
        "predict Brent",
        _deps(forecast=_Forecast(error=RuntimeError("yahoo down"))),
    )
    assert reply.forecast_ran is True
    assert "uncertain" in reply.text.lower() or "unavailable" in reply.text.lower()
    assert "80.0" not in reply.text


def test_web_citation_markdown_includes_full_url():
    from oil_gas_analyst.turn import apply_citation_links, markdown_cite

    reply = run_turn(
        "What's Brent today?",
        _deps(retriever=_Retr([MOMR]), dropper=_Drop(keep_all=False), web=_Web([REUTERS])),
    )
    web = next(c for c in reply.citations if c.kind == "web")
    assert web.url == "https://www.reuters.com/markets/brent"
    linked = markdown_cite(web)
    assert linked == "[Источник: reuters.com, web](https://www.reuters.com/markets/brent)"
    body = apply_citation_links(f"Price rose {web.label}.", [web])
    assert "https://www.reuters.com/markets/brent" in body
    assert "](https://" in body


class _BoomRetr:
    def retrieve(self, question: str, k: int = 5):
        raise OSError(111, "Connection refused")


def test_retrieve_connection_refused_still_answers_via_web():
    reply = run_turn(
        "What's Brent today?",
        _deps(retriever=_BoomRetr(), web=_Web([REUTERS])),
    )
    assert reply.refused is False
    assert reply.web_ran is True
    assert any(c.kind == "web" for c in reply.citations)
    assert "80.0" not in reply.text


def test_remote_embedding_falls_back_to_local_on_connection_refused():
    from oil_gas_analyst.retrieve import FallbackEmbeddingFunction

    class Boom:
        def __call__(self, input):
            raise OSError(111, "Connection refused")

        def embed_query(self, text: str):
            raise OSError(111, "Connection refused")

    class Local:
        def __call__(self, input):
            return [[0.1, 0.2] for _ in input]

        def embed_query(self, text: str):
            return [0.3, 0.4]

    emb = FallbackEmbeddingFunction(Boom(), lambda: Local())
    assert emb.embed_query("oil prices") == [0.3, 0.4]
    assert emb(["passage"]) == [[0.1, 0.2]]

