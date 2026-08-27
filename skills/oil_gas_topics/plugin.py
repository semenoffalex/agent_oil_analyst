"""Ouroboros extension: 30-day Reddit oil-topic overview from the Dashboard cache."""

from __future__ import annotations


def register(api):
    def oil_gas_topics(ctx):
        from oil_gas_analyst.topic_dynamics import topics_for_tool

        return topics_for_tool()

    api.register_tool(
        "oil_gas_topics",
        handler=oil_gas_topics,
        description=(
            "Overview of oil-related Reddit topics for the last 30 Moscow days: "
            "Russian labels, comment-volume dynamics, and a few headlines. "
            "Not prices. Do not invent topics if the cache is empty."
        ),
        schema={"type": "object", "properties": {}, "required": []},
        timeout_sec=30,
    )
