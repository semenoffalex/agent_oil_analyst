from oil_gas_analyst.eval_dialogues import README_EVAL_DIALOGUES, invoke_dashboard_eval
from oil_gas_analyst.session_start_web import SESSION_START_INJECT_HEADER, SessionStartRailHit
from oil_gas_analyst.types import LoopResult, Reply


class _FrozenLoop:
    def __init__(self):
        self.questions: list[str] = []

    def complete(self, question: str) -> LoopResult:
        self.questions.append(question)
        return LoopResult(text="ok")


def test_readme_lists_five_eval_dialogues():
    assert len(README_EVAL_DIALOGUES) == 5
    ids = {item[0] for item in README_EVAL_DIALOGUES}
    assert ids == {"report", "web", "combined", "forecast", "out_of_competence"}


def test_invoke_dashboard_eval_injects_session_start_hits():
    loop = _FrozenLoop()
    hits = [
        SessionStartRailHit(
            title="Brent rises",
            outlet="reuters.com",
            snippet="OPEC held output.",
            url="https://www.reuters.com/markets/brent",
            citation="[Источник: reuters.com, web]",
        )
    ]
    reply = invoke_dashboard_eval("Tell me about the headline.", loop, session_start_hits=hits)
    assert reply.text == "ok"
    assert SESSION_START_INJECT_HEADER in loop.questions[0]
    assert "reuters.com" in loop.questions[0]


def test_invoke_dashboard_eval_without_hits_skips_inject():
    loop = _FrozenLoop()
    invoke_dashboard_eval("What is Brent?", loop, session_start_hits=())
    assert loop.questions == ["What is Brent?"]
