"""Contact de-duplication and merge rules."""

from .normalization import (
    ALLOWED_FIELDS,
    _ascii_fold,
    _choose_primary_phone_from_numbers,
    _clean_text,
    _phone_digits,
)


def _contact_dedupe_key(contact: dict) -> tuple[str, str, str]:
    """Build a stable deduplication key for one normalized contact."""

    phone_key = _phone_digits(str(contact.get("phone", "")))
    email_key = _clean_text(contact.get("email", "")).casefold()
    name_key = _ascii_fold(_clean_text(contact.get("full_name", "")))
    return (phone_key, email_key, name_key)


def _contact_phone_digit_keys(contact: dict) -> set[str]:
    """Collect all phone digit variants from one contact for overlap checks."""

    keys: set[str] = set()

    phone_value = _clean_text(contact.get("phone"))
    phone_digits = _phone_digits(phone_value)
    if phone_digits:
        keys.add(phone_digits)

    phone_numbers = contact.get("phone_numbers")
    if isinstance(phone_numbers, list):
        for item in phone_numbers:
            if not isinstance(item, dict):
                continue
            digits = _phone_digits(_clean_text(item.get("raw") or item.get("e164")))
            if digits:
                keys.add(digits)

    return keys


def _dedupe_contacts(contacts: list[dict]) -> list[dict]:
    """Remove duplicate contacts while preserving first-seen order and richer data."""

    deduped: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    def merge_missing(existing: dict, incoming: dict) -> None:
        """Merge richer incoming fields into an already selected contact."""

        existing_has_person_name = bool(_clean_text(existing.get("full_name")))
        incoming_has_person_name = bool(_clean_text(incoming.get("full_name")))

        for field in ALLOWED_FIELDS:
            if not _clean_text(existing.get(field)) and _clean_text(incoming.get(field)):
                existing[field] = incoming.get(field)

        merged_phone_numbers: list[dict] = []
        seen_phone_keys: set[tuple[str, str]] = set()

        def add_phone_number_item(phone_type: str, raw_value: object) -> None:
            """Append one deduplicated phone-number entry to the merged contact."""

            raw = _clean_text(raw_value)
            digits = _phone_digits(raw)
            if not digits:
                return
            normalized_type = _clean_text(phone_type) or "other"
            key = (normalized_type, digits)
            if key in seen_phone_keys:
                return
            seen_phone_keys.add(key)
            merged_phone_numbers.append({"type": normalized_type, "raw": raw})

        existing_phone_numbers = existing.get("phone_numbers")
        incoming_phone_numbers = incoming.get("phone_numbers")
        had_explicit_phone_numbers = isinstance(existing_phone_numbers, list) or isinstance(
            incoming_phone_numbers, list
        )
        if incoming_has_person_name and not existing_has_person_name:
            add_phone_number_item("business", incoming.get("phone"))
            add_phone_number_item("business", existing.get("phone"))
        else:
            add_phone_number_item("business", existing.get("phone"))
            add_phone_number_item("business", incoming.get("phone"))
        if isinstance(incoming_phone_numbers, list):
            for item in existing_phone_numbers if isinstance(existing_phone_numbers, list) else []:
                if not isinstance(item, dict):
                    continue
                add_phone_number_item(
                    _clean_text(item.get("type")) or "other",
                    item.get("raw") or item.get("e164"),
                )
            for item in incoming_phone_numbers:
                if not isinstance(item, dict):
                    continue
                add_phone_number_item(
                    _clean_text(item.get("type")) or "other",
                    item.get("raw") or item.get("e164"),
                )
        elif isinstance(existing_phone_numbers, list):
            for item in existing_phone_numbers:
                if not isinstance(item, dict):
                    continue
                add_phone_number_item(
                    _clean_text(item.get("type")) or "other",
                    item.get("raw") or item.get("e164"),
                )
        if merged_phone_numbers and (had_explicit_phone_numbers or len(merged_phone_numbers) > 1):
            existing["phone_numbers"] = merged_phone_numbers
            existing["phone"] = _choose_primary_phone_from_numbers(
                merged_phone_numbers,
                fallback=_clean_text(existing.get("phone") or incoming.get("phone")),
            )
        existing_source = _clean_text(existing.get("_source_text"))
        incoming_source = _clean_text(incoming.get("_source_text"))
        if not existing_source and incoming_source:
            existing["_source_text"] = incoming.get("_source_text")
        elif existing_source and incoming_source and len(incoming_source) < len(existing_source):
            existing["_source_text"] = incoming.get("_source_text")

    for contact in contacts:
        key = _contact_dedupe_key(contact)
        if key in seen:
            for existing in deduped:
                if _contact_dedupe_key(existing) == key:
                    merge_missing(existing, contact)
                    break
            continue
        phone_key, email_key, name_key = key
        if phone_key and name_key:
            merged = False
            for existing in deduped:
                existing_key = _contact_dedupe_key(existing)
                same_phone_and_name = (
                    existing_key[0] == phone_key
                    and existing_key[2] == name_key
                )
                compatible_email = (
                    not existing_key[1]
                    or not email_key
                    or existing_key[1] == email_key
                )
                if same_phone_and_name and compatible_email:
                    merge_missing(existing, contact)
                    seen.add(key)
                    merged = True
                    break
            if merged:
                continue
        incoming_has_person_name = bool(_clean_text(contact.get("full_name")))
        if incoming_has_person_name:
            merged = False
            incoming_phone_keys = _contact_phone_digit_keys(contact)
            for existing in deduped:
                existing_has_person_name = bool(_clean_text(existing.get("full_name")))
                if existing_has_person_name:
                    continue
                existing_email = _clean_text(existing.get("email")).casefold()
                incoming_email = _clean_text(contact.get("email")).casefold()
                shared_email = bool(existing_email and incoming_email and existing_email == incoming_email)
                shared_phone = bool(_contact_phone_digit_keys(existing) & incoming_phone_keys)
                if shared_email or shared_phone:
                    merge_missing(existing, contact)
                    seen.add(key)
                    merged = True
                    break
            if merged:
                continue
        if name_key and email_key:
            merged = False
            for existing in deduped:
                existing_key = _contact_dedupe_key(existing)
                same_name_and_email = existing_key[1] == email_key and existing_key[2] == name_key
                if same_name_and_email:
                    merge_missing(existing, contact)
                    seen.add(key)
                    merged = True
                    break
            if merged:
                continue
        seen.add(key)
        deduped.append(contact)
    return deduped
