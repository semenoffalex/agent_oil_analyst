from __future__ import annotations

from oil_gas_analyst.turn import apply_citation_links, footer_flags, markdown_cite
from oil_gas_analyst.types import Reply


def format_reply(reply: Reply) -> str:
    """Render chat message: linked body, Sources list, and footer flags."""
    parts = [apply_citation_links(reply.text.strip(), reply.citations)]
    if reply.citations:
        parts.append("\n**Sources**")
        parts.extend(f"- {markdown_cite(c)}" for c in reply.citations)
    flags = footer_flags(reply)
    if flags:
        parts.append("\n_" + " · ".join(flags) + "_")
    return "\n".join(parts)
