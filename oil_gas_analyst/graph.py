"""Compatibility alias. Eval and tests use the Dashboard Analyst-turn seam."""

from __future__ import annotations

from oil_gas_analyst.eval_dialogues import invoke_dashboard_eval
from oil_gas_analyst.types import AnalystLoop, Reply


def invoke_analyst(question: str, loop: AnalystLoop) -> Reply:
    """Send one question through the Streamlit Dashboard turn seam."""
    return invoke_dashboard_eval(question, loop, session_start_hits=())
