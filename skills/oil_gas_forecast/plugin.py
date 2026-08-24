"""Ouroboros extension: AutoARIMA, UnobservedComponents, and AutoReg Forecast in the same tool loop."""

from __future__ import annotations


def register(api):
    def run_forecast(ctx, query: str = ""):
        from oil_gas_analyst.forecast import forecast_for_tool

        return forecast_for_tool(query)

    api.register_tool(
        "run_forecast",
        handler=run_forecast,
        description=(
            "Oil-price Forecast: AutoARIMA, UnobservedComponents, and AutoReg with intervals. "
            "Default Brent; WTI if named; Urals has no series. Never average the methods."
        ),
        schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "User question (horizon and crude name if any).",
                }
            },
            "required": ["query"],
        },
        timeout_sec=120,
    )
