from oil_gas_analyst.graph import invoke_analyst
from oil_gas_analyst.turn import AnalystDeps, REFUSAL_TEXT
from oil_gas_analyst.types import Chunk, ForecastResult, MethodForecast


OIL = Chunk(
    text="The global oil demand growth forecast for 2026 remains at 1.4 mb/d.",
    title="OPEC MOMR",
    date="2026-03",
    page_start=42,
    page_end=46,
    heading="World Oil Demand",
)


class Cin:
    def classify(self, question: str) -> str:
        return "in"


class C:
    def classify(self, question: str) -> str:
        return "out"


class R:
    def retrieve(self, question: str, k: int = 5):
        return []


class Roil:
    def retrieve(self, question: str, k: int = 5):
        return [OIL]


class D:
    def keep(self, question: str, chunks):
        return chunks


class W:
    def search(self, question: str):
        return []


class F:
    def forecast(self, question: str) -> ForecastResult:
        raise AssertionError("no forecast")


class P:
    def compose(self, question: str, **kwargs) -> str:
        return "x"


def test_graph_same_refuse_as_run_turn():
    deps = AnalystDeps(
        classifier=C(),
        retriever=R(),
        dropper=D(),
        web=W(),
        forecast=F(),
        composer=P(),
        denied_domains=[],
    )
    reply = invoke_analyst("what's the weather today?", deps)
    assert reply.refused is True
    assert reply.text == REFUSAL_TEXT


def test_invoke_analyst_reuses_compiled_graph():
    deps = AnalystDeps(
        classifier=C(),
        retriever=R(),
        dropper=D(),
        web=W(),
        forecast=F(),
        composer=P(),
        denied_domains=[],
    )
    first = invoke_analyst("what's the weather today?", deps)
    graph = getattr(deps, "_compiled_graph", None)
    second = invoke_analyst("what's the weather today?", deps)
    assert first.refused is True
    assert second.refused is True
    assert graph is not None
    assert getattr(deps, "_compiled_graph") is graph


def _in_deps(**kwargs) -> AnalystDeps:
    return AnalystDeps(
        classifier=kwargs.get("classifier", Cin()),
        retriever=kwargs.get("retriever", Roil()),
        dropper=D(),
        web=W(),
        forecast=kwargs.get("forecast", F()),
        composer=P(),
        denied_domains=[],
    )


def test_refused_graph_stops_after_classify():
    reply = invoke_analyst(
        "what's the weather today?",
        AnalystDeps(
            classifier=C(),
            retriever=R(),
            dropper=D(),
            web=W(),
            forecast=F(),
            composer=P(),
            denied_domains=[],
        ),
    )
    assert reply.refused is True
    assert reply.steps == ["classify"]


def test_report_only_graph_skips_tools():
    reply = invoke_analyst("What is OPEC's 2026 world oil demand outlook?", _in_deps())
    assert reply.refused is False
    assert reply.web_ran is False
    assert reply.forecast_ran is False
    assert reply.steps == ["classify", "retrieve", "drop", "compose"]


def test_forecast_graph_runs_tools_node():
    result = ForecastResult(
        symbol="BZ=F",
        methods=[
            MethodForecast(name="sarima", point=80.0, low=70.0, high=90.0, interpretation="x"),
            MethodForecast(name="holt_winters", point=81.0, low=72.0, high=91.0, interpretation="x"),
        ],
        horizon_days=90,
    )

    class Fc:
        def forecast(self, question: str) -> ForecastResult:
            return result

    reply = invoke_analyst("спрогнозируй цену Brent на 3 месяца", _in_deps(forecast=Fc()))
    assert reply.forecast_ran is True
    assert reply.steps == ["classify", "retrieve", "drop", "tools", "compose"]
