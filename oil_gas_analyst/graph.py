from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from oil_gas_analyst.turn import AnalystDeps, run_turn
from oil_gas_analyst.types import Reply


class TurnState(TypedDict, total=False):
    question: str
    reply: Reply


def build_graph(deps: AnalystDeps):
    def analyst_node(state: TurnState) -> dict[str, Any]:
        return {"reply": run_turn(state["question"], deps)}

    graph = StateGraph(TurnState)
    graph.add_node("analyst", analyst_node)
    graph.add_edge(START, "analyst")
    graph.add_edge("analyst", END)
    return graph.compile()


def invoke_analyst(question: str, deps: AnalystDeps) -> Reply:
    graph = getattr(deps, "_compiled_graph", None)
    if graph is None:
        graph = build_graph(deps)
        deps._compiled_graph = graph
    out = graph.invoke({"question": question})
    return out["reply"]
