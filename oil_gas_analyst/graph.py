from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from oil_gas_analyst.turn import (
    AnalystDeps,
    TurnCtx,
    finish_compose,
    finish_refuse,
    needs_tools,
    new_turn,
    step_classify,
    step_compose,
    step_drop,
    step_retrieve,
    step_tools,
)
from oil_gas_analyst.types import Reply


class TurnState(TypedDict, total=False):
    question: str
    ctx: TurnCtx
    reply: Reply


def build_graph(deps: AnalystDeps):
    def classify_node(state: TurnState) -> dict[str, Any]:
        ctx = new_turn(state["question"], deps)
        step_classify(ctx)
        patch: dict[str, Any] = {"ctx": ctx}
        if ctx.refused:
            patch["reply"] = finish_refuse(ctx)
        return patch

    def retrieve_node(state: TurnState) -> dict[str, Any]:
        ctx = state["ctx"]
        step_retrieve(ctx)
        return {"ctx": ctx}

    def drop_node(state: TurnState) -> dict[str, Any]:
        ctx = state["ctx"]
        step_drop(ctx)
        return {"ctx": ctx}

    def tools_node(state: TurnState) -> dict[str, Any]:
        ctx = state["ctx"]
        step_tools(ctx)
        return {"ctx": ctx}

    def compose_node(state: TurnState) -> dict[str, Any]:
        ctx = state["ctx"]
        step_compose(ctx)
        return {"ctx": ctx, "reply": finish_compose(ctx)}

    def after_classify(state: TurnState) -> str:
        return END if state["ctx"].refused else "retrieve"

    def after_drop(state: TurnState) -> str:
        return "tools" if needs_tools(state["ctx"]) else "compose"

    graph = StateGraph(TurnState)
    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("drop", drop_node)
    graph.add_node("tools", tools_node)
    graph.add_node("compose", compose_node)
    graph.add_edge(START, "classify")
    graph.add_conditional_edges("classify", after_classify)
    graph.add_edge("retrieve", "drop")
    graph.add_conditional_edges("drop", after_drop)
    graph.add_edge("tools", "compose")
    graph.add_edge("compose", END)
    return graph.compile()


def invoke_analyst(question: str, deps: AnalystDeps) -> Reply:
    graph = getattr(deps, "_compiled_graph", None)
    if graph is None:
        graph = build_graph(deps)
        deps._compiled_graph = graph
    out = graph.invoke({"question": question})
    return out["reply"]
