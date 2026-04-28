"""LLM transport + orchestration entrypoint for inbox classification."""

import json
import os
import re
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv
from ollama import Client
try:
    from rapidfuzz import fuzz
except ImportError:  # pragma: no cover - dependency fallback for minimal test envs
    fuzz = None

from .json_parser import parse_first_llm_json, parse_llm_json
from .normalization import (
    _dedupe_contacts,
    _extract_contacts,
    _extract_signature_contacts_from_mail,
    _extract_structured_contacts_from_mail,
    _normalize_llm_result as _normalize_llm_result_impl,
)
from .promtInbox import PROMPT_CONTEXT_TEMPLATE, PROMPT_SIGNATURE_TEMPLATE
from .patterns import GREETING_PATTERNS

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH if ENV_PATH.exists() else None)

DISPOSITION_RELEVANT = "relevant"
DISPOSITION_IRRELEVANT = "irrelevant"
DISPOSITION_UNKNOWN = "unknown"

_SIGNATURE_SIGNOFF_MARKERS = (
    "mit freundlichen gruessen",
    "freundliche gruesse",
    "beste gruesse",
    "viele gruesse",
    "best regards",
    "kind regards",
    "regards",
    "mfg",
)
_SIGNATURE_CONTACT_HINT_RE = re.compile(
    r"(telefon|tel\.?|telefax|fax|mobil|handy|durchwahl|e-?mail|web|www\.|http|gmbh|\bag\b|\bug\b|\bkg\b|str\.|stra[sz]e|adresse|hrb|ust)",
    flags=re.IGNORECASE,
)
_SIGNATURE_NAME_HINT_RE = re.compile(
    r"[A-Z\u00c4\u00d6\u00dc][A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df'`\-\.]+"
    r"\s+[A-Z\u00c4\u00d6\u00dc][A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df'`\-\.]+"
)
_MAIL_PREAMBLE_SCAN_LIMIT = 20
_MAIL_HEADER_RE = re.compile(
    r"^(von|from|an|to|cc|bcc|betreff|subject|gesendet|sent|datum|date)\s*:",
    flags=re.IGNORECASE,
)
_MAIL_HEADER_TEXT_RE = re.compile(
    r"^(gesendet\s+am|sent\s+on|am\s+.+\s+schrieb|on\s+.+\s+wrote)\b",
    flags=re.IGNORECASE,
)
_FORWARDED_HEADER_RE = re.compile(
    r"^-+\s*(urspruengliche nachricht|original message|weitergeleitete nachricht|forwarded message)\s*-+$",
    flags=re.IGNORECASE,
)
_GREETING_INLINE_CONTENT_RE = re.compile(
    r"\b(bitte|ich|wir|du|sie|kannst|koennen|koennten|anbei|wegen|bezueglich|"
    r"please|we|i|you|can|could|attached|regarding)\b",
    flags=re.IGNORECASE,
)
_FUZZY_GREETING_CANDIDATES = (
    "hallo",
    "guten tag",
    "guten morgen",
    "guten abend",
    "sehr geehrte damen und herren",
    "hello",
    "dear sir or madam",
    "to whom it may concern",
)


def _ascii_fold(value: str) -> str:
    """Fold German umlauts/eszett for robust marker matching."""

    folded = value.translate(
        str.maketrans(
            {
                "\u00e4": "ae",
                "\u00f6": "oe",
                "\u00fc": "ue",
                "\u00c4": "Ae",
                "\u00d6": "Oe",
                "\u00dc": "Ue",
                "\u00df": "ss",
            }
        )
    )
    return folded.casefold()


def _is_signature_marker_line(line: str) -> bool:
    """Check whether one line looks like a signature sign-off marker."""

    stripped = line.strip()
    if not stripped:
        return False
    if stripped in {"--", "---", "__", "___"}:
        return True

    normalized = _ascii_fold(stripped)
    return any(normalized.startswith(marker) for marker in _SIGNATURE_SIGNOFF_MARKERS)


def _infer_signature_start(lines: list[str]) -> int | None:
    """Infer signature start from bottom contact hints when no sign-off was found."""

    if len(lines) < 4:
        return None

    start_scan = max(0, len(lines) - 14)
    for idx in range(start_scan, len(lines)):
        tail_lines = [line.strip() for line in lines[idx:] if line.strip()]
        if len(tail_lines) < 3:
            continue

        hint_count = sum(1 for line in tail_lines if _SIGNATURE_CONTACT_HINT_RE.search(line))
        if hint_count < 2:
            continue

        head_window = tail_lines[:4]
        has_name_hint = any(_SIGNATURE_NAME_HINT_RE.search(line) for line in head_window)
        if has_name_hint or hint_count >= 3:
            return idx

    return None


def _normalize_preamble_line(line: str) -> str:
    """Normalize one line for mail preamble detection."""

    normalized = _ascii_fold(line)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized.strip(" \t,.;:!?")


def _fuzzy_ratio(value: str, candidate: str) -> float:
    """Compare greeting text while keeping rapidfuzz optional for local tests."""

    if fuzz is not None:
        return fuzz.ratio(value, candidate)

    from difflib import SequenceMatcher

    return SequenceMatcher(None, value, candidate).ratio() * 100


def _looks_like_mail_header_line(line: str) -> bool:
    """Return True for leading mail metadata lines that should not reach the LLM."""

    normalized = _normalize_preamble_line(line)
    if not normalized:
        return False

    return bool(
        _MAIL_HEADER_RE.match(normalized)
        or _MAIL_HEADER_TEXT_RE.match(normalized)
        or _FORWARDED_HEADER_RE.match(normalized)
    )


def _looks_like_greeting_line(line: str) -> bool:
    """Return True for a standalone greeting line, including small typos."""

    stripped = line.strip()
    if not stripped:
        return False

    normalized = _normalize_preamble_line(stripped)
    if not normalized:
        return False

    # If text follows a comma on the same line, keep the line to avoid dropping content.
    comma_index = normalized.find(",")
    if comma_index != -1 and comma_index < len(normalized.rstrip(",")) - 1:
        return False

    words = normalized.split()
    if len(words) > 9 or len(normalized) > 120:
        return False

    if _GREETING_INLINE_CONTENT_RE.search(normalized):
        return False

    if any(re.match(pattern, normalized) for pattern in GREETING_PATTERNS):
        return True

    return any(
        _fuzzy_ratio(normalized, candidate) >= 85
        for candidate in _FUZZY_GREETING_CANDIDATES
    )


def _strip_mail_preamble(mail: str) -> str:
    """Strip leading mail headers and greeting lines from a context section."""

    raw_mail = "" if mail is None else str(mail)
    lines = raw_mail.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    while lines and not lines[0].strip():
        lines.pop(0)

    scanned = 0
    while lines and scanned < _MAIL_PREAMBLE_SCAN_LIMIT:
        line = lines[0].strip()

        if not line:
            lines.pop(0)
            scanned += 1
            continue

        if _looks_like_mail_header_line(line) or _looks_like_greeting_line(line):
            lines.pop(0)
            scanned += 1
            continue

        break

    return "\n".join(lines).strip()


def _looks_like_signature_name_line(line: str) -> bool:
    """Return True for person-name lines directly after a sign-off marker."""

    stripped = line.strip()
    if not stripped:
        return False

    if _SIGNATURE_CONTACT_HINT_RE.search(stripped):
        return False

    normalized = _ascii_fold(stripped)
    normalized = re.sub(
        r"^(i\.?\s*a\.?|i\.?\s*v\.?|im\s+auftrag|ppa\.?|pp\.?|herr|frau|hr|fr|"
        r"dr\.?|prof\.?|dipl\.?(?:-|\s*)ing\.?)\s+",
        "",
        normalized,
    ).strip(" ,;:-")

    if not normalized:
        return False

    return bool(_SIGNATURE_NAME_HINT_RE.search(stripped) or _SIGNATURE_NAME_HINT_RE.search(normalized))


def _strip_signature_preamble(signature: str) -> str:
    """Strip sign-off text and direct person-name lines from a signature block."""

    raw_signature = "" if signature is None else str(signature)
    lines = raw_signature.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    while lines and not lines[0].strip():
        lines.pop(0)

    if not lines or not _is_signature_marker_line(lines[0]):
        return "\n".join(lines).strip()

    lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)

    removed_name_lines = 0
    while lines and removed_name_lines < 3 and _looks_like_signature_name_line(lines[0]):
        lines.pop(0)
        removed_name_lines += 1
        while lines and not lines[0].strip():
            lines.pop(0)

    return "\n".join(lines).strip()


def _split_mail_context_and_signature(mail: str) -> tuple[str, str]:
    """Split one mail into context and signature sections for separate model calls."""

    raw_mail = "" if mail is None else str(mail)
    normalized_mail = raw_mail.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized_mail.strip():
        return "", ""

    lines = normalized_mail.split("\n")

    signature_start: int | None = None
    for idx, line in enumerate(lines):
        if _is_signature_marker_line(line):
            signature_start = idx
            break

    if signature_start is None:
        signature_start = _infer_signature_start(lines)

    if signature_start is None:
        return _strip_mail_preamble(normalized_mail), ""

    context = "\n".join(lines[:signature_start]).strip()
    signature = "\n".join(lines[signature_start:]).strip()
    context = _strip_mail_preamble(context)
    signature = _strip_signature_preamble(signature)

    if not signature:
        return _strip_mail_preamble(normalized_mail), ""
    return context, signature


def _build_prompt(mail: str, query_type: str) -> str:
    """Render query-specific prompt with one mail payload."""

    if query_type == "context":
        return PROMPT_CONTEXT_TEMPLATE.format(mail=mail)
    if query_type == "signature":
        return PROMPT_SIGNATURE_TEMPLATE.format(mail=mail)
    raise ValueError(f"Unsupported prompt query_type: {query_type}")


def _ollama_generate(prompt: str) -> str:
    """Call Ollama generate endpoint and return raw model text."""

    host = os.getenv("LLM_ENDPOINT", "http://localhost:11434")
    model = os.getenv("LLM_MODEL", "llama3.2:1b")
    client = Client(host=host)
    response = client.generate(model=model, prompt=prompt)
    return response["response"]


def _llamacpp_generate(prompt: str) -> str:
    """Call llama.cpp OpenAI-compatible endpoint and return raw model text."""

    endpoint = os.getenv("LLM_ENDPOINT", "http://localhost:8080").rstrip("/")
    model = os.getenv("LLM_MODEL", "")
    request_url = (
        f"{endpoint}/chat/completions"
        if endpoint.endswith("/v1")
        else f"{endpoint}/v1/chat/completions"
    )

    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    if model:
        payload["model"] = model

    req = request.Request(
        url=request_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw_response = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach llama.cpp endpoint at {request_url}: {exc}") from exc

    try:
        return raw_response["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise RuntimeError("llama.cpp response format is invalid.") from exc


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


def _generate_raw_response(mail: str, query_type: str) -> str:
    """Generate one raw model response for the provided mail section."""

    prompt = _build_prompt(mail, query_type=query_type)
    backend = os.getenv("LLM_BACKEND", "ollama").strip().lower().replace("-", "_")

    if backend == "ollama":
        return _ollama_generate(prompt)
    if backend in {"llama_cpp", "llama.cpp", "llamacpp"}:
        return _llamacpp_generate(prompt)

    raise ValueError(
        "Unsupported LLM_BACKEND. Use one of: ollama, llama_cpp, llama.cpp, llamacpp."
    )


def llm_connection_with_disposition(mail: str) -> dict:
    """Return contacts plus disposition for downstream operated-flag decisions."""

    if not str(mail or "").strip():
        return {
            "contacts": [],
            "disposition": DISPOSITION_UNKNOWN,
        }

    context_mail, signature_mail = _split_mail_context_and_signature(mail)
    segments = [
        ("context", context_mail),
        ("signature", signature_mail),
    ]
    non_empty_segments = [
        (query_type, segment_mail)
        for query_type, segment_mail in segments
        if isinstance(segment_mail, str) and segment_mail.strip()
    ]
    if not non_empty_segments:
        non_empty_segments = [("context", context_mail)]

    explicit_false_count = 0
    explicit_true_count = 0
    normalized_contacts: list[dict] = []

    for query_type, segment_mail in non_empty_segments:
        raw_response = _generate_raw_response(segment_mail, query_type=query_type)
        parsed_any = parse_first_llm_json(raw_response)
        if isinstance(parsed_any, dict) and parsed_any.get("is_allowed") is False:
            explicit_false_count += 1
        if isinstance(parsed_any, dict) and parsed_any.get("is_allowed") is True:
            explicit_true_count += 1

        parsed_allowed: dict = {}
        try:
            parsed_allowed = parse_llm_json(raw_response)
        except RuntimeError:
            parsed_allowed = {}

        # Normalize against the full mail text so context/signature fields can complement each other.
        normalized_contacts.extend(_normalize_llm_contacts(parsed_allowed, mail))

    list_contacts = _extract_structured_contacts_from_mail(mail)
    signature_contacts = _extract_signature_contacts_from_mail(mail)
    contacts = _dedupe_contacts(normalized_contacts + list_contacts + signature_contacts)

    if contacts:
        disposition = DISPOSITION_RELEVANT
    elif explicit_false_count == len(non_empty_segments):
        disposition = DISPOSITION_IRRELEVANT
    elif explicit_true_count == len(non_empty_segments):
        # Model allowed every segment but normalization rejected all candidate fields.
        # Treat as final non-actionable result instead of retrying forever as unknown.
        disposition = DISPOSITION_IRRELEVANT
    else:
        disposition = DISPOSITION_UNKNOWN

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
    if len(contacts) == 1:
        return contacts[0]
    return contacts


def test_connection(mail: str) -> dict | list[dict] | None:
    """Backward-compatible wrapper kept for existing callers/tests."""

    return llm_connection(mail)
