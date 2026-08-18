"""Ouroboros extension: Report retrieve in the same tool loop as the solve model."""

from __future__ import annotations


def register(api):
    def retrieve_reports(ctx, query: str = ""):
        from oil_gas_analyst.retrieve import retrieve_for_tool

        return retrieve_for_tool(query)

    api.register_tool(
        "retrieve_reports",
        handler=retrieve_reports,
        description=(
            "Retrieve Report chunks from the OPEC/EIA/CBR corpus (e5 + Chroma). "
            "Call for in-Competence oil/gas questions. Returns citation labels to copy verbatim."
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
        timeout_sec=120,
    )
