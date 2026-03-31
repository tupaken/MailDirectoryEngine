"""Unit tests for LLM parsing and normalization helpers."""

import pytest

from llm_service.LLM.Connection import _normalize_llm_result, parse_llm_json


def test_parse_llm_json_accepts_clean_allowed_json():
    raw = '{"is_allowed": true, "company": "Company Inc."}'
    parsed = parse_llm_json(raw)
    assert parsed["is_allowed"] is True
    assert parsed["company"] == "Company Inc."


def test_parse_llm_json_skips_false_and_returns_following_true_object():
    raw = """```json
{"is_allowed": false}
```
extra text that should be ignored
{"is_allowed": true}
"""
    parsed = parse_llm_json(raw)
    assert parsed == {"is_allowed": True}


def test_parse_llm_json_handles_python_literal_output():
    raw = "{'is_allowed': True, 'company': 'Company Inc.'}"
    parsed = parse_llm_json(raw)
    assert parsed["is_allowed"] is True
    assert parsed["company"] == "Company Inc."


def test_parse_llm_json_raises_when_no_allowed_json_object():
    with pytest.raises(RuntimeError, match="Could not parse JSON object"):
        parse_llm_json('{"is_allowed": false}')


def test_normalize_result_returns_false_when_not_allowed():
    parsed = {"is_allowed": False, "full_name": "John Doe"}
    result = _normalize_llm_result(parsed, "John Doe")
    assert result == {"is_allowed": False}


def test_normalize_result_rejects_hallucinated_values():
    parsed = {
        "is_allowed": True,
        "full_name": "John Doe",
        "company": "ABC Corporation",
        "email": "john@example.com",
        "phone": "+49 123 456789",
    }
    result = _normalize_llm_result(parsed, "Reach us at info@real-company.com")
    assert result == {"is_allowed": False}


def test_normalize_result_keeps_only_values_found_in_mail():
    parsed = {
        "is_allowed": True,
        "full_name": "John Doe",
        "company": "Fake Corp",
        "email": "john.doe@abc.com",
        "phone": "+1 555 123 4567",
        "address": "Invented Street 9",
        "website": "abc.com",
    }
    mail = "Contact: John Doe, john.doe@abc.com, phone +1 (555) 123-4567, website https://abc.com"
    result = _normalize_llm_result(parsed, mail)
    assert result == {
        "is_allowed": True,
        "full_name": "John Doe",
        "company": "",
        "email": "john.doe@abc.com",
        "phone": "+1 555 123 4567",
        "address": "",
        "website": "abc.com",
    }


def test_normalize_result_requires_phone_for_allowed_result():
    parsed = {
        "is_allowed": True,
        "full_name": "John Doe",
        "company": "Acme GmbH",
        "phone": "",
    }
    mail = "John Doe\nAcme GmbH"
    result = _normalize_llm_result(parsed, mail)
    assert result == {"is_allowed": False}


def test_normalize_result_infers_name_from_signature_near_phone():
    parsed = {
        "is_allowed": True,
        "full_name": "Leipzig Telefon",
        "company": "MUSTERBAU NORD GmbH",
        "email": "lena.sommer@musterbau-nord.de",
        "phone": "+49-351-700-10",
        "address": "",
        "website": "",
    }
    mail = """
Von: Bewerbungen <jobs@musterbau-nord.de>
Gesendet: Mittwoch, 25. März 2026 16:20
An: Team <team@musterbau-nord.de>
Betreff: test_signatur

Sehr geehrte Damen und Herren

als Anlage erhalten Sie

Mit freundlichen Grüßen

Lena Sommer

MUSTERBAU NORD GmbH
Hafenstraße 21
01067 Dresden
Telefon: +49-351-700-10
Telefax: +49-351-700-11
E-Mail: lena.sommer@musterbau-nord.de
Web: www.musterbau-nord.de
Geschäftsführer: Kai Nord
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Lena Sommer"


def test_normalize_result_rejects_role_based_name_when_no_person_name():
    parsed = {
        "is_allowed": True,
        "full_name": "Kai Nord",
        "company": "MUSTERBAU NORD GmbH",
        "phone": "+49-351-700-10",
    }
    mail = """
MUSTERBAU NORD GmbH
Geschaeftsfuehrer: Kai Nord
Telefon: +49-351-700-10
"""
    result = _normalize_llm_result(parsed, mail)
    assert result == {"is_allowed": False}


def test_normalize_result_infers_name_from_contact_label_when_phone_present():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme GmbH",
        "phone": "+49 30 123456",
    }
    mail = """
Kontakt: Anna Meyer
Acme GmbH
Telefon: +49 30 123456
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Anna Meyer"
