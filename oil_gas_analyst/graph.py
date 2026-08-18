"""Compatibility alias. The conversation path is the Ouroboros loop, not LangGraph."""

from __future__ import annotations

from oil_gas_analyst.turn import run_turn
from oil_gas_analyst.types import AnalystLoop, Reply


def invoke_analyst(question: str, loop: AnalystLoop) -> Reply:
    """Send one question through the Analyst turn seam.

    Args:
        question: User question.
        loop: Ouroboros gateway or a frozen test double.

    Returns:
        Same ``Reply`` as ``run_turn``.
    """
    return run_turn(question, loop)
