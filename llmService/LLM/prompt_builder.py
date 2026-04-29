"""Prompt rendering for inbox LLM queries."""

from .promtInbox import PROMPT_CONTEXT_TEMPLATE, PROMPT_SIGNATURE_TEMPLATE


def _build_prompt(mail: str, query_type: str) -> str:
    """Render query-specific prompt with one mail payload."""

    if query_type == "context":
        return PROMPT_CONTEXT_TEMPLATE.format(mail=mail)
    if query_type == "signature":
        return PROMPT_SIGNATURE_TEMPLATE.format(mail=mail)
    raise ValueError(f"Unsupported prompt query_type: {query_type}")
