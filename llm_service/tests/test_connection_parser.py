"""Unit tests for LLM parsing and normalization helpers."""

import pytest

from llm_service.LLM.Connection import (
    _extract_structured_contacts_from_mail,
    _normalize_llm_result,
    parse_llm_json,
)


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
        "phone": "+999 100 200300",
    }
    result = _normalize_llm_result(parsed, "Reach us at info@real-company.com")
    assert result == {"is_allowed": False}


def test_normalize_result_keeps_only_values_found_in_mail():
    parsed = {
        "is_allowed": True,
        "full_name": "John Doe",
        "company": "Fake Corp",
        "email": "john.doe@abc.com",
        "phone": "+999 200 300 4000",
        "address": "Invented Street 9",
        "website": "abc.com",
    }
    mail = "Contact: John Doe, john.doe@abc.com, phone +999 (200) 300-4000, website https://abc.com"
    result = _normalize_llm_result(parsed, mail)
    assert result == {
        "is_allowed": True,
        "full_name": "John Doe",
        "company": "",
        "email": "john.doe@abc.com",
        "phone": "+999 200 300 4000",
        "address": "",
        "website": "abc.com",
    }


def test_normalize_result_requires_phone_for_allowed_result():
    parsed = {
        "is_allowed": True,
        "full_name": "John Doe",
        "company": "Acme Co",
        "phone": "",
    }
    mail = "John Doe\nAcme Co"
    result = _normalize_llm_result(parsed, mail)
    assert result == {"is_allowed": False}


def test_normalize_result_infers_name_from_signature_near_phone():
    parsed = {
        "is_allowed": True,
        "full_name": "Signal Contact",
        "company": "NORTHSHORE BUILD Co",
        "email": "lena.sommer@northshore-build.invalid",
        "phone": "+999-700-100-10",
        "address": "",
        "website": "",
    }
    mail = """
Von: Bewerbungen <jobs@northshore-build.invalid>
Gesendet: Mittwoch, 25. März 2026 16:20
An: Team <team@northshore-build.invalid>
Betreff: test_signatur

Sehr geehrte Damen und Herren

als Anlage erhalten Sie

Mit freundlichen Grüßen

Lena Sommer

NORTHSHORE BUILD Co
Harbor Road 21
99999 Sampletown
Telefon: +999-700-100-10
Telefax: +999-700-100-11
E-Mail: lena.sommer@northshore-build.invalid
Web: www.northshore-build.invalid
Geschäftsführer: Kai Nord
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Lena Sommer"


def test_normalize_result_rejects_role_based_name_when_no_person_name():
    parsed = {
        "is_allowed": True,
        "full_name": "Kai Nord",
        "company": "NORTHSHORE BUILD Co",
        "phone": "+999-700-100-10",
    }
    mail = """
NORTHSHORE BUILD Co
Geschaeftsfuehrer: Kai Nord
Telefon: +999-700-100-10
"""
    result = _normalize_llm_result(parsed, mail)
    assert result == {"is_allowed": False}


def test_normalize_result_infers_name_from_contact_label_when_phone_present():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Co",
        "phone": "+999 300 123456",
    }
    mail = """
Kontakt: Anna Meyer
Acme Co
Telefon: +999 300 123456
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Anna Meyer"


def test_normalize_result_infers_name_from_company_dash_contact_line():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Nordwerk Services",
        "email": "nina.becker@nordwerk-services.de",
        "phone": "+999 170 1112233",
    }
    mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Nordwerk Services - Nina Becker; +999 170 1112233; nina.becker@nordwerk-services.de
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Nina Becker"


def test_normalize_result_matches_name_to_phone_when_multiple_contact_lines():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Astera Technik",
        "email": "service@astera-technik.de",
        "phone": "+999 351 5558800",
    }
    mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Nordwerk Services - Nina Becker; +999 170 1112233; nina.becker@nordwerk-services.de
Astera Technik - Leon Hartmann; +999 351 5558800; service@astera-technik.de
Elbgarten Pflege - Mira Kruse; +999 341 7788991; mira.kruse@elbgarten-pflege.de
Rheinufer Bau - Tom Faber; +999 221 4455667; tom.faber@rheinufer-bau.de
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Leon Hartmann"


def test_extract_structured_contacts_from_mail_returns_all_contacts():
    mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Nordwerk Services - Nina Becker; +999 170 1112233; nina.becker@nordwerk-services.de
Astera Technik - Leon Hartmann; +999 351 5558800; service@astera-technik.de
Elbgarten Pflege - Mira Kruse; +999 341 7788991; mira.kruse@elbgarten-pflege.de
Rheinufer Bau - Tom Faber; +999 221 4455667; tom.faber@rheinufer-bau.de
"""
    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 4
    assert [contact["full_name"] for contact in contacts] == [
        "Nina Becker",
        "Leon Hartmann",
        "Mira Kruse",
        "Tom Faber",
    ]
    assert [contact["phone"] for contact in contacts] == [
        "+999 170 1112233",
        "+999 351 5558800",
        "+999 341 7788991",
        "+999 221 4455667",
    ]


def test_extract_structured_contacts_from_mail_reads_email_from_following_line():
    mail = """
Nordwerk Services - Nina Becker; +999 170 1112233;
nina.becker@nordwerk-services.invalid
Astera Technik - Leon Hartmann; +999 351 5558800;
service@astera-technik.invalid
"""
    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 2
    assert contacts[0]["email"] == "nina.becker@nordwerk-services.invalid"
    assert contacts[1]["email"] == "service@astera-technik.invalid"
