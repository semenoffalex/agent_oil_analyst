"""Live Eval dialogues on the Streamlit Dashboard seam (run_turn + Session-start Web)."""

from __future__ import annotations

from collections.abc import Sequence

from oil_gas_analyst.session_start_web import (
    SessionStartRailHit,
    fetch_session_start_web,
    visible_rail_hits,
)
from oil_gas_analyst.turn import run_turn
from oil_gas_analyst.types import AnalystLoop, Reply

# Five acceptance dialogues (README Eval table / assignment).
README_EVAL_DIALOGUES: tuple[tuple[str, str], ...] = (
    ("report", "What is OPEC's 2026 world oil demand outlook?"),
    ("web", "What's the latest OPEC statement on output?"),
    ("combined", "What's Brent today given OPEC demand?"),
    ("forecast", "спрогнозируй цену Brent на 3 месяца"),
    ("out_of_competence", "what's the weather today?"),
)


def load_session_start_hits(*, searcher=None) -> list[SessionStartRailHit]:
    return visible_rail_hits(fetch_session_start_web(searcher=searcher))


def invoke_dashboard_eval(
    question: str,
    loop: AnalystLoop,
    *,
    session_start_hits: Sequence[SessionStartRailHit] | None = None,
) -> Reply:
    """One Dashboard chat turn: Ouroboros loop plus optional Session-start Web inject."""
    hits = list(session_start_hits) if session_start_hits is not None else load_session_start_hits()
    return run_turn(question, loop, session_start_hits=hits)
