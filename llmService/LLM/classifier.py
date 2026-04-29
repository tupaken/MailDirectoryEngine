"""Inbox contact-classification orchestration."""

from ..API.LlmBackendClient import generate_prompt_response
from .json_parser import parse_first_llm_json, parse_llm_json
from .mail_preprocessing import (
    _compose_clean_mail_source,
    _split_mail_context_and_signature_segments,
    _split_mail_thread,
    _strip_mail_headers_everywhere,
)
from .normalization import (
    _dedupe_contacts,
    _extract_contacts,
    _extract_signature_contacts_from_mail,
    _extract_structured_contacts_from_mail,
    _normalize_llm_result as _normalize_llm_result_impl,
)
from .prompt_builder import _build_prompt

DISPOSITION_RELEVANT = "relevant"
DISPOSITION_IRRELEVANT = "irrelevant"
DISPOSITION_UNKNOWN = "unknown"


def _normalize_llm_result(parsed: dict, mail: str) -> dict:
    """Compatibility wrapper around normalization logic."""

    return _normalize_llm_result_impl(parsed, mail)


def _normalize_llm_contacts(parsed: dict, mail: str) -> list[dict]:
    """Normalize every parsed contact and keep only allowed entries."""

    if not isinstance(parsed, dict):
        return []

    results: list[dict] = []
    for contact in _extract_contacts(parsed):
        candidate = dict(contact)
        if "is_allowed" not in candidate:
            candidate["is_allowed"] = parsed.get("is_allowed")
        normalized = _normalize_llm_result(candidate, mail)
        if normalized.get("is_allowed") is True:
            results.append(normalized)

    return _dedupe_contacts(results)


def _attach_source_text(contacts: list[dict], source_text: str) -> list[dict]:
    """Attach the originating mail part to contacts for later scoped sync."""

    enriched: list[dict] = []
    for contact in contacts:
        candidate = dict(contact)
        existing_source = candidate.get("_source_text")
        if not isinstance(existing_source, str) or not existing_source.strip():
            candidate["_source_text"] = source_text
        enriched.append(candidate)
    return enriched


def _build_segments(mail_parts: list[str]) -> tuple[list[tuple[str, str, str]], list[str], list[str]]:
    """Build model-call segments plus deterministic extraction sources."""

    segments: list[tuple[str, str, str]] = []
    clean_mail_sources: list[str] = []
    signature_extraction_sources: list[str] = []

    for mail_part in mail_parts:
        stripped_mail_part = _strip_mail_headers_everywhere(mail_part)
        context_mail, signature_mail, signature_source_mail = (
            _split_mail_context_and_signature_segments(stripped_mail_part)
        )
        context_mail = _strip_mail_headers_everywhere(context_mail)
        signature_mail = _strip_mail_headers_everywhere(signature_mail)
        signature_source_mail = _strip_mail_headers_everywhere(signature_source_mail)
        clean_mail_source = _strip_mail_headers_everywhere(
            _compose_clean_mail_source(context_mail, signature_mail)
        )

        if clean_mail_source:
            clean_mail_sources.append(clean_mail_source)
        if signature_source_mail:
            signature_extraction_sources.append(signature_source_mail)

        segments.extend(
            [
                ("context", context_mail, context_mail),
                ("signature", signature_mail, signature_mail),
            ]
        )

    return segments, clean_mail_sources, signature_extraction_sources


def _non_empty_segments(segments: list[tuple[str, str, str]], mail: str) -> list[tuple[str, str, str]]:
    """Filter empty model-call segments with a fallback to the raw mail."""

    result = [
        (query_type, segment_mail, source_mail)
        for query_type, segment_mail, source_mail in segments
        if isinstance(segment_mail, str) and segment_mail.strip()
    ]
    return result or [("context", str(mail), str(mail))]


def _classify_model_segments(
    segments: list[tuple[str, str, str]],
) -> tuple[list[dict], int, int]:
    """Call the configured LLM for all segments and normalize accepted contacts."""

    explicit_false_count = 0
    explicit_true_count = 0
    normalized_contacts: list[dict] = []

    for query_type, segment_mail, source_mail in segments:
        raw_response = _generate_raw_response(segment_mail, query_type=query_type)
        parsed_any = parse_first_llm_json(raw_response)
        if isinstance(parsed_any, dict) and parsed_any.get("is_allowed") is False:
            explicit_false_count += 1
        if isinstance(parsed_any, dict) and parsed_any.get("is_allowed") is True:
            explicit_true_count += 1

        try:
            parsed_allowed = parse_llm_json(raw_response)
        except RuntimeError:
            parsed_allowed = {}

        normalized_contacts.extend(
            _attach_source_text(_normalize_llm_contacts(parsed_allowed, source_mail), source_mail)
        )

    return normalized_contacts, explicit_false_count, explicit_true_count


def _generate_raw_response(mail: str, query_type: str) -> str:
    """Generate one raw model response for the provided mail section."""

    prompt = _build_prompt(mail, query_type=query_type)
    return generate_prompt_response(prompt)


def _extract_deterministic_contacts(
    clean_mail_sources: list[str],
    signature_extraction_sources: list[str],
) -> list[dict]:
    """Extract contacts with regex/heuristics that do not require the LLM."""

    list_contacts: list[dict] = []
    signature_contacts: list[dict] = []

    for clean_mail_source in clean_mail_sources:
        list_contacts.extend(
            _attach_source_text(_extract_structured_contacts_from_mail(clean_mail_source), clean_mail_source)
        )
    for signature_source_mail in signature_extraction_sources:
        signature_contacts.extend(
            _attach_source_text(
                _extract_signature_contacts_from_mail(signature_source_mail),
                signature_source_mail,
            )
        )

    return list_contacts + signature_contacts


def _resolve_disposition(
    contacts: list[dict],
    explicit_false_count: int,
    explicit_true_count: int,
    segment_count: int,
) -> str:
    """Map segment results into the worker disposition contract."""

    if contacts:
        return DISPOSITION_RELEVANT
    if explicit_false_count == segment_count:
        return DISPOSITION_IRRELEVANT
    if explicit_true_count == segment_count:
        return DISPOSITION_IRRELEVANT
    return DISPOSITION_UNKNOWN


def llm_connection_with_disposition(mail: str) -> dict:
    """Return contacts plus disposition for downstream operated-flag decisions."""

    if not str(mail or "").strip():
        return {
            "contacts": [],
            "disposition": DISPOSITION_UNKNOWN,
        }

    mail_parts = _split_mail_thread(mail)
    segments, clean_mail_sources, signature_extraction_sources = _build_segments(mail_parts)
    non_empty_segments = _non_empty_segments(segments, mail)

    normalized_contacts, explicit_false_count, explicit_true_count = _classify_model_segments(
        non_empty_segments
    )
    deterministic_contacts = _extract_deterministic_contacts(
        clean_mail_sources,
        signature_extraction_sources,
    )
    contacts = _dedupe_contacts(normalized_contacts + deterministic_contacts)
    disposition = _resolve_disposition(
        contacts,
        explicit_false_count,
        explicit_true_count,
        len(non_empty_segments),
    )

    return {
        "contacts": contacts,
        "disposition": disposition,
    }


def llm_connection(mail: str) -> dict | list[dict] | None:
    """Send one mail text to configured LLM backend and return allowed result(s)."""

    decision = llm_connection_with_disposition(mail)
    contacts = decision.get("contacts", [])

    if not contacts:
        return None
    public_contacts = [
        {key: value for key, value in contact.items() if not str(key).startswith("_")}
        for contact in contacts
        if isinstance(contact, dict)
    ]
    if not public_contacts:
        return None
    if len(public_contacts) == 1:
        return public_contacts[0]
    return public_contacts


def test_connection(mail: str) -> dict | list[dict] | None:
    """Backward-compatible wrapper kept for existing callers/tests."""

    return llm_connection(mail)
