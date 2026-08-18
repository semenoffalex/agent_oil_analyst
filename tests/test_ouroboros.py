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
