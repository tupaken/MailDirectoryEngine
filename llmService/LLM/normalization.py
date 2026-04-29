"""Normalization and contact extraction for parsed LLM outputs."""

import re

ALLOWED_FIELDS = ("full_name", "company", "email", "phone", "address", "website")
PLACEHOLDER_RE = re.compile(r"\b(test\d*|demo|sample|dummy|example)\b", re.IGNORECASE)
ROLE_TITLE_PART = r"(?:geschaeftsfuehrer(?:in)?|ceo|inhaber|vorstand|gf)"
PHONE_RE = re.compile(r"(?:(?:\+|00)\d[\d\s()/-]{5,}\d|\b0\d[\d\s()/-]{5,}\d\b|\b\d{6,}\b)")
EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.IGNORECASE)
HONORIFIC_TITLES = {
    "herr",
    "frau",
    "hr",
    "fr",
    "prof",
    "professor",
    "dr",
    "doktor",
    "ing",
    "ingenieur",
    "ingenieurin",
    "ingeneur",
    "dipl",
    "diplom",
    "dipl-ing",
    "dipl.-ing",
    "dipl ing",
}
LEADING_NAME_TITLE_RE = re.compile(
    r"^(?:(?:herr|frau|hr|fr|prof(?:essor)?|dr|doktor|ing(?:enieur|eneur)(?:in)?|dipl(?:om)?(?:[.\-\s]*ing(?:enieur|eneur)(?:in)?)?)\.?\s+)+",
    flags=re.IGNORECASE,
)
TRAILING_DEGREE_RE = re.compile(
    r"(?:,\s*|\s+)(?:mba|m\.?sc|b\.?sc|m\.?a|b\.?a|m\.?eng|b\.?eng)\.?$",
    flags=re.IGNORECASE,
)
LEADING_NAME_PREFIX_RE = re.compile(
    r"^(?:(?:i\.?\s*a\.?|i\.?\s*v\.?|im\s+auftrag|ppa\.?|pp\.?)\s+)+",
    flags=re.IGNORECASE,
)
NAME_TOKEN_RE = r"[A-Z\u00c4\u00d6\u00dc][a-z\u00e4\u00f6\u00fc\u00df]+(?:[-'][A-Z\u00c4\u00d6\u00dc]?[a-z\u00e4\u00f6\u00fc\u00df]+)?"
NAME_RE = re.compile(rf"({NAME_TOKEN_RE}(?:\s+{NAME_TOKEN_RE}){{1,2}})")
NAME_RE_ALL_CAPS = re.compile(r"([A-Z\u00c4\u00d6\u00dc]{2,}(?:\s+[A-Z\u00c4\u00d6\u00dc]{2,}){1,2})")
CONTACT_LIST_LINE_RE = re.compile(
    r"(?P<company>[^\n;]+?)\s*[-\u2013\u2014]\s*"
    r"(?P<full_name>[A-Z\u00c4\u00d6\u00dc][\w'.`\-]+(?:\s+[A-Z\u00c4\u00d6\u00dc][\w'.`\-]+){1,3})\s*;\s*"
    r"(?P<phone>(?:(?:\+|00)\d[\d\s()/-]{5,}\d|\b\d{6,}\b))"
    r"(?:\s*;\s*(?P<email>[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}))?",
    flags=re.IGNORECASE,
)
STRUCTURED_CONTACT_CONTINUATION_HINT_RE = re.compile(
    r"^(telefon|tel\.?|mobil(?:telefon)?|handy|fax|telefax|durchwahl|"
    r"e-?mail|de-?mail|web(?:site)?|www\.|http)",
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
    "str.",
    "str",
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
SIGNATURE_SIGNOFF_MARKERS = (
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
SIGNATURE_CONTACT_HINT_RE = re.compile(
    r"(telefon|tel\.?|telefax|fax|mobil|handy|durchwahl|e-?mail|web|www\.|http|gmbh|\bag\b|\bug\b|\bkg\b|str\.|stra[sz]e|adresse|hrb|ust)",
    flags=re.IGNORECASE,
)
LEGAL_NUMBER_LINE_HINT_RE = re.compile(
    r"(hrb|hraa|handelsregister|registergericht|amtsgericht|ust|ust-id|umsatzsteuer|steuernummer|tax|iban|bic)",
    flags=re.IGNORECASE,
)
GENERIC_SIGNATURE_FOOTER_HINT_RE = re.compile(
    r"(vorsitzender|aufsichtsrat|geschaeftsfuehrer|geschaeftsfuehrerin|sitz der gesellschaft|"
    r"amtsgericht|handelsregister|hrb|ust|www\.|http)",
    flags=re.IGNORECASE,
)

NAME_SCORE_INLINE_PHONE_LINE = 4
NAME_SCORE_LABEL = 3
NAME_SCORE_NEAR_PHONE_LINE = 2
NAME_SCORE_SIGNOFF = 2
NAME_SCORE_EMAIL_DERIVED = 1
NAME_SCORE_SIGNATURE_PHONE_BONUS = 3
NAME_SCORE_EMAIL_MATCH_BONUS = 2
NON_PERSON_NAME_TOKENS = {
    "gmbh",
    "ag",
    "ug",
    "kg",
    "llc",
    "inc",
    "ltd",
    "limited",
    "company",
    "co",
    "corp",
    "corporation",
    "group",
    "holding",
}
NON_PERSON_ORG_TOKENS = {
    "fachbereich",
    "abteilung",
    "projektleitung",
    "development",
    "netzbetrieb",
    "waerme",
    "fernwaerme",
    "betriebsingenieur",
    "referat",
    "dezernat",
    "sachgebiet",
    "sekretariat",
    "verwaltung",
    "stadtverwaltung",
    "amt",
    "behoerde",
    "stadt",
    "gemeinde",
    "landkreis",
    "ministerium",
    "department",
    "team",
    "service",
    "support",
    "office",
    "unit",
}
ADDRESS_PREFIX_TOKENS = {
    "am",
    "an",
    "auf",
    "bei",
    "im",
    "in",
    "vom",
    "von",
    "zur",
    "zum",
}
GREETING_NAME_PHRASES = {
    "beste gruesse",
    "freundliche gruesse",
    "mit freundlichen gruessen",
    "viele gruesse",
    "best regards",
    "kind regards",
    "many thanks",
    "thanks and regards",
}
NON_PERSON_NAME_PHRASES = {
    "fuer fragen",
    "for questions",
    "unser team",
    "ihr team",
    "our team",
    "customer service",
    "service center",
    "service-center",
}
NON_PERSON_GREETING_TOKENS = {
    "hallo",
    "hi",
    "hey",
    "dear",
    "liebe",
    "lieber",
    "moin",
    "servus",
}
DOMAIN_PREFIX_TRIM_TOKENS = (
    "pb",
    "my",
    "mail",
    "team",
    "office",
    "info",
    "kontakt",
)
MAX_PHONE_DIGITS = 17


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


def _normalize_person_name_candidate(value: str) -> str:
    """Normalize person-name candidates (titles/order) to Firstname Surname shape."""

    candidate = _clean_text(value).strip(" ,;:-")
    if not candidate:
        return ""

    candidate = re.sub(r"\s+", " ", candidate)
    candidate = candidate.rstrip(":").strip(" ,;:-")

    while True:
        stripped = LEADING_NAME_PREFIX_RE.sub("", candidate).strip(" ,;:-")
        if stripped == candidate:
            break
        candidate = stripped
    if not candidate:
        return ""

    while True:
        stripped = LEADING_NAME_TITLE_RE.sub("", candidate).strip(" ,;:-")
        if stripped == candidate:
            break
        candidate = stripped
    if not candidate:
        return ""

    if candidate.count(",") == 1:
        left, right = [part.strip(" ,;:-") for part in candidate.split(",", 1)]
        if left and right:
            if not any(ch.isdigit() for ch in left) and not any(ch.isdigit() for ch in right):
                if len(left.split()) <= 2 and 1 <= len(right.split()) <= 3:
                    candidate = f"{right} {left}"

    candidate = TRAILING_DEGREE_RE.sub("", candidate).strip(" ,;:-")
    candidate = re.sub(r"\s+", " ", candidate)

    tokens = [token for token in candidate.split(" ") if token]
    while tokens:
        first_token = tokens[0].strip(".").casefold()
        if first_token in HONORIFIC_TITLES:
            tokens = tokens[1:]
            continue
        break

    if len(tokens) < 2:
        return ""
    return " ".join(tokens)


def _is_signature_marker_line(line: str) -> bool:
    """Return True when one line likely starts a signature block."""

    stripped = _clean_text(line)
    if not stripped:
        return False
    if stripped in {"--", "---", "__", "___"}:
        return True

    folded_line = _ascii_fold(stripped)
    return any(folded_line.startswith(marker) for marker in SIGNATURE_SIGNOFF_MARKERS)


def _find_signature_start_index(lines: list[str]) -> int | None:
    """Best-effort signature start detection based on sign-off/contact hints."""

    for idx, line in enumerate(lines):
        if _is_signature_marker_line(line):
            return idx

    if len(lines) < 4:
        return None

    start_scan = max(0, len(lines) - 14)
    for idx in range(start_scan, len(lines)):
        tail_lines = [line for line in lines[idx:] if line]
        if len(tail_lines) < 3:
            continue
        hint_count = sum(1 for line in tail_lines if SIGNATURE_CONTACT_HINT_RE.search(line))
        if hint_count >= 2:
            return idx

    return None


def _looks_like_recipient_distribution_line(line: str) -> bool:
    """Detect header/distribution lines that list many recipients."""

    cleaned = _clean_text(line)
    if not cleaned:
        return False

    folded = _ascii_fold(cleaned)
    header_prefixes = (
        "an:",
        "to:",
        "cc:",
        "bcc:",
        "kopie:",
        "copy:",
        "antwort an:",
        "reply-to:",
        "reply to:",
        "von:",
        "from:",
    )
    if folded.startswith(header_prefixes) and cleaned.count("@") >= 1:
        return True

    email_count = len(EMAIL_RE.findall(cleaned))
    if email_count >= 2 and (";" in cleaned or "," in cleaned):
        return True

    return False


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
    candidates = [_clean_text(name)]
    normalized = _normalize_person_name_candidate(name)
    if normalized and normalized not in candidates:
        candidates.append(normalized)

    for candidate in candidates:
        if not candidate:
            continue
        folded_candidate = _ascii_fold(candidate)
        escaped_name = re.escape(folded_candidate)
        matching_lines = [
            line
            for line in folded_mail.splitlines()
            if folded_candidate in line
        ]
        if not matching_lines:
            continue

        if any(not re.search(ROLE_TITLE_PART, line) for line in matching_lines):
            return False

        left_context = rf"{ROLE_TITLE_PART}[^\n\r]{{0,40}}{escaped_name}"
        right_context = rf"{escaped_name}[^\n\r]{{0,40}}{ROLE_TITLE_PART}"
        if bool(re.search(left_context, folded_mail)) or bool(re.search(right_context, folded_mail)):
            return True
    return False


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

    if field == "full_name":
        normalized_name = _normalize_person_name_candidate(value)
        if not normalized_name:
            return False
        if normalized_name.casefold() in mail_lower:
            return True

        parts = normalized_name.split()
        if len(parts) >= 2:
            swapped = f"{parts[-1]}, {' '.join(parts[:-1])}".casefold()
            if swapped in mail_lower:
                return True

        folded_mail = _ascii_fold(mail)
        escaped_name = re.escape(_ascii_fold(normalized_name))
        titled_pattern = (
            r"(?:\b(?:herr|frau|prof(?:essor)?|dr|doktor|ing(?:enieur|eneur)(?:in)?)[.]?\s+){0,2}"
            rf"{escaped_name}\b"
        )
        return bool(re.search(titled_pattern, folded_mail))

    return value_lower in mail_lower


def _looks_like_person_name_line(line: str) -> bool:
    """Heuristically validate whether a line resembles a real person name."""

    raw_candidate = _clean_text(line).strip(" ,;:-")
    if not raw_candidate:
        return False
    if any(ch.isdigit() for ch in raw_candidate):
        return False

    candidate = _normalize_person_name_candidate(raw_candidate)
    if not candidate:
        return False

    folded_candidate = _ascii_fold(candidate)
    if folded_candidate in GREETING_NAME_PHRASES:
        return False
    if folded_candidate in NON_PERSON_NAME_PHRASES:
        return False

    if _contains_business_hint(candidate):
        return False

    folded_tokens = [_ascii_fold(token.strip(".,;:")) for token in candidate.split()]
    if folded_tokens and folded_tokens[0] in ADDRESS_PREFIX_TOKENS:
        return False
    if folded_tokens and folded_tokens[0] in NON_PERSON_GREETING_TOKENS:
        return False
    if len(folded_tokens) >= 2 and folded_tokens[0] == "guten" and folded_tokens[1] in {
        "tag",
        "morgen",
        "abend",
    }:
        return False
    if any(token in NON_PERSON_NAME_TOKENS for token in folded_tokens):
        return False
    if any(token in NON_PERSON_ORG_TOKENS for token in folded_tokens):
        return False

    return bool(NAME_RE.fullmatch(candidate) or NAME_RE_ALL_CAPS.fullmatch(candidate))


def _phone_digits(value: str) -> str:
    """Return only digit characters from one phone-like value."""

    return re.sub(r"\D", "", value or "")


def _collapse_repeated_phone_digits(digits: str) -> str:
    """Collapse exact repeated phone-digit sequences (e.g. abcabc -> abc)."""

    if not digits:
        return ""

    length = len(digits)
    for unit_len in range(6, (length // 2) + 1):
        if length % unit_len != 0:
            continue
        repeat_count = length // unit_len
        if repeat_count < 2:
            continue
        unit = digits[:unit_len]
        if unit * repeat_count == digits:
            return unit
    return digits


def _normalize_phone_value_from_mail(phone_value: str, mail: str) -> str:
    """Map one phone candidate to a realistic explicit number from the mail."""

    candidate = _clean_text(phone_value)
    if not candidate:
        return ""

    candidate_digits = _collapse_repeated_phone_digits(_phone_digits(candidate))
    if len(candidate_digits) < 6:
        return ""

    explicit_matches: list[tuple[str, str]] = []
    for match in PHONE_RE.finditer(mail or ""):
        raw = _clean_text(match.group(0))
        digits = _collapse_repeated_phone_digits(_phone_digits(raw))
        if len(digits) < 6 or len(digits) > MAX_PHONE_DIGITS:
            continue
        explicit_matches.append((raw, digits))

    if explicit_matches:
        for raw, digits in explicit_matches:
            if digits == candidate_digits:
                return raw

        related = [
            (raw, digits)
            for raw, digits in explicit_matches
            if digits in candidate_digits or candidate_digits in digits
        ]
        if related:
            related.sort(key=lambda item: len(item[1]), reverse=True)
            return related[0][0]

    if len(candidate_digits) > MAX_PHONE_DIGITS:
        return ""
    return candidate


def _split_compound_localpart_to_name_tokens(local_part: str, domain_part: str) -> tuple[str, str]:
    """Try splitting one unsuffixed local-part into first/last name tokens."""

    local_alpha = re.sub(r"[^A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df]", "", local_part).casefold()
    if len(local_alpha) < 7 or local_alpha in GENERIC_EMAIL_LOCALPART_TOKENS:
        return ("", "")

    domain_label = domain_part.split(".", 1)[0]
    domain_alpha = re.sub(
        r"[^A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df]", "", domain_label
    ).casefold()
    if len(domain_alpha) < 4:
        return ("", "")

    domain_roots = {domain_alpha}
    for prefix in DOMAIN_PREFIX_TRIM_TOKENS:
        if domain_alpha.startswith(prefix) and len(domain_alpha) - len(prefix) >= 4:
            domain_roots.add(domain_alpha[len(prefix) :])

    best: tuple[int, int, int, str, str] | None = None
    for split_idx in range(3, len(local_alpha) - 2):
        first = local_alpha[:split_idx]
        last = local_alpha[split_idx:]
        if len(first) < 3 or len(last) < 3:
            continue
        if first in GENERIC_EMAIL_LOCALPART_TOKENS or last in GENERIC_EMAIL_LOCALPART_TOKENS:
            continue

        for root in domain_roots:
            if len(root) < 4:
                continue
            if not (last == root or root.endswith(last) or last.endswith(root)):
                continue

            exact_match = 1 if last == root else 0
            root_overlap = min(len(last), len(root))
            first_len = len(first)
            candidate = (exact_match, root_overlap, first_len, first, last)
            if best is None or candidate > best:
                best = candidate

    if best is None:
        return ("", "")

    return (best[3], best[4])


def _extract_name_from_email_address(email: str) -> str:
    """Derive a person-like name from an email local-part when possible."""

    cleaned = _clean_text(email)
    match = EMAIL_RE.search(cleaned)
    if not match:
        return ""

    address = match.group(0)
    local_part, domain_part = address.split("@", 1)
    local_part = local_part.split("+", 1)[0].casefold()
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
        first_token, last_token = _split_compound_localpart_to_name_tokens(local_part, domain_part)
        if first_token and last_token:
            tokens = [first_token, last_token]
        else:
            return ""

    candidate = " ".join(part[:1].upper() + part[1:] for part in tokens[:3])
    candidate = _normalize_person_name_candidate(candidate)
    if not candidate:
        return ""
    if not _looks_like_person_name_line(candidate):
        return ""
    return candidate


def _email_localpart(email: str) -> str:
    """Extract normalized local-part from one email address."""

    cleaned = _clean_text(email)
    match = EMAIL_RE.search(cleaned)
    if not match:
        return ""
    return match.group(0).split("@", 1)[0].split("+", 1)[0].casefold()


def _email_localpart_tokens(email: str) -> list[str]:
    """Extract conservative alpha tokens from one email local-part."""

    local_part = _email_localpart(email)
    if not local_part:
        return []

    tokens: list[str] = []
    for raw_token in re.split(r"[._-]+", local_part):
        token = re.sub(r"[^A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df]", "", raw_token).casefold()
        if not token:
            continue
        tokens.append(token)
    return tokens


def _email_looks_personal(email: str) -> bool:
    """Heuristic for person-like mailbox local-parts."""

    local_part = _email_localpart(email)
    if not local_part:
        return False

    tokens = _email_localpart_tokens(email)
    if not tokens:
        return False

    if any(token in GENERIC_EMAIL_LOCALPART_TOKENS for token in tokens):
        return False

    if len(tokens) >= 2:
        return True

    token = tokens[0]
    token_alpha = re.sub(r"[^a-z]", "", _ascii_fold(token))
    return len(token_alpha) >= 6


def _email_localpart_matches_name(email: str, full_name: str) -> bool:
    """Check whether an email local-part can plausibly belong to full_name."""

    normalized_name = _normalize_person_name_candidate(full_name)
    local_part = _email_localpart(email)
    if not normalized_name or not local_part:
        return False

    local_folded = _ascii_fold(local_part)
    local_compact = re.sub(r"[^a-z]", "", local_folded)

    name_tokens = [token for token in _ascii_fold(normalized_name).split() if token]
    if not name_tokens:
        return False

    for token in name_tokens:
        if len(token) >= 3 and token in local_folded:
            return True

    if len(name_tokens) >= 2:
        first_last = f"{name_tokens[0]}{name_tokens[-1]}"
        last_first = f"{name_tokens[-1]}{name_tokens[0]}"
        if first_last in local_compact or last_first in local_compact:
            return True

        initials_last = "".join(token[0] for token in name_tokens[:-1]) + name_tokens[-1]
        if initials_last and initials_last in local_compact:
            return True

    compact_name = "".join(name_tokens)
    if compact_name and compact_name in local_compact:
        return True

    return False


def _email_localpart_conflicts_with_name(email: str, full_name: str) -> bool:
    """Return True when a non-generic email local-part points to another person."""

    normalized_name = _normalize_person_name_candidate(full_name)
    if not normalized_name:
        return False

    tokens = _email_localpart_tokens(email)
    meaningful_tokens = [
        re.sub(r"[^a-z]", "", _ascii_fold(token))
        for token in tokens
        if token.casefold() not in GENERIC_EMAIL_LOCALPART_TOKENS
    ]
    meaningful_tokens = [token for token in meaningful_tokens if len(token) >= 3]
    if not meaningful_tokens:
        return False

    if _email_localpart_matches_name(email, normalized_name):
        return False

    name_tokens = [
        re.sub(r"[^a-z]", "", _ascii_fold(token))
        for token in normalized_name.split()
        if len(re.sub(r"[^a-z]", "", _ascii_fold(token))) >= 3
    ]
    if not name_tokens:
        return False

    return not any(
        email_token in name_token or name_token in email_token
        for email_token in meaningful_tokens
        for name_token in name_tokens
    )


def _names_are_compatible(primary_name: str, secondary_name: str) -> bool:
    """Check whether two person-name forms likely describe the same person."""

    normalized_primary = _normalize_person_name_candidate(primary_name)
    normalized_secondary = _normalize_person_name_candidate(secondary_name)
    if not normalized_primary or not normalized_secondary:
        return False

    folded_primary = _ascii_fold(normalized_primary)
    folded_secondary = _ascii_fold(normalized_secondary)
    if folded_primary == folded_secondary:
        return True

    primary_tokens = [token for token in folded_primary.split() if token]
    secondary_tokens = [token for token in folded_secondary.split() if token]
    if len(primary_tokens) < 2 or len(secondary_tokens) < 2:
        return False

    if primary_tokens[-1] == secondary_tokens[-1]:
        first_a = primary_tokens[0]
        first_b = secondary_tokens[0]
        if first_a == first_b:
            return True
        if first_a[0] == first_b[0]:
            return True

    primary_set = set(primary_tokens)
    secondary_set = set(secondary_tokens)
    if primary_set.issubset(secondary_set) or secondary_set.issubset(primary_set):
        return True

    return False


def _extract_name_from_phone_line(line: str) -> str:
    """Extract a person-like name from one line that also contains a phone number."""

    cleaned_line = _clean_text(line)
    if not cleaned_line or not PHONE_RE.search(cleaned_line):
        return ""

    # Common contact-list format: "Company - First Last; +49 ...; mail@company.de"
    dash_match = re.search(
        r"[-\u2013\u2014]\s*"
        r"([A-Z\u00c4\u00d6\u00dc][\w'.`\-]+(?:\s+[A-Z\u00c4\u00d6\u00dc][\w'.`\-]+){1,3})"
        r"\s*(?=;|,|$)",
        cleaned_line,
    )
    if dash_match:
        candidate = _normalize_person_name_candidate(dash_match.group(1))
        if _looks_like_person_name_line(candidate):
            return candidate

    phone_match = PHONE_RE.search(cleaned_line)
    if not phone_match:
        return ""
    before_phone = cleaned_line[: phone_match.start()].strip(" ,;:-")
    if not before_phone:
        return ""

    labeled_match = re.search(
        r"(?:contact|kontakt|ansprechpartner|name|anrede)\s*[:\-]\s*([^;|]+)$",
        before_phone,
        flags=re.IGNORECASE,
    )
    if labeled_match:
        candidate = _normalize_person_name_candidate(labeled_match.group(1))
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

    normalized_before_phone = _normalize_person_name_candidate(before_phone)
    if _looks_like_person_name_line(normalized_before_phone):
        return normalized_before_phone

    inline_names = NAME_RE.findall(cleaned_line)
    for candidate in reversed(inline_names):
        candidate = _normalize_person_name_candidate(candidate)
        if _looks_like_person_name_line(candidate):
            return candidate

    return ""


def _normalize_phone_type_hint(value: str) -> str:
    """Map free-form phone labels to canonical contact phone types."""

    label = _ascii_fold(_clean_text(value))
    if not label:
        return "other"
    if any(token in label for token in ("fax", "telefax")):
        return "fax"
    if any(token in label for token in ("mobil", "mobile", "handy", "cell")):
        return "mobile"
    if any(token in label for token in ("home", "privat", "private")):
        return "home"
    if any(
        token in label
        for token in ("telefon", "phone", "tel", "zentrale", "durchwahl", "direct", "office", "work")
    ):
        return "business"
    return "other"


def _looks_like_structured_contact_continuation_line(line: str) -> bool:
    """Return True for lines that belong to one structured contact list item."""

    cleaned = _clean_text(line)
    if not cleaned:
        return False
    if CONTACT_LIST_LINE_RE.search(cleaned):
        return False
    if STRUCTURED_CONTACT_CONTINUATION_HINT_RE.search(cleaned):
        return True
    if EMAIL_RE.search(cleaned):
        return True
    return False


def _extract_phone_numbers_from_structured_lines(lines: list[str]) -> list[dict[str, str]]:
    """Collect typed phone candidates from a structured contact block."""

    extracted: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for idx, line in enumerate(lines):
        cleaned = _clean_text(line)
        if not cleaned:
            continue

        matches = PHONE_RE.findall(cleaned)
        if not matches:
            continue

        phone_type = "business" if idx == 0 else _normalize_phone_type_hint(cleaned.split(":", 1)[0])

        for match in matches:
            raw = _clean_text(match)
            if not raw:
                continue
            digits = _phone_digits(raw)
            if len(digits) < 6 or len(digits) > MAX_PHONE_DIGITS:
                continue
            dedupe_key = (phone_type, digits)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            extracted.append({"type": phone_type, "raw": raw})

    return extracted


_SIGNATURE_HEADER_OR_HISTORY_RE = re.compile(
    r"^(von|from|an|to|cc|bcc|betreff|subject|gesendet|sent|datum|date)\s*:|"
    r"^(am\s+.+\s+schrieb|on\s+.+\s+wrote|gesendet\s+am|sent\s+on)\b",
    flags=re.IGNORECASE,
)


def _extract_phone_numbers_from_signature_lines(lines: list[str]) -> list[dict[str, str]]:
    """Collect typed phone candidates from one signature block."""

    extracted: list[dict[str, str]] = []
    seen_digits: set[str] = set()

    for line in lines:
        cleaned = _clean_text(line)
        if not cleaned:
            continue
        if LEGAL_NUMBER_LINE_HINT_RE.search(cleaned):
            continue
        if "•" in cleaned and GENERIC_SIGNATURE_FOOTER_HINT_RE.search(cleaned):
            continue

        matches = PHONE_RE.findall(cleaned)
        if not matches:
            continue
        if "•" in cleaned and len(matches) >= 2 and not EMAIL_RE.search(cleaned):
            continue

        type_hint = cleaned.split(":", 1)[0] if ":" in cleaned else cleaned
        phone_type = _normalize_phone_type_hint(type_hint)

        for match in matches:
            raw = _clean_text(match)
            digits = _phone_digits(raw)
            if len(digits) < 6 or len(digits) > MAX_PHONE_DIGITS:
                continue
            if digits in seen_digits:
                continue
            seen_digits.add(digits)
            extracted.append({"type": phone_type, "raw": raw})

    return extracted


def _choose_primary_phone_from_numbers(
    phone_numbers: list[dict[str, str]],
    fallback: str = "",
) -> str:
    """Choose the best primary phone from typed phone entries."""

    type_priority = ("business", "mobile", "home", "other", "fax")
    for preferred_type in type_priority:
        for phone_item in phone_numbers:
            if not isinstance(phone_item, dict):
                continue
            if _clean_text(phone_item.get("type")) != preferred_type:
                continue
            raw = _clean_text(phone_item.get("raw") or phone_item.get("e164"))
            if raw:
                return raw
    return _clean_text(fallback)


def _looks_like_generic_signature_footer_anchor(line: str) -> bool:
    """Detect company/legal footer lines that should not start a personal contact block."""

    cleaned = _clean_text(line)
    if not cleaned:
        return False
    if LEGAL_NUMBER_LINE_HINT_RE.search(cleaned):
        return True
    if "•" not in cleaned:
        return False
    if not GENERIC_SIGNATURE_FOOTER_HINT_RE.search(cleaned):
        return False
    return len(PHONE_RE.findall(cleaned)) >= 1


def _signature_contact_block_bounds(lines: list[str], anchor_index: int) -> tuple[int, int]:
    """Find a compact local signature block around one phone line."""

    start = anchor_index
    max_up = max(0, anchor_index - 8)
    while start > max_up:
        previous_line = _clean_text(lines[start - 1])
        if not previous_line:
            break
        if _looks_like_recipient_distribution_line(previous_line):
            break
        if _SIGNATURE_HEADER_OR_HISTORY_RE.match(previous_line):
            break
        if re.fullmatch(r"-{5,}", previous_line):
            break
        start -= 1

    end = anchor_index
    max_down = min(len(lines) - 1, anchor_index + 8)
    while end < max_down:
        next_line = _clean_text(lines[end + 1])
        if not next_line:
            break
        if _looks_like_recipient_distribution_line(next_line):
            break
        if _SIGNATURE_HEADER_OR_HISTORY_RE.match(next_line):
            break
        if re.fullmatch(r"-{5,}", next_line):
            break
        end += 1

    return start, end


def _extract_name_from_mail(mail: str, phone: str = "") -> str:
    """Infer one best contact name from scored candidates in the mail text."""

    lines = [_clean_text(line) for line in mail.splitlines() if _clean_text(line)]
    if not lines:
        return ""

    signature_start_idx = _find_signature_start_index(lines)

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

    phone_in_signature = bool(
        signature_start_idx is not None and any(idx >= signature_start_idx for idx in phone_indexes)
    )

    email_name_candidates: list[tuple[int, str]] = []
    for line_idx, line in enumerate(lines):
        if _looks_like_recipient_distribution_line(line):
            continue
        for email_match in EMAIL_RE.finditer(line):
            candidate = _extract_name_from_email_address(email_match.group(0))
            if not candidate:
                continue
            if _is_role_based_name(candidate, mail):
                continue
            email_name_candidates.append((line_idx, candidate))

    scored_candidates: dict[str, tuple[int, int, int, str]] = {}

    def _add_scored_candidate(candidate: str, line_idx: int, base_score: int) -> None:
        """Validate and score one person-name candidate found near contact data."""

        if 0 <= line_idx < len(lines):
            if _looks_like_recipient_distribution_line(lines[line_idx]):
                return

        normalized = _normalize_person_name_candidate(candidate)
        if not normalized:
            return
        if _is_placeholder(normalized):
            return
        if not _looks_like_person_name_line(normalized):
            return
        if _is_role_based_name(normalized, mail):
            return

        score = base_score
        nearest_phone_distance = 999
        if phone_indexes:
            nearest_phone_distance = min(abs(line_idx - phone_idx) for phone_idx in phone_indexes)
            if nearest_phone_distance <= 1:
                score += 2
            elif nearest_phone_distance <= 3:
                score += 1

        if (
            signature_start_idx is not None
            and line_idx >= signature_start_idx
            and phone_in_signature
        ):
            score += NAME_SCORE_SIGNATURE_PHONE_BONUS

        normalized_key = _ascii_fold(normalized)
        for email_line_idx, email_candidate in email_name_candidates:
            if _ascii_fold(email_candidate) != normalized_key:
                continue
            score += NAME_SCORE_EMAIL_MATCH_BONUS
            if abs(email_line_idx - line_idx) <= 3:
                score += 1
            break

        current = (score, nearest_phone_distance, line_idx, normalized)
        existing = scored_candidates.get(normalized_key)
        if existing is None:
            scored_candidates[normalized_key] = current
            return

        if current[0] > existing[0]:
            scored_candidates[normalized_key] = current
            return
        if current[0] == existing[0] and current[1] < existing[1]:
            scored_candidates[normalized_key] = current
            return
        if current[0] == existing[0] and current[1] == existing[1] and current[2] < existing[2]:
            scored_candidates[normalized_key] = current

    labeled_pattern = re.compile(
        r"(?:contact|kontakt|ansprechpartner|name|anrede)\s*[:\-]\s*([^;|]+)",
        flags=re.IGNORECASE,
    )
    labeled_candidates: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        match = labeled_pattern.search(line)
        if not match:
            continue
        candidate = _normalize_person_name_candidate(match.group(1))
        if not candidate:
            continue
        labeled_candidates.append((idx, candidate))
        _add_scored_candidate(candidate, idx, NAME_SCORE_LABEL)

    for phone_idx in phone_indexes:
        inline_candidate = _extract_name_from_phone_line(lines[phone_idx])
        _add_scored_candidate(inline_candidate, phone_idx, NAME_SCORE_INLINE_PHONE_LINE)

        if labeled_candidates:
            nearest_labeled = min(
                labeled_candidates,
                key=lambda item: (abs(item[0] - phone_idx), 0 if item[0] <= phone_idx else 1),
            )
            _add_scored_candidate(nearest_labeled[1], nearest_labeled[0], NAME_SCORE_LABEL)

        start = max(0, phone_idx - 16)
        for line_idx in range(phone_idx - 1, start - 1, -1):
            candidate = _normalize_person_name_candidate(lines[line_idx])
            if not candidate:
                continue
            distance = phone_idx - line_idx
            proximity_score = NAME_SCORE_NEAR_PHONE_LINE + (1 if distance <= 2 else 0)
            _add_scored_candidate(candidate, line_idx, proximity_score)

        window_start = max(0, phone_idx - 4)
        window_end = min(len(lines), phone_idx + 5)
        for line_idx in range(window_start, window_end):
            for email_match in EMAIL_RE.finditer(lines[line_idx]):
                candidate = _extract_name_from_email_address(email_match.group(0))
                _add_scored_candidate(candidate, line_idx, NAME_SCORE_EMAIL_DERIVED)

    if signature_start_idx is not None:
        end = min(len(lines), signature_start_idx + 10)
        for line_idx in range(signature_start_idx + 1, end):
            candidate = _normalize_person_name_candidate(lines[line_idx])
            _add_scored_candidate(candidate, line_idx, NAME_SCORE_SIGNOFF)

    for line_idx, candidate in email_name_candidates:
        _add_scored_candidate(candidate, line_idx, NAME_SCORE_EMAIL_DERIVED)

    if not scored_candidates:
        return ""

    best = max(scored_candidates.values(), key=lambda item: (item[0], -item[1], -item[2]))
    return best[3]


def _extract_inline_email(value: str) -> str:
    """Extract one email address from arbitrary field text."""

    cleaned = _clean_text(value)
    if not cleaned:
        return ""
    match = EMAIL_RE.search(cleaned)
    return _clean_text(match.group(0)) if match else ""


def _extract_inline_phone(value: str) -> str:
    """Extract one probable phone token from arbitrary field text."""

    cleaned = _clean_text(value)
    if not cleaned:
        return ""

    match = PHONE_RE.search(cleaned)
    if not match:
        return ""

    candidate = _clean_text(match.group(0))
    digits = _phone_digits(candidate)
    if len(digits) < 6 or len(digits) > MAX_PHONE_DIGITS:
        return ""

    # Avoid treating plain IDs (e.g., register numbers) as phone values.
    starts_like_phone = candidate.startswith("+") or candidate.startswith("00") or candidate.startswith("0")
    has_phone_separators = any(sep in candidate for sep in (" ", "-", "(", ")", "/"))
    if not starts_like_phone and not has_phone_separators:
        return ""

    return candidate


def _extract_inline_name(value: str) -> str:
    """Extract one person-like name from arbitrary field text."""

    cleaned = _clean_text(value).strip(" ,;:-")
    if not cleaned:
        return ""

    labeled_match = re.search(
        r"(?:contact|kontakt|ansprechpartner|name|anrede)\s*[:\-]\s*([^;|]+)",
        cleaned,
        flags=re.IGNORECASE,
    )
    if labeled_match:
        candidate = _normalize_person_name_candidate(labeled_match.group(1))
        if _looks_like_person_name_line(candidate):
            return candidate

    direct = _normalize_person_name_candidate(cleaned)
    if _looks_like_person_name_line(direct):
        return direct

    for match in NAME_RE.findall(cleaned):
        candidate = _normalize_person_name_candidate(match)
        if _looks_like_person_name_line(candidate):
            return candidate

    return ""


def _recover_swapped_contact_fields(contact: dict, mail_raw: str, mail_text: str) -> dict:
    """Recover obvious email/phone/name swaps across parsed contact fields."""

    if not isinstance(contact, dict):
        return {}

    recovered = {field: _clean_text(contact.get(field, "")) for field in ALLOWED_FIELDS}

    source_keys: list[str] = list(ALLOWED_FIELDS)
    for key in contact.keys():
        if isinstance(key, str) and key not in source_keys:
            source_keys.append(key)
    person_name_source_keys = ["full_name", "phone", "email"]
    for key in source_keys:
        if key in person_name_source_keys:
            continue
        folded_key = _ascii_fold(key)
        if "name" in folded_key:
            person_name_source_keys.append(key)

    # Recover email from any field that contains one.
    email_value = _extract_inline_email(recovered.get("email", ""))
    if not email_value or not _value_in_mail("email", email_value, mail_text):
        for key in source_keys:
            email_candidate = _extract_inline_email(contact.get(key, ""))
            if not email_candidate:
                continue
            if _is_placeholder(email_candidate):
                continue
            if not _value_in_mail("email", email_candidate, mail_text):
                continue
            email_value = email_candidate
            break
    if email_value:
        recovered["email"] = email_value

    # Recover phone from any field that contains one.
    phone_value = _normalize_phone_value_from_mail(recovered.get("phone", ""), mail_raw)
    if not phone_value:
        for key in source_keys:
            phone_candidate_raw = _extract_inline_phone(contact.get(key, ""))
            if not phone_candidate_raw:
                continue
            phone_candidate = _normalize_phone_value_from_mail(phone_candidate_raw, mail_raw)
            if not phone_candidate:
                continue
            if not _value_in_mail("phone", phone_candidate, mail_text):
                continue
            phone_value = phone_candidate
            break
    if phone_value:
        recovered["phone"] = phone_value

    # Recover full_name from swapped fields or from any embedded email.
    full_name_value = _normalize_person_name_candidate(recovered.get("full_name", ""))
    full_name_valid = (
        bool(full_name_value)
        and _looks_like_person_name_line(full_name_value)
        and not _is_role_based_name(full_name_value, mail_raw)
        and _value_in_mail("full_name", full_name_value, mail_text)
    )
    if not full_name_valid:
        full_name_value = ""

    if not full_name_value:
        for key in person_name_source_keys:
            name_candidate = _extract_inline_name(contact.get(key, ""))
            if not name_candidate:
                continue
            if _is_role_based_name(name_candidate, mail_raw):
                continue
            if not _value_in_mail("full_name", name_candidate, mail_text):
                continue
            full_name_value = name_candidate
            break

    if not full_name_value:
        for key in person_name_source_keys:
            email_candidate = _extract_inline_email(contact.get(key, ""))
            if not email_candidate:
                continue
            inferred_name = _extract_name_from_email_address(email_candidate)
            if not inferred_name:
                continue
            if _is_role_based_name(inferred_name, mail_raw):
                continue
            if not _value_in_mail("full_name", inferred_name, mail_text):
                continue
            full_name_value = inferred_name
            break

    if full_name_value:
        recovered["full_name"] = full_name_value

    return recovered


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
    contact = _recover_swapped_contact_fields(contact, mail_raw, mail_text)
    normalized: dict[str, object] = {"is_allowed": True}

    for field in ALLOWED_FIELDS:
        raw_value = _clean_text(contact.get(field, ""))
        if not raw_value:
            normalized[field] = ""
            continue
        if field == "full_name":
            raw_value = _normalize_person_name_candidate(raw_value)
            if not raw_value:
                normalized[field] = ""
                continue
        if field == "phone":
            raw_value = _normalize_phone_value_from_mail(raw_value, mail_raw)
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
        email_based_name = _extract_name_from_email_address(str(normalized.get("email", "")))
        if email_based_name and not _is_role_based_name(email_based_name, mail_raw):
            normalized["full_name"] = email_based_name
        else:
            inferred_name = _extract_name_from_mail(mail_raw, str(normalized.get("phone", "")))
            if inferred_name and not _is_placeholder(inferred_name):
                normalized["full_name"] = inferred_name
    if not normalized.get("full_name"):
        company_display_name = _clean_text(normalized.get("company", ""))
        if company_display_name:
            normalized["_display_name_fallback"] = company_display_name
        else:
            return {"is_allowed": False}

    # Prevent cross-mixed identity fields (name from one person, email of another).
    email_value = _clean_text(normalized.get("email", ""))
    full_name_value = _clean_text(normalized.get("full_name", ""))
    if email_value and full_name_value:
        email_person_name = _extract_name_from_email_address(email_value)
        if email_person_name:
            if not _names_are_compatible(full_name_value, email_person_name):
                normalized["email"] = ""
        elif _email_localpart_conflicts_with_name(email_value, full_name_value):
            normalized["email"] = ""
        elif _email_looks_personal(email_value) and not _email_localpart_matches_name(
            email_value, full_name_value
        ):
            normalized["email"] = ""

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


from .contact_dedupe import _dedupe_contacts
from .contact_extraction import (
    _extract_signature_contacts_from_mail,
    _extract_structured_contacts_from_mail,
)

