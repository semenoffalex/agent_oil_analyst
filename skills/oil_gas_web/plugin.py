"""Ouroboros extension: DuckDuckGo Web search in the same tool loop as the solve model."""

from __future__ import annotations


def register(api):
    def search_web(ctx, query: str = ""):
        from oil_gas_analyst.web import search_for_tool

        return search_for_tool(query)

    api.register_tool(
        "search_web",
        handler=search_web,
        description=(
            "Search the open Web (DuckDuckGo) for oil/gas news and live quotes. "
            "Returns citation labels. Do not cite hits marked denied (Yellow-press)."
        ),
        schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query. English is fine for a Russian user question.",
                }
            },
            "required": ["query"],
        },
        timeout_sec=60,
    )
