"""Normalization and contact extraction for parsed LLM outputs."""

import re

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
GENERIC_EMAIL_LOCALPART_TOKENS = {
    "info",
    "kontakt",
    "contact",
    "office",
    "mail",
    "hello",
    "team",
    "support",
    "service",
    "sales",
    "vertrieb",
    "einkauf",
    "jobs",
    "job",
    "bewerbung",
    "bewerbungen",
    "karriere",
    "career",
    "hr",
    "admin",
    "postmaster",
    "noreply",
    "no",
    "reply",
    "datenschutz",
    "privacy",
    "billing",
    "invoice",
    "buchhaltung",
    "accounting",
    "marketing",
    "presse",
    "press",
}


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


def _contains_business_hint(value: str) -> bool:
    """Check text for business/legal marker words while avoiding substring false hits."""

    folded_value = _ascii_fold(f" {value} ")

    for hint in BUSINESS_LINE_HINTS:
        folded_hint = _ascii_fold(str(hint)).strip()
        if not folded_hint:
            continue

        alnum_len = len(re.sub(r"[^a-z0-9]", "", folded_hint))
        if alnum_len <= 3:
            pattern = rf"(?<![a-z0-9]){re.escape(folded_hint)}(?![a-z0-9])"
            if re.search(pattern, folded_value):
                return True
            continue

        if folded_hint in folded_value:
            return True

    return False


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

    if _contains_business_hint(candidate):
        return False

    return bool(NAME_RE.fullmatch(candidate) or NAME_RE_ALL_CAPS.fullmatch(candidate))


def _phone_digits(value: str) -> str:
    """Return only digit characters from one phone-like value."""

    return re.sub(r"\D", "", value or "")


def _extract_name_from_email_address(email: str) -> str:
    """Derive a person-like name from an email local-part when possible."""

    cleaned = _clean_text(email)
    match = EMAIL_RE.search(cleaned)
    if not match:
        return ""

    local_part = match.group(0).split("@", 1)[0].split("+", 1)[0].casefold()
    if not local_part:
        return ""

    tokens: list[str] = []
    for raw_token in re.split(r"[._-]+", local_part):
        token = re.sub(r"[^A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df]", "", raw_token)
        if len(token) < 2:
            continue
        if token in GENERIC_EMAIL_LOCALPART_TOKENS:
            continue
        tokens.append(token)

    if len(tokens) < 2:
        return ""

    candidate = " ".join(part[:1].upper() + part[1:] for part in tokens[:3])
    if not _looks_like_person_name_line(candidate):
        return ""
    return candidate


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

    labeled_pattern = re.compile(
        r"(?:contact|kontakt|ansprechpartner|name)\s*[:\-]\s*"
        r"([A-Z\u00c4\u00d6\u00dc][\w'`\-]+(?:\s+[A-Z\u00c4\u00d6\u00dc][\w'`\-]+){1,2})",
        flags=re.IGNORECASE,
    )
    labeled_candidates: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        match = labeled_pattern.search(line)
        if not match:
            continue
        candidate = _clean_text(match.group(1)).strip(" ,;:-")
        if not _looks_like_person_name_line(candidate):
            continue
        if _is_role_based_name(candidate, mail):
            continue
        labeled_candidates.append((idx, candidate))

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

        if labeled_candidates:
            nearest_labeled = min(
                labeled_candidates,
                key=lambda item: (abs(item[0] - phone_idx), 0 if item[0] <= phone_idx else 1),
            )
            return nearest_labeled[1]

        start = max(0, phone_idx - 16)
        for line_idx in range(phone_idx - 1, start - 1, -1):
            candidate = lines[line_idx].strip(" ,;:-")
            if not _looks_like_person_name_line(candidate):
                continue
            if _is_role_based_name(candidate, mail):
                continue
            return candidate

        # Fallback: derive a name from nearby email local-parts.
        window_start = max(0, phone_idx - 4)
        window_end = min(len(lines), phone_idx + 5)
        for line_idx in range(window_start, window_end):
            for email_match in EMAIL_RE.finditer(lines[line_idx]):
                candidate = _extract_name_from_email_address(email_match.group(0))
                if not candidate:
                    continue
                if _is_role_based_name(candidate, mail):
                    continue
                return candidate

    if labeled_candidates:
        return labeled_candidates[0][1]

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

    # Last resort: derive from any email in the message.
    for line in lines:
        for email_match in EMAIL_RE.finditer(line):
            candidate = _extract_name_from_email_address(email_match.group(0))
            if not candidate:
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
