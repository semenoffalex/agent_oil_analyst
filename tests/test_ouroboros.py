"""Ouroboros gateway adapter: question → Reply without LangGraph."""

import json
from io import BytesIO
from urllib.error import HTTPError
from urllib.request import Request

from oil_gas_analyst.ouroboros import OuroborosLoop
from oil_gas_analyst.turn import run_turn


class _Http:
    def __init__(self, script: list[tuple[int, dict]]):
        self.script = list(script)
        self.calls: list[tuple[str, str, dict | None]] = []

    def __call__(self, req: Request, timeout=None):
        method = req.get_method()
        url = req.full_url
        body = None
        if req.data:
            body = json.loads(req.data.decode("utf-8"))
        self.calls.append((method, url, body))
        status, payload = self.script.pop(0)
        raw = json.dumps(payload).encode("utf-8")
        if status >= 400:
            raise HTTPError(url, status, "error", hdrs=None, fp=BytesIO(raw))
        return _Resp(raw)


class _Resp:
    def __init__(self, raw: bytes):
        self._raw = raw

    def read(self):
        return self._raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def test_gateway_turn_returns_task_answer(monkeypatch):
    http = _Http(
        [
            (200, {"task_id": "t-1", "status": "queued"}),
            (200, {"task_id": "t-1", "status": "running"}),
            (
                200,
                {
                    "task_id": "t-1",
                    "status": "completed",
                    "result": "OPEC demand stays at 1.4 mb/d.",
                },
            ),
        ]
    )
    monkeypatch.setattr("oil_gas_analyst.ouroboros.urlopen", http)
    loop = OuroborosLoop(base_url="http://ouroboros:8765", poll_interval=0)
    reply = run_turn("What is OPEC's 2026 world oil demand outlook?", loop)
    assert reply.text == "OPEC demand stays at 1.4 mb/d."
    assert reply.refused is False
    methods_paths = [(m, u.split("?")[0]) for m, u, _ in http.calls]
    assert methods_paths[0] == ("POST", "http://ouroboros:8765/api/tasks")
    assert http.calls[0][2]["description"] == "What is OPEC's 2026 world oil demand outlook?"
    assert http.calls[0][2]["metadata"]["source"] == "chainlit"
    assert ("GET", "http://ouroboros:8765/api/tasks/t-1") in methods_paths


def test_gateway_reads_answer_from_outcome_axes(monkeypatch):
    http = _Http(
        [
            (200, {"task_id": "t-2", "status": "queued"}),
            (
                200,
                {
                    "task_id": "t-2",
                    "status": "completed",
                    "outcome_axes": {"final_answer": "Demand 1.4 mb/d."},
                },
            ),
        ]
    )
    monkeypatch.setattr("oil_gas_analyst.ouroboros.urlopen", http)
    loop = OuroborosLoop(base_url="http://ouroboros:8765", poll_interval=0)
    reply = run_turn("outlook?", loop)
    assert reply.text == "Demand 1.4 mb/d."


def test_gateway_marks_retrieve_when_tool_name_is_in_the_task_record(monkeypatch):
    http = _Http(
        [
            (200, {"task_id": "t-3", "status": "queued"}),
            (
                200,
                {
                    "task_id": "t-3",
                    "status": "completed",
                    "result": (
                        "OPEC sees 2026 demand growth at 1.4 mb/d "
                        "[Отчёт OPEC MOMR, 2026-03, pp. 42–46 (excerpt)]."
                    ),
                    "trace_summary": "ext_18_oil_gas_retrieve_retrieve_reports",
                },
            ),
        ]
    )
    monkeypatch.setattr("oil_gas_analyst.ouroboros.urlopen", http)
    loop = OuroborosLoop(base_url="http://ouroboros:8765", poll_interval=0)
    reply = run_turn("What is OPEC's 2026 world oil demand outlook?", loop)
    assert reply.retrieved is True
    from oil_gas_analyst.turn import has_grounded_report

    assert has_grounded_report(reply) is True


def test_gateway_marks_web_when_search_tool_is_in_the_task_record(monkeypatch):
    http = _Http(
        [
            (200, {"task_id": "t-4", "status": "queued"}),
            (
                200,
                {
                    "task_id": "t-4",
                    "status": "completed",
                    "result": (
                        "OPEC kept output policy unchanged "
                        "[Источник: reuters.com, web]."
                    ),
                    "trace_summary": "ext_12_oil_gas_web_search_web",
                },
            ),
        ]
    )
    monkeypatch.setattr("oil_gas_analyst.ouroboros.urlopen", http)
    loop = OuroborosLoop(base_url="http://ouroboros:8765", poll_interval=0)
    reply = run_turn("What's the latest OPEC statement on output?", loop)
    assert reply.web_ran is True
    assert "[Источник:" in reply.text
    assert "kp.ru" not in reply.text.casefold()
    assert "dailymail" not in reply.text.casefold()


def test_gateway_marks_forecast_when_tool_is_in_the_task_record(monkeypatch):
    http = _Http(
        [
            (200, {"task_id": "t-5", "status": "queued"}),
            (
                200,
                {
                    "task_id": "t-5",
                    "status": "completed",
                    "result": (
                        "Two paths, not an average. "
                        "[Forecast sarima BZ=F 90d 74.1 (70–78)] "
                        "[Forecast holt_winters BZ=F 90d 73.2 (69–77)]."
                    ),
                    "trace_summary": "ext_16_oil_gas_forecast_run_forecast",
                },
            ),
        ]
    )
    monkeypatch.setattr("oil_gas_analyst.ouroboros.urlopen", http)
    loop = OuroborosLoop(base_url="http://ouroboros:8765", poll_interval=0)
    reply = run_turn("What's Brent in three months?", loop)
    assert reply.forecast_ran is True
    assert "[Forecast " in reply.text


def test_gateway_retries_while_supervisor_is_starting(monkeypatch):
    http = _Http(
        [
            (503, {"error": "supervisor is still starting"}),
            (200, {"task_id": "t-6", "status": "queued"}),
            (
                200,
                {
                    "task_id": "t-6",
                    "status": "completed",
                    "result": "Refused.",
                },
            ),
        ]
    )
    monkeypatch.setattr("oil_gas_analyst.ouroboros.urlopen", http)
    loop = OuroborosLoop(base_url="http://ouroboros:8765", poll_interval=0)
    reply = run_turn("what's the weather today?", loop)
    assert reply.text == "Refused."
    assert http.calls[0][0] == "POST"
