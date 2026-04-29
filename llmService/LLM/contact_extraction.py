"""Deterministic contact extraction from structured lists and signatures."""

import re

from .contact_dedupe import _dedupe_contacts
from .normalization import (
    CONTACT_LIST_LINE_RE,
    EMAIL_RE,
    PHONE_RE,
    _ascii_fold,
    _choose_primary_phone_from_numbers,
    _clean_text,
    _extract_name_from_mail,
    _extract_phone_numbers_from_signature_lines,
    _extract_phone_numbers_from_structured_lines,
    _is_role_based_name,
    _looks_like_generic_signature_footer_anchor,
    _looks_like_person_name_line,
    _looks_like_recipient_distribution_line,
    _looks_like_structured_contact_continuation_line,
    _normalize_llm_result,
    _normalize_person_name_candidate,
    _normalize_phone_value_from_mail,
    _phone_digits,
    _signature_contact_block_bounds,
)


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
        full_name = _normalize_person_name_candidate(match.group("full_name"))
        phone = _clean_text(match.group("phone"))
        email_match = EMAIL_RE.search(line)
        email = _clean_text(email_match.group(0)) if email_match else ""
        source_lines = [line]
        end = min(len(lines), idx + 6)
        for next_idx in range(idx + 1, end):
            next_line = lines[next_idx]
            if not next_line:
                continue
            if CONTACT_LIST_LINE_RE.search(next_line):
                break
            if not _looks_like_structured_contact_continuation_line(next_line):
                break
            source_lines.append(next_line)
            if not email:
                next_email_match = EMAIL_RE.search(next_line)
                if next_email_match:
                    email = _clean_text(next_email_match.group(0))

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
            normalized["_source_text"] = "\n".join(source_lines).strip()
            phone_numbers = _extract_phone_numbers_from_structured_lines(source_lines)
            if phone_numbers:
                normalized["phone_numbers"] = phone_numbers
            extracted.append(normalized)

    return _dedupe_contacts(extracted)


def _extract_signature_contacts_from_mail(mail: str) -> list[dict]:
    """Extract contacts from signature-like phone/email blocks in plain mail text."""

    if mail is None:
        return []

    mail_text = str(mail)
    lines = [_clean_text(raw_line) for raw_line in mail_text.splitlines()]
    extracted: list[dict] = []
    seen_phone_digits: set[str] = set()

    def _extract_local_name_near_phone(line_index: int) -> str:
        up_start = max(0, line_index - 10)
        up_end = line_index
        for cand_idx in range(up_end - 1, up_start - 1, -1):
            cand_line = lines[cand_idx]
            if not cand_line:
                continue
            if _looks_like_recipient_distribution_line(cand_line):
                continue
            folded_line = _ascii_fold(cand_line)
            if re.search(r"\b(telefon|tel\.?|mobil|handy|durchwahl|fax|e-?mail|web)\b", folded_line):
                continue
            candidate = _normalize_person_name_candidate(cand_line)
            if not candidate:
                continue
            if not _looks_like_person_name_line(candidate):
                continue
            if _is_role_based_name(candidate, mail_text):
                continue
            return candidate
        return ""

    for idx, line in enumerate(lines):
        if not line:
            continue

        folded = _ascii_fold(line)
        if not re.search(r"\b(telefon|tel\.?|mobil|handy|durchwahl)\b", folded):
            continue
        if _looks_like_generic_signature_footer_anchor(line):
            continue

        phone_match = PHONE_RE.search(line)
        if not phone_match:
            continue

        phone_raw = _clean_text(phone_match.group(0))
        phone_value = _normalize_phone_value_from_mail(phone_raw, mail_text)
        if not phone_value:
            continue

        phone_digits = _phone_digits(phone_value)
        if phone_digits in seen_phone_digits:
            continue

        block_start, block_end = _signature_contact_block_bounds(lines, idx)
        block_lines = [block_line for block_line in lines[block_start : block_end + 1] if block_line]
        if not block_lines:
            continue

        phone_numbers = _extract_phone_numbers_from_signature_lines(block_lines)
        if not phone_numbers:
            continue
        primary_phone = _choose_primary_phone_from_numbers(phone_numbers, fallback=phone_value)

        email_value = ""
        best_distance = 999
        for cand_idx in range(block_start, block_end + 1):
            cand_line = lines[cand_idx]
            if not cand_line or _looks_like_recipient_distribution_line(cand_line):
                continue
            email_match = EMAIL_RE.search(cand_line)
            if not email_match:
                continue
            distance = abs(cand_idx - idx)
            if distance < best_distance:
                best_distance = distance
                email_value = _clean_text(email_match.group(0))
        if not email_value:
            start = max(0, idx - 8)
            end = min(len(lines), idx + 9)
            for cand_idx in range(start, end):
                cand_line = lines[cand_idx]
                if not cand_line or _looks_like_recipient_distribution_line(cand_line):
                    continue
                email_match = EMAIL_RE.search(cand_line)
                if not email_match:
                    continue
                distance = abs(cand_idx - idx)
                if distance < best_distance:
                    best_distance = distance
                    email_value = _clean_text(email_match.group(0))

        full_name = _extract_local_name_near_phone(idx)
        if not full_name:
            full_name = _extract_name_from_mail(mail_text, primary_phone)
        parsed = {
            "is_allowed": True,
            "full_name": full_name,
            "company": "",
            "email": email_value,
            "phone": primary_phone,
            "address": "",
            "website": "",
        }
        normalized = _normalize_llm_result(parsed, mail_text)
        if normalized.get("is_allowed") is True:
            normalized["phone_numbers"] = phone_numbers
            normalized["_source_text"] = "\n".join(block_lines).strip()
            extracted.append(normalized)
            for phone_item in phone_numbers:
                if not isinstance(phone_item, dict):
                    continue
                item_digits = _phone_digits(_clean_text(phone_item.get("raw") or phone_item.get("e164")))
                if item_digits:
                    seen_phone_digits.add(item_digits)

    return _dedupe_contacts(extracted)
