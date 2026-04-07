"""Canonical contact payload + HTTP client for ContactService integration."""

import json
import os
import re
from urllib import error, request

SCHEMA_VERSION = "1.0"
DEFAULT_CONTACT_SERVICE_ENDPOINT = "http://localhost:5000/api/contacts/canonical"
PHONE_RE = re.compile(r"(?:(?:\+|00)\d[\d\s()/-]{5,}\d|\b\d{6,}\b)")


def _clean_text(value: object) -> str:
    """Normalize optional values to trimmed strings."""

    if value is None:
        return ""
    return str(value).strip()


def _split_name(full_name: str) -> tuple[str, str]:
    """Split one full name into given_name and surname."""

    cleaned = _clean_text(full_name)
    if not cleaned:
        return "", ""

    parts = cleaned.split()
    if len(parts) == 1:
        return parts[0], ""

    given_name = " ".join(parts[:-1])
    surname = parts[-1]
    return given_name, surname


def _normalize_phone_e164(phone_value: str) -> str:
    """Best-effort normalization to an E.164-like string."""

    raw = _clean_text(phone_value)
    if not raw:
        return ""

    if raw.startswith("+"):
        normalized = "+" + re.sub(r"\D", "", raw[1:])
        return normalized if len(normalized) > 1 else ""

    if raw.startswith("00"):
        normalized = "+" + re.sub(r"\D", "", raw[2:])
        return normalized if len(normalized) > 1 else ""

    return ""


def _phone_digits(value: str) -> str:
    """Return numeric-only representation for deduplication."""

    return re.sub(r"\D", "", _clean_text(value))


def _normalize_phone_type(type_hint: str) -> str:
    """Map free text phone labels to canonical phone types."""

    label = _clean_text(type_hint).casefold()
    if not label:
        return "other"

    if any(token in label for token in ("telefax", "fax")):
        return "fax"
    if any(token in label for token in ("mobil", "mobile", "handy", "cell")):
        return "mobile"
    if any(token in label for token in ("home", "privat", "private")):
        return "home"
    if any(
        token in label
        for token in (
            "business",
            "work",
            "office",
            "telefon",
            "phone",
            "tel",
            "zentrale",
            "durchwahl",
            "direct",
        )
    ):
        return "business"
    return "other"


def _extract_phone_candidates_from_text(source_text: str) -> list[tuple[str, str]]:
    """Extract labeled phone-like values from source mail text."""

    candidates: list[tuple[str, str]] = []
    if not source_text:
        return candidates

    for raw_line in str(source_text).splitlines():
        line = _clean_text(raw_line)
        if not line:
            continue

        matches = PHONE_RE.findall(line)
        if not matches:
            continue

        type_hint = line
        if ":" in line:
            type_hint = line.split(":", 1)[0]
        phone_type = _normalize_phone_type(type_hint)

        for match in matches:
            phone_value = _clean_text(match)
            if phone_value:
                candidates.append((phone_type, phone_value))

    return candidates


def _collect_phone_candidates(contact: dict, source_text: str) -> list[tuple[str, str]]:
    """Collect phone candidates from normalized contact data and source text."""

    candidates: list[tuple[str, str]] = []

    def add_candidate(phone_type: str, value: object) -> None:
        raw = _clean_text(value)
        if not raw:
            return
        candidates.append((_normalize_phone_type(phone_type), raw))

    add_candidate("business", contact.get("phone"))
    add_candidate("business", contact.get("business_phone"))
    add_candidate("mobile", contact.get("mobile_phone") or contact.get("mobile"))
    add_candidate("home", contact.get("home_phone") or contact.get("home"))
    add_candidate("fax", contact.get("fax") or contact.get("telefax") or contact.get("business_fax"))

    phone_numbers = contact.get("phone_numbers")
    if isinstance(phone_numbers, dict):
        for key, value in phone_numbers.items():
            add_candidate(str(key), value)
    elif isinstance(phone_numbers, list):
        for item in phone_numbers:
            if not isinstance(item, dict):
                continue
            add_candidate(item.get("type", "other"), item.get("e164") or item.get("raw"))

    candidates.extend(_extract_phone_candidates_from_text(source_text))
    return candidates


def _dedupe_phone_candidates(candidates: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Deduplicate candidate numbers while preserving order and better labels."""

    type_priority = {"fax": 4, "mobile": 3, "home": 3, "business": 2, "other": 1}
    deduped: list[tuple[str, str]] = []
    index_by_key: dict[str, int] = {}

    for phone_type, raw in candidates:
        digits_key = _phone_digits(raw)
        dedupe_key = digits_key if digits_key else _clean_text(raw).casefold()
        if not dedupe_key:
            continue

        if dedupe_key in index_by_key:
            idx = index_by_key[dedupe_key]
            existing_type, existing_raw = deduped[idx]
            if type_priority.get(phone_type, 0) > type_priority.get(existing_type, 0):
                deduped[idx] = (phone_type, existing_raw)
            continue

        index_by_key[dedupe_key] = len(deduped)
        deduped.append((phone_type, raw))

    return deduped


def _build_phone_items(contact: dict, source_text: str) -> list[dict[str, str]]:
    """Build canonical phone objects from contact and source text candidates."""

    candidates = _collect_phone_candidates(contact, source_text)
    deduped = _dedupe_phone_candidates(candidates)

    phone_items: list[dict[str, str]] = []
    for phone_type, raw in deduped:
        item: dict[str, str] = {
            "type": phone_type,
            "raw": raw,
        }
        phone_e164 = _normalize_phone_e164(raw)
        if phone_e164:
            item["e164"] = phone_e164
        phone_items.append(item)

    return phone_items


def build_canonical_contact_payload(
    contact: dict,
    source_message_id: int | None = None,
    source_text: str | None = None,
) -> dict:
    """Map one normalized LLM contact to the shared canonical JSON schema."""

    if not isinstance(contact, dict):
        raise ValueError("contact must be a dictionary")

    full_name = _clean_text(contact.get("full_name"))
    given_name, surname = _split_name(full_name)

    phones = _build_phone_items(contact, source_text or "")
    if not phones:
        raise ValueError("contact.phone is required for canonical payload")

    notes = _clean_text(contact.get("notes"))
    account_key = _clean_text(os.getenv("EWS_ACCOUNT_KEY", "bewerbung")) or "bewerbung"

    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "account_key": account_key,
        "contact": {
            "full_name": full_name,
            "given_name": given_name,
            "surname": surname,
            "company": _clean_text(contact.get("company")),
            "email": _clean_text(contact.get("email")),
            "phones": phones,
            "address": _clean_text(contact.get("address")),
            "website": _clean_text(contact.get("website")),
            "notes": notes,
        },
    }

    if source_message_id is not None:
        payload["source_message_id"] = str(source_message_id)

    return payload


def send_canonical_contact_payload(payload: dict) -> dict:
    """Send one canonical contact payload to ContactService API."""

    endpoint = os.getenv("CONTACT_SERVICE_ENDPOINT", DEFAULT_CONTACT_SERVICE_ENDPOINT).strip()
    if not endpoint:
        raise RuntimeError("CONTACT_SERVICE_ENDPOINT is empty")

    timeout = int(os.getenv("CONTACT_SERVICE_TIMEOUT_SECONDS", "30"))
    api_key = _clean_text(os.getenv("CONTACT_SERVICE_API_KEY"))

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    req = request.Request(
        url=endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"ContactService returned HTTP {exc.code} for {endpoint}: {error_text}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach ContactService endpoint {endpoint}: {exc}") from exc

    if not response_body.strip():
        return {"status": "ok"}

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError:
        return {"status": "ok", "raw_response": response_body}

    if isinstance(parsed, dict):
        return parsed
    return {"status": "ok", "response": parsed}
