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
    EMAIL_RE,
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
    "mit freundlichem gruss",
    "mit freundlichem grusse",
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
_MAIL_HEADER_KEY_RE = re.compile(
    r"^(von|from|an|to|cc|bcc|betreff|subject|gesendet|sent|datum|date)\s*:",
    flags=re.IGNORECASE,
)
_MAIL_HEADER_LABEL_RE = re.compile(
    r"^(von|from|an|to|cc|bcc|betreff|subject|gesendet|sent|datum|date)\s*$",
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
_FORWARDED_TEXT_RE = re.compile(
    r"^(anfang der weitergeleiteten nachricht|begin forwarded message|forwarded message)\b",
    flags=re.IGNORECASE,
)

_FORWARD_INTRO_RE = re.compile(
        r"^\s*(anfang der weitergeleiteten nachricht|begin forwarded message|"
    r"-+\s*(urspruengliche nachricht|original message|weitergeleitete nachricht|forwarded message)\s*-+)\s*$",
    flags=re.IGNORECASE,
)

_REPLY_INTRO_RE = re.compile(
    r"^\s*(am\s+.+\s+schrieb|on\s+.+\s+wrote|gesendet\s+am|sent\s+on)\b",
    flags=re.IGNORECASE,
)

_QUOTE_PREFIX_RE = re.compile(r"^\s*>+(?:\s+|$)")
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
_HEADER_ARTIFACT_RE = re.compile(r"^[\s<>\"']+$")


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


def _mail_header_key(line: str) -> str:
    """Return the normalized header key for mail metadata lines."""

    normalized = _normalize_preamble_line(line)
    normalized = re.sub(r"^plain\s+", "", normalized, count=1)

    match = _MAIL_HEADER_KEY_RE.match(normalized)
    if match:
        return match.group(1)

    match = _MAIL_HEADER_LABEL_RE.match(normalized)
    if match:
        return match.group(1)

    return ""


def _is_plain_marker_line(line: str) -> bool:
    """Detect plain-text conversion markers that are not mail content."""

    return _normalize_preamble_line(line) in {"plain", "text", "plaintext"}


def _is_leading_header_artifact_line(line: str) -> bool:
    """Detect split HTML/header fragments before the actual mail body."""

    stripped = line.strip()
    if not stripped:
        return False
    if _HEADER_ARTIFACT_RE.match(stripped):
        return True
    if EMAIL_RE.search(stripped) and not _GREETING_INLINE_CONTENT_RE.search(stripped):
        without_email = EMAIL_RE.sub("", stripped).strip(" <>\"';")
        if not without_email:
            return True
    if re.fullmatch(r"[\w.+\-]+@[\w.\-]+", stripped, flags=re.IGNORECASE):
        return True
    return False


def _strip_one_header_field(lines: list[str]) -> None:
    """Remove one leading mail header field, including split continuation lines."""

    if not lines:
        return

    header_line = lines.pop(0)
    header_key = _mail_header_key(header_line)
    inline_value = header_line.split(":", 1)[1].strip() if ":" in header_line else ""
    has_inline_value = bool(inline_value and not _HEADER_ARTIFACT_RE.match(inline_value))
    if has_inline_value and header_key not in {"betreff", "subject"}:
        return

    while lines:
        next_line = lines[0].strip()
        if not next_line:
            lines.pop(0)
            break
        if _mail_header_key(next_line):
            break
        if _looks_like_greeting_line(next_line) or _is_signature_marker_line(next_line):
            break
        if _is_quoted_history_intro_line(next_line):
            break

        lines.pop(0)


def _looks_like_mail_header_line(line: str) -> bool:
    """Return True for leading mail metadata lines that should not reach the LLM."""

    normalized = _normalize_preamble_line(line)
    if not normalized:
        return False

    return bool(
        _mail_header_key(normalized)
        or _MAIL_HEADER_TEXT_RE.match(normalized)
        or _FORWARDED_HEADER_RE.match(normalized)
        or _FORWARDED_TEXT_RE.match(normalized)
    )


def _looks_like_greeting_line(line: str) -> bool:
    """Return True for a standalone greeting line, including small typos."""

    stripped = line.strip()
    if not stripped:
        return False

    normalized = _normalize_preamble_line(stripped)
    if not normalized:
        return False

    if normalized.startswith(("sehr geehrte", "sehr geehrter", "dear ")):
        return not _GREETING_INLINE_CONTENT_RE.search(normalized)

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

        if _is_plain_marker_line(line):
            lines.pop(0)
            scanned += 1
            continue

        if _is_leading_header_artifact_line(line):
            lines.pop(0)
            scanned += 1
            continue

        if _mail_header_key(line):
            _strip_one_header_field(lines)
            scanned += 1
            continue

        if _looks_like_mail_header_line(line) or _looks_like_greeting_line(line):
            lines.pop(0)
            scanned += 1
            continue

        break

    return "\n".join(lines).strip()


def _is_quoted_history_intro_line(line: str) -> bool:
    """Return True for one-line reply history markers."""

    normalized = _normalize_preamble_line(line)
    if not normalized:
        return False

    return bool(
        _FORWARDED_HEADER_RE.match(normalized)
        or _FORWARDED_TEXT_RE.match(normalized)
        or re.match(r"^am\s+.+\s+schrieb\b", normalized)
        or re.match(r"^on\s+.+\s+wrote\b", normalized)
    )


def _has_previous_content(lines: list[str]) -> bool:
    """Return True when a pending thread part already contains real text."""

    return any(line.strip() and not _is_plain_marker_line(line) for line in lines)


def _looks_like_mail_header_cluster(lines: list[str], start_idx: int) -> bool:
    """Detect a block of mail headers that starts an older quoted/forwarded mail."""

    first_line = lines[start_idx].strip() if 0 <= start_idx < len(lines) else ""
    if not _mail_header_key(first_line):
        return False

    seen_headers: set[str] = set()
    checked = 0

    for idx in range(start_idx, min(len(lines), start_idx + 8)):
        line = lines[idx].strip()
        if not line:
            continue

        header_key = _mail_header_key(line)
        if not header_key:
            continue

        checked += 1
        seen_headers.add(header_key)

    has_sender = bool({"von", "from"} & seen_headers)
    has_second_header = len(seen_headers) >= 2
    return checked >= 2 and has_sender and has_second_header


def _strip_quote_prefix(line: str) -> str:
    """Remove leading quote markers from one quoted mail-history line."""

    return re.sub(r"^\s*>+\s?", "", line)


def _is_quote_history_line(line: str, in_quoted_part: bool) -> bool:
    """Detect quoted mail-history lines without treating address brackets as quotes."""

    match = _QUOTE_PREFIX_RE.match(line)
    if not match:
        return False

    remainder = line[match.end() :].strip()
    return bool(remainder) or in_quoted_part


def _split_mail_thread(mail: str) -> list[str]:
    """Split a reply/forward chain into individual raw mail texts."""

    raw_mail = "" if mail is None else str(mail)
    lines = raw_mail.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    parts: list[str] = []
    current: list[str] = []
    in_quoted_part = False

    for idx, line in enumerate(lines):
        if _is_quoted_history_intro_line(line) and _has_previous_content(current):
            part = "\n".join(current).strip()
            if part:
                parts.append(part)
            current = []
            in_quoted_part = False
            continue

        is_quoted_line = _is_quote_history_line(line, in_quoted_part)
        if is_quoted_line and _has_previous_content(current) and not in_quoted_part:
            part = "\n".join(current).strip()
            if part:
                parts.append(part)
            current = []
            in_quoted_part = True

        if _looks_like_mail_header_cluster(lines, idx) and _has_previous_content(current):
            part = "\n".join(current).strip()
            if part:
                parts.append(part)
            current = []
            in_quoted_part = False

        if not is_quoted_line and line.strip():
            in_quoted_part = False

        current.append(_strip_quote_prefix(line) if is_quoted_line else line)

    part = "\n".join(current).strip()
    if part:
        parts.append(part)

    return parts or ([raw_mail.strip()] if raw_mail.strip() else [])


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


def _strip_signature_header_tail(lines: list[str]) -> list[str]:
    """Remove embedded reply headers that trail a signature block."""

    cleaned = list(lines)
    for idx, line in enumerate(cleaned):
        if _is_quoted_history_intro_line(line) or _mail_header_key(line):
            cleaned = cleaned[:idx]
            break

    while cleaned and re.match(r"^\s*-{5,}\s*$", cleaned[-1]):
        cleaned.pop()

    return cleaned


def _strip_signature_preamble(signature: str) -> str:
    """Strip sign-off text and direct person-name lines from a signature block."""

    raw_signature = "" if signature is None else str(signature)
    lines = raw_signature.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    while lines and not lines[0].strip():
        lines.pop(0)

    if not lines:
        return ""
    if not _is_signature_marker_line(lines[0]):
        lines = _strip_signature_header_tail(lines)
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

    lines = _strip_signature_header_tail(lines)
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


def _compose_clean_mail_source(context: str, signature: str) -> str:
    """Build the cleaned per-mail source text used for normalization and sync."""

    return "\n\n".join(
        part.strip()
        for part in (context, signature)
        if isinstance(part, str) and part.strip()
    )


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

    mail_parts = _split_mail_thread(mail)
    segments: list[tuple[str, str, str]] = []
    clean_mail_sources: list[str] = []
    for mail_part in mail_parts:
        context_mail, signature_mail = _split_mail_context_and_signature(mail_part)
        clean_mail_source = _compose_clean_mail_source(context_mail, signature_mail)
        if clean_mail_source:
            clean_mail_sources.append(clean_mail_source)
        segments.extend(
            [
                ("context", context_mail, clean_mail_source),
                ("signature", signature_mail, clean_mail_source),
            ]
        )

    non_empty_segments = [
        (query_type, segment_mail, source_mail)
        for query_type, segment_mail, source_mail in segments
        if isinstance(segment_mail, str) and segment_mail.strip()
    ]
    if not non_empty_segments:
        non_empty_segments = [("context", str(mail), str(mail))]

    explicit_false_count = 0
    explicit_true_count = 0
    normalized_contacts: list[dict] = []

    for query_type, segment_mail, source_mail in non_empty_segments:
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

        # Normalize against the current mail part so separate replies/forwards do not mix fields.
        normalized_contacts.extend(
            _attach_source_text(_normalize_llm_contacts(parsed_allowed, source_mail), source_mail)
        )

    list_contacts: list[dict] = []
    signature_contacts: list[dict] = []
    for clean_mail_source in clean_mail_sources:
        list_contacts.extend(
            _attach_source_text(_extract_structured_contacts_from_mail(clean_mail_source), clean_mail_source)
        )
        signature_contacts.extend(
            _attach_source_text(_extract_signature_contacts_from_mail(clean_mail_source), clean_mail_source)
        )
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

def _strip_mail_headers_everywhere(mail: str) -> str:
    """
    Remove transport/thread headers from a mail segment.

    Important:
    Von/From, An/To, Cc, Bcc, Betreff/Subject, Datum/Date, Gesendet/Sent
    are metadata. They must not be sent to the LLM as context or signature,
    because they cause recipient/header names to be merged with unrelated
    signature contact data.
    """

    raw_mail = "" if mail is None else str(mail)
    lines = raw_mail.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    cleaned: list[str] = []
    skipping_header_continuation = False

    for line in lines:
        stripped = line.strip()
        normalized = _normalize_preamble_line(line)

        if not stripped:
            skipping_header_continuation = False
            cleaned.append(line)
            continue

        if (
            _MAIL_HEADER_NAME_RE.match(line)
            or _FORWARD_INTRO_RE.match(normalized)
            or _REPLY_INTRO_RE.match(normalized)
        ):
            skipping_header_continuation = True
            continue

        # RFC-style folded header continuation:
        #   To: foo@example.com,
        #       bar@example.com
        # Also catches fragments created by HTML-to-text
        if skipping_header_continuation:
            if line[:1].isspace() or stripped.startswith(",") or re.search(r"<[^>]*@[^>]*$", stripped):
                continue
            skipping_header_continuation = False

        cleaned.append(line)

    result = "\n".join(cleaned)

    # Collapse excessive blank lines after header removal.
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()
