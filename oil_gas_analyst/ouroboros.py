"""HTTP adapter to a running Ouroboros gateway (not an import of the agent core)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from oil_gas_analyst.types import LoopError, LoopResult

urlopen = urllib.request.urlopen

_TERMINAL = frozenset(
    {"completed", "failed", "cancelled", "canceled", "error", "degraded"}
)


class OuroborosError(LoopError):
    """Gateway transport or empty-completion failure."""


class OuroborosLoop:
    """One Analyst turn: POST /api/tasks, wait, return the visible answer.

    Demo compose sets ``OUROBOROS_TASK_REVIEW_MODE=off`` so queued tasks do not
    run task-acceptance Review, P3, or ``/review``.
    """

    def __init__(
        self,
        base_url: str,
        *,
        poll_interval: float = 1.0,
        timeout_sec: float = 180.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.timeout_sec = timeout_sec

    def complete(self, question: str) -> LoopResult:
        created = self._request(
            "POST",
            "/api/tasks",
            {
                "description": question,
                "metadata": {"source": "chainlit", "delegation_role": "chat"},
                "source": "chainlit",
            },
        )
        task_id = str(created.get("task_id") or "")
        if not task_id:
            raise OuroborosError(f"Ouroboros task create returned no task_id: {created}")
        deadline = time.time() + self.timeout_sec
        while True:
            result = self._request("GET", f"/api/tasks/{urllib.parse.quote(task_id)}")
            if _is_terminal(result):
                text = _answer_text(result)
                if not str(text).strip():
                    raise LoopError("Ouroboros returned an empty completion.")
                return LoopResult(
                    text=str(text).strip(),
                    retrieved=_tool_ran(result, "retrieve_reports"),
                    web_ran=_tool_ran(result, "web_search") or _tool_ran(result, "search_web"),
                    forecast_ran=_tool_ran(result, "forecast"),
                    citations=_citations_from_text(str(text)),
                )
            if time.time() >= deadline:
                raise TimeoutError(
                    f"Ouroboros task {task_id} did not finish within {self.timeout_sec:g}s"
                )
            if self.poll_interval > 0:
                time.sleep(self.poll_interval)

    def _request(self, method: str, path: str, body: dict[str, Any] | None = None) -> Any:
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers=headers,
            method=method.upper(),
        )
        try:
            with urlopen(req, timeout=max(30.0, self.timeout_sec)) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            raise OuroborosError(f"HTTP {exc.code}: {raw or exc}") from exc
        except urllib.error.URLError as exc:
            raise OuroborosError(f"cannot reach Ouroboros at {self.base_url}: {exc}") from exc
        except TimeoutError as exc:
            raise LoopError(f"Ouroboros request timed out at {self.base_url}") from exc
        if not raw.strip():
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw


def _is_terminal(result: dict[str, Any]) -> bool:
    return str(result.get("status") or "").lower() in _TERMINAL


def _answer_text(result: dict[str, Any]) -> str:
    value = result.get("result")
    if isinstance(value, str) and value.strip():
        return value
    if isinstance(value, dict):
        for key in ("result", "answer", "text", "output", "final_answer"):
            inner = value.get(key)
            if isinstance(inner, str) and inner.strip():
                return inner
    axes = result.get("outcome_axes")
    if isinstance(axes, dict):
        for key in ("final_answer", "answer", "summary", "result"):
            inner = axes.get(key)
            if isinstance(inner, str) and inner.strip():
                return inner
    for key in ("answer", "text", "output"):
        inner = result.get(key)
        if isinstance(inner, str) and inner.strip():
            return inner
    return ""


def _tool_ran(payload: dict[str, Any], name: str) -> bool:
    blob = json.dumps(payload).lower()
    return name.lower() in blob


def _citations_from_text(text: str) -> list:
    import re

    from oil_gas_analyst.types import Citation

    found: list[Citation] = []
    for match in re.finditer(r"\[Отчёт [^\]]+\]", text):
        found.append(Citation(kind="report", label=match.group(0)))
    for match in re.finditer(r"\[Источник: [^\]]+\]", text):
        found.append(Citation(kind="web", label=match.group(0)))
    for match in re.finditer(r"\[Forecast [^\]]+\]", text):
        found.append(Citation(kind="forecast", label=match.group(0)))
    return found
