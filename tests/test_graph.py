from oil_gas_analyst.graph import invoke_analyst
from oil_gas_analyst.turn import AnalystDeps, REFUSAL_TEXT
from oil_gas_analyst.types import ForecastResult


class C:
    def classify(self, question: str) -> str:
        return "out"


class R:
    def retrieve(self, question: str, k: int = 5):
        return []


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
