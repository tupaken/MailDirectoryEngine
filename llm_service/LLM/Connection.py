"""LLM prompt wrapper used to classify inbox text payloads."""

import ast
import json
import os
import re
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv
from ollama import Client

from .promtInbox import PROMPT_TEMPLATE

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH if ENV_PATH.exists() else None)

ALLOWED_FIELDS = ("full_name", "company", "email", "phone", "address", "website")
PLACEHOLDER_RE = re.compile(r"\b(test\d*|demo|sample|dummy|example)\b", re.IGNORECASE)
ROLE_TITLE_PART = r"(?:geschaeftsfuehrer(?:in)?|ceo|inhaber|vorstand|gf)"
PHONE_RE = re.compile(r"(?:(?:\+|00)\d[\d\s()/-]{5,}\d|\b\d{6,}\b)")
EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)
NAME_RE = re.compile(
    r"([A-Z\u00c4\u00d6\u00dc][a-z\u00e4\u00f6\u00fc\u00df]+(?:[-'][A-Z\u00c4\u00d6\u00dc]?[a-z\u00e4\u00f6\u00fc\u00df]+)?"
    r"(?:\s+[A-Z\u00c4\u00d6\u00dc][a-z\u00e4\u00f6\u00fc\u00df]+(?:[-'][A-Z\u00c4\u00d6\u00dc]?[a-z\u00e4\u00f6\u00fc\u00df]+)?){1,2})"
)
NAME_RE_ALL_CAPS = re.compile(r"([A-Z\u00c4\u00d6\u00dc]{2,}(?:\s+[A-Z\u00c4\u00d6\u00dc]{2,}){1,2})")
CONTACT_LIST_LINE_RE = re.compile(
    r"(?P<company>[^\n;]+?)\s*[-\u2013\u2014]\s*"
    r"(?P<full_name>[A-Z\u00c4\u00d6\u00dc][\w'`\-]+(?:\s+[A-Z\u00c4\u00d6\u00dc][\w'`\-]+){1,2})\s*;\s*"
    r"(?P<phone>(?:(?:\+|00)\d[\d\s()/-]{5,}\d|\b\d{6,}\b))"
    r"(?:\s*;\s*(?P<email>[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}))?",
    flags=re.IGNORECASE,
)
BUSINESS_LINE_HINTS = (
    "telefon",
    "telefax",
    "fax",
    "e-mail",
    "email",
    "web",
    "www",
    "gmbh",
    " ag ",
    " ug ",
    " kg ",
    "e.v",
    "strasse",
    "straße",
    "gesellschaft",
    "sitz",
    "handelsregister",
    "betriebsnummer",
    "amtsgericht",
    "hrb",
    "ust",
)


def _build_prompt(mail: str) -> str:
    """Render the inbox classification prompt with one mail payload."""

    return PROMPT_TEMPLATE.format(mail=mail)


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


def llm_connection(mail: str) -> dict | list[dict] | None:
    """Send one mail text to configured LLM backend and return allowed result(s)."""

    prompt = _build_prompt(mail)
    backend = os.getenv("LLM_BACKEND", "ollama").strip().lower().replace("-", "_")

    if backend == "ollama":
        raw_response = _ollama_generate(prompt)
    elif backend in {"llama_cpp", "llama.cpp", "llamacpp"}:
        raw_response = _llamacpp_generate(prompt)
    else:
        raise ValueError(
            "Unsupported LLM_BACKEND. Use one of: ollama, llama_cpp, llama.cpp, llamacpp."
        )

    parsed: dict = {}
    try:
        parsed = parse_llm_json(raw_response)
    except RuntimeError:
        parsed = {}

    normalized_contacts = _normalize_llm_contacts(parsed, mail)
    list_contacts = _extract_structured_contacts_from_mail(mail)
    contacts = _dedupe_contacts(normalized_contacts + list_contacts)

    if not contacts:
        return None
    if len(contacts) == 1:
        return contacts[0]
    return contacts


def test_connection(mail: str) -> dict | list[dict] | None:
    """Backward-compatible wrapper kept for existing callers/tests."""

    return llm_connection(mail)


def _clean_text(value: object) -> str:
    """Convert any value to normalized single-line text."""

    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _is_placeholder(value: str) -> bool:
    """Return True when a value looks like test/demo placeholder content."""

    return bool(PLACEHOLDER_RE.search(value))


def _normalize_website(value: str) -> str:
    """Normalize a website to a bare lowercase host for text matching."""

    website = value.strip().lower()
    website = re.sub(r"^https?://", "", website)
    website = website.split("/", 1)[0]
    if website.startswith("www."):
        website = website[4:]
    return website


def _ascii_fold(value: str) -> str:
    """Fold German umlauts/eszett to ASCII-compatible comparison form."""

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


def _is_role_based_name(name: str, mail: str) -> bool:
    """Detect names that only appear in management-role context."""

    folded_mail = _ascii_fold(mail)
    escaped_name = re.escape(_ascii_fold(name))
    left_context = rf"{ROLE_TITLE_PART}[^\n\r]{{0,40}}{escaped_name}"
    right_context = rf"{escaped_name}[^\n\r]{{0,40}}{ROLE_TITLE_PART}"
    return bool(re.search(left_context, folded_mail)) or bool(
        re.search(right_context, folded_mail)
    )


def _value_in_mail(field: str, value: str, mail: str) -> bool:
    """Check whether one extracted field value is explicitly present in mail text."""

    if not value:
        return False

    value_lower = value.casefold()
    mail_lower = mail.casefold()

    if field == "phone":
        value_digits = re.sub(r"\D", "", value)
        mail_digits = re.sub(r"\D", "", mail)
        return len(value_digits) >= 6 and value_digits in mail_digits

    if field == "website":
        normalized = _normalize_website(value)
        return bool(normalized) and normalized in mail_lower

    return value_lower in mail_lower


def _looks_like_person_name_line(line: str) -> bool:
    """Heuristically validate whether a line resembles a real person name."""

    candidate = _clean_text(line).strip(" ,;:-")
    if not candidate:
        return False
    if ":" in candidate:
        return False
    if any(ch.isdigit() for ch in candidate):
        return False

    folded = _ascii_fold(f" {candidate} ")
    if any(hint in folded for hint in BUSINESS_LINE_HINTS):
        return False

    return bool(NAME_RE.fullmatch(candidate) or NAME_RE_ALL_CAPS.fullmatch(candidate))


def _phone_digits(value: str) -> str:
    """Return only digit characters from one phone-like value."""

    return re.sub(r"\D", "", value or "")


def _extract_name_from_phone_line(line: str) -> str:
    """Extract a person-like name from one line that also contains a phone number."""

    cleaned_line = _clean_text(line)
    if not cleaned_line or not PHONE_RE.search(cleaned_line):
        return ""

    # Common contact-list format: "Company - First Last; +49 ...; mail@company.de"
    dash_match = re.search(
        r"[-\u2013\u2014]\s*"
        r"([A-Z\u00c4\u00d6\u00dc][\w'`\-]+(?:\s+[A-Z\u00c4\u00d6\u00dc][\w'`\-]+){1,2})"
        r"\s*(?=;|,|$)",
        cleaned_line,
    )
    if dash_match:
        candidate = _clean_text(dash_match.group(1)).strip(" ,;:-")
        if _looks_like_person_name_line(candidate):
            return candidate

    phone_match = PHONE_RE.search(cleaned_line)
    if not phone_match:
        return ""
    before_phone = cleaned_line[: phone_match.start()].strip(" ,;:-")
    if not before_phone:
        return ""

    labeled_match = re.search(
        r"(?:contact|kontakt|ansprechpartner|name)\s*[:\-]\s*"
        r"([A-Z\u00c4\u00d6\u00dc][\w'`\-]+(?:\s+[A-Z\u00c4\u00d6\u00dc][\w'`\-]+){1,2})$",
        before_phone,
        flags=re.IGNORECASE,
    )
    if labeled_match:
        candidate = _clean_text(labeled_match.group(1)).strip(" ,;:-")
        if _looks_like_person_name_line(candidate):
            return candidate

    if ";" in before_phone:
        parts = [part.strip(" ,;:-") for part in before_phone.split(";") if part.strip(" ,;:-")]
        if parts:
            before_phone = parts[-1]

    dash_parts = [
        part.strip(" ,;:-")
        for part in re.split(r"\s[-\u2013\u2014]\s", before_phone)
        if part.strip(" ,;:-")
    ]
    if dash_parts:
        before_phone = dash_parts[-1]

    if _looks_like_person_name_line(before_phone):
        return before_phone

    inline_names = NAME_RE.findall(cleaned_line)
    for candidate in reversed(inline_names):
        candidate = _clean_text(candidate).strip(" ,;:-")
        if _looks_like_person_name_line(candidate):
            return candidate

    return ""


def _extract_name_from_mail(mail: str, phone: str = "") -> str:
    """Infer contact name from labels, phone context, or signature fallback."""

    lines = [_clean_text(line) for line in mail.splitlines() if _clean_text(line)]
    if not lines:
        return ""

    # Prefer explicitly labeled contact names.
    labeled_pattern = re.compile(
        r"(?:contact|kontakt|ansprechpartner|name)\s*[:\-]\s*"
        r"([A-Z\u00c4\u00d6\u00dc][\w'`\-]+(?:\s+[A-Z\u00c4\u00d6\u00dc][\w'`\-]+){1,2})",
        flags=re.IGNORECASE,
    )
    for line in lines:
        match = labeled_pattern.search(line)
        if not match:
            continue
        candidate = _clean_text(match.group(1))
        if _looks_like_person_name_line(candidate) and not _is_role_based_name(candidate, mail):
            return candidate

    # Best effort: extract from the phone line itself or nearest valid name line above it.
    target_phone_digits = _phone_digits(phone)
    phone_indexes = []
    for idx, line in enumerate(lines):
        if not PHONE_RE.search(line):
            continue
        if target_phone_digits and target_phone_digits not in _phone_digits(line):
            continue
        phone_indexes.append(idx)

    if not phone_indexes:
        phone_indexes = [idx for idx, line in enumerate(lines) if PHONE_RE.search(line)]

    for phone_idx in phone_indexes:
        inline_candidate = _extract_name_from_phone_line(lines[phone_idx])
        if inline_candidate and not _is_role_based_name(inline_candidate, mail):
            return inline_candidate

        start = max(0, phone_idx - 16)
        for line_idx in range(phone_idx - 1, start - 1, -1):
            candidate = lines[line_idx].strip(" ,;:-")
            if not _looks_like_person_name_line(candidate):
                continue
            if _is_role_based_name(candidate, mail):
                continue
            return candidate

    # Signature fallback after "Mit freundlichen Gruessen".
    signoff_idx = -1
    for idx, line in enumerate(lines):
        if "mit freundlichen gruessen" in _ascii_fold(line):
            signoff_idx = idx
            break
    if signoff_idx != -1:
        end = min(len(lines), signoff_idx + 9)
        for line_idx in range(signoff_idx + 1, end):
            candidate = lines[line_idx].strip(" ,;:-")
            if not _looks_like_person_name_line(candidate):
                continue
            if _is_role_based_name(candidate, mail):
                continue
            return candidate

    return ""


def _extract_contact(parsed: dict) -> dict:
    """Extract one contact object from supported LLM response shapes."""

    contacts = parsed.get("contacts")
    if isinstance(contacts, list) and contacts and isinstance(contacts[0], dict):
        return contacts[0]
    return parsed if isinstance(parsed, dict) else {}


def _extract_contacts(parsed: dict) -> list[dict]:
    """Extract all contact objects from supported LLM response shapes."""

    if not isinstance(parsed, dict):
        return []

    contacts = parsed.get("contacts")
    if isinstance(contacts, list):
        result = [contact for contact in contacts if isinstance(contact, dict)]
        return result

    return [parsed]


def _normalize_llm_result(parsed: dict, mail: str) -> dict:
    """Apply hard business validation and normalize one parsed LLM result."""

    if not isinstance(parsed, dict):
        return {"is_allowed": False}
    if parsed.get("is_allowed") is not True:
        return {"is_allowed": False}

    mail_raw = "" if mail is None else str(mail)
    mail_text = _clean_text(mail_raw)
    if not mail_text:
        return {"is_allowed": False}

    contact = _extract_contact(parsed)
    normalized: dict[str, object] = {"is_allowed": True}

    for field in ALLOWED_FIELDS:
        raw_value = _clean_text(contact.get(field, ""))
        if not raw_value:
            normalized[field] = ""
            continue
        if field == "full_name" and _is_role_based_name(raw_value, mail_raw):
            normalized[field] = ""
            continue
        if field == "full_name" and not _looks_like_person_name_line(raw_value):
            normalized[field] = ""
            continue
        if _is_placeholder(raw_value):
            normalized[field] = ""
            continue
        if not _value_in_mail(field, raw_value, mail_text):
            normalized[field] = ""
            continue
        normalized[field] = raw_value

    # Hard requirement from business rule: phone must be present for allowed results.
    if not normalized.get("phone"):
        return {"is_allowed": False}

    # Ensure full_name is present when a phone number exists.
    if not normalized.get("full_name"):
        inferred_name = _extract_name_from_mail(mail_raw, str(normalized.get("phone", "")))
        if inferred_name and not _is_placeholder(inferred_name):
            normalized["full_name"] = inferred_name
    if not normalized.get("full_name"):
        return {"is_allowed": False}

    evidence_fields = ("company", "email", "phone", "address", "website")
    evidence_count = sum(1 for field in evidence_fields if normalized.get(field))

    if evidence_count == 0:
        return {"is_allowed": False}
    if evidence_count == 1 and normalized.get("email"):
        return {"is_allowed": False}

    return normalized


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


def _contact_dedupe_key(contact: dict) -> tuple[str, str, str]:
    """Build a stable deduplication key for one normalized contact."""

    phone_key = _phone_digits(str(contact.get("phone", "")))
    email_key = _clean_text(contact.get("email", "")).casefold()
    name_key = _ascii_fold(_clean_text(contact.get("full_name", "")))
    return (phone_key, email_key, name_key)


def _dedupe_contacts(contacts: list[dict]) -> list[dict]:
    """Remove duplicate contacts while preserving first-seen order."""

    deduped: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for contact in contacts:
        key = _contact_dedupe_key(contact)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(contact)
    return deduped


def _extract_structured_contacts_from_mail(mail: str) -> list[dict]:
    """Extract contacts from list-like lines: 'Company - Name; Phone; Email'."""

    if mail is None:
        return []

    extracted: list[dict] = []
    lines = [_clean_text(raw_line) for raw_line in str(mail).splitlines()]
    for idx, line in enumerate(lines):
        if not line:
            continue

        match = CONTACT_LIST_LINE_RE.search(line)
        if not match:
            continue

        company = _clean_text(match.group("company")).strip(" ,;:-")
        full_name = _clean_text(match.group("full_name")).strip(" ,;:-")
        phone = _clean_text(match.group("phone"))
        email_match = EMAIL_RE.search(line)
        email = _clean_text(email_match.group(0)) if email_match else ""
        if not email:
            # Some mail cleaners split "company/name/phone;" and email onto the next line.
            end = min(len(lines), idx + 4)
            for next_idx in range(idx + 1, end):
                next_line = lines[next_idx]
                if not next_line:
                    continue
                if CONTACT_LIST_LINE_RE.search(next_line):
                    break
                next_email_match = EMAIL_RE.search(next_line)
                if next_email_match:
                    email = _clean_text(next_email_match.group(0))
                    break

        parsed = {
            "is_allowed": True,
            "full_name": full_name,
            "company": company,
            "email": email,
            "phone": phone,
            "address": "",
            "website": "",
        }
        normalized = _normalize_llm_result(parsed, str(mail))
        if normalized.get("is_allowed") is True:
            extracted.append(normalized)

    return _dedupe_contacts(extracted)


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences around JSON-like model output."""

    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    return cleaned.replace("```", "").strip()


def _extract_json_object_candidates(text: str) -> list[str]:
    """Extract balanced JSON object substrings from arbitrary text."""

    candidates: list[str] = []
    depth = 0
    start = None
    in_string = False
    quote_char = ""
    escaped = False

    for idx, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote_char:
                in_string = False
            continue

        if char in {'"', "'"}:
            in_string = True
            quote_char = char
            continue

        if char == "{":
            if depth == 0:
                start = idx
            depth += 1
            continue

        if char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start : idx + 1])
                start = None

    return candidates


def _load_json_object(text: str) -> dict | None:
    """Parse one JSON/Python-like object string into a JSON-compatible dict."""

    normalized = text.strip()
    if not normalized:
        return None

    # Normalize common JSON-like output patterns from LLMs.
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
    normalized = re.sub(r"\bTrue\b", "true", normalized)
    normalized = re.sub(r"\bFalse\b", "false", normalized)
    normalized = re.sub(r"\bNone\b", "null", normalized)
    normalized = re.sub(r",\s*([}\]])", r"\1", normalized)

    try:
        parsed = json.loads(normalized)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback for single quotes / Python literal style output.
    pythonish = re.sub(r"\btrue\b", "True", normalized)
    pythonish = re.sub(r"\bfalse\b", "False", pythonish)
    pythonish = re.sub(r"\bnull\b", "None", pythonish)
    try:
        parsed = ast.literal_eval(pythonish)
    except (SyntaxError, ValueError):
        return None

    if isinstance(parsed, dict):
        return json.loads(json.dumps(parsed))
    return None


def parse_llm_json(raw: str) -> dict:
    """Parse and return the first allowed JSON object found in LLM output."""

    if not raw or raw.strip() == "":
        raise RuntimeError("LLM returned empty response")

    cleaned = _strip_markdown_fences(raw.strip())
    candidate_texts = [cleaned]

    # Handle quoted JSON blobs (e.g. "\"{\\\"is_allowed\\\": true}\"").
    try:
        unwrapped = json.loads(cleaned)
        if isinstance(unwrapped, str):
            candidate_texts.append(unwrapped)
    except json.JSONDecodeError:
        pass

    for candidate_text in candidate_texts:
        object_candidates = _extract_json_object_candidates(candidate_text)
        if not object_candidates:
            parsed = _load_json_object(candidate_text)
            if parsed is not None and parsed.get("is_allowed") is True:
                return parsed
            continue

        for obj in object_candidates:
            parsed = _load_json_object(obj)
            if parsed is not None and parsed.get("is_allowed") is True:
                return parsed

    raise RuntimeError(f"Could not parse JSON object from LLM output:\n{raw}")

