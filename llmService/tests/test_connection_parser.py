"""Unit tests for LLM parsing and normalization helpers."""

import pytest

from llmService.LLM.Connection import (
    _extract_signature_contacts_from_mail,
    _extract_structured_contacts_from_mail,
    _normalize_llm_result,
    _strip_mail_headers_everywhere,
    parse_first_llm_json,
    parse_llm_json,
)
from llmService.LLM.normalization import _dedupe_contacts, _looks_like_person_name_line


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


def test_parse_llm_json_coerces_string_boolean_true():
    raw = '{"is_allowed": "true", "company": "Company Inc."}'
    parsed = parse_llm_json(raw)
    assert parsed["is_allowed"] is True
    assert parsed["company"] == "Company Inc."


def test_parse_llm_json_raises_when_no_allowed_json_object():
    with pytest.raises(RuntimeError, match="Could not parse JSON object"):
        parse_llm_json('{"is_allowed": false}')


def test_normalize_result_returns_false_when_not_allowed():
    parsed = {"is_allowed": False, "full_name": "Alex Smith"}
    result = _normalize_llm_result(parsed, "Alex Smith")
    assert result == {"is_allowed": False}


def test_normalize_result_rejects_hallucinated_values():
    parsed = {
        "is_allowed": True,
        "full_name": "Alex Smith",
        "company": "ABC Corporation",
        "email": "alpha.person@anon.invalid",
        "phone": "+999 100 200300",
    }
    result = _normalize_llm_result(parsed, "Reach us at info@anon.invalid")
    assert result == {"is_allowed": False}


def test_normalize_result_keeps_only_values_found_in_mail():
    parsed = {
        "is_allowed": True,
        "full_name": "Andre Xxxxx",
        "company": "Fake Corp",
        "email": "andre.xxxxx@anon.invalid",
        "phone": "+999 200 300 4000",
        "address": "Invented Street 9",
        "website": "anon.invalid",
    }
    mail = "Contact: Andre Xxxxx, andre.xxxxx@anon.invalid, phone +999 (200) 300-4000, website https://anon.invalid"
    result = _normalize_llm_result(parsed, mail)
    assert result == {
        "is_allowed": True,
        "full_name": "Andre Xxxxx",
        "company": "",
        "email": "andre.xxxxx@anon.invalid",
        "phone": "+999 (200) 300-4000",
        "address": "",
        "website": "anon.invalid",
    }


def test_normalize_result_requires_phone_for_allowed_result():
    parsed = {
        "is_allowed": True,
        "full_name": "Andre Xxxxx",
        "company": "Acme Co",
        "phone": "",
    }
    mail = "Andre Xxxxx\nAcme Co"
    result = _normalize_llm_result(parsed, mail)
    assert result == {"is_allowed": False}


def test_normalize_result_recovers_swapped_email_and_phone_fields():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Logistics LLC",
        "email": "+49 301 0004342",
        "phone": "taylor.smith@anon.invalid",
    }
    mail = """
Acme Logistics LLC
Phone: +49 (30) 1000 4342
E-Mail: taylor.smith@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["email"] == "taylor.smith@anon.invalid"
    assert result["phone"] == "+49 (30) 1000 4342"
    assert result["full_name"] == "Taylor Smith"


def test_normalize_result_recovers_phone_from_swapped_full_name_field():
    parsed = {
        "is_allowed": True,
        "full_name": "+49 30 123456",
        "company": "Acme LLC",
        "email": "robin.smith@anon.invalid",
        "phone": "Robin Smith",
    }
    mail = """
Robin Smith
Acme LLC
Telefon: +49 30 123456
E-Mail: robin.smith@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["phone"] == "+49 30 123456"
    assert result["full_name"] == "Robin Smith"


def test_normalize_result_infers_signature_name_not_recipient_list_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Rivertown",
        "email": "taylor.smith@anon.invalid",
        "phone": "+49-160-0002207",
    }
    mail = """
From:
Smith <taylor.smith@anon.invalid>
To:
Smith, Jordan <jordan.smith@anon.invalid>; Weber <robin.smith@anon.invalid>; Testrolle <testrolle@anon.invalid>
Subject:
Urlaub
Taylor Smith
PLANUNGSBUERO BEISPIEL LLC
Teststrasse 1
99999 Rivertown
Telefon: +999-700-100-18
Mobil: +49-160-0002207
E-Mail:
taylor.smith@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Taylor Smith"
    assert result["phone"] == "+49-160-0002207"
    assert result["email"] == "taylor.smith@anon.invalid"


def test_normalize_result_infers_name_from_signature_near_phone():
    parsed = {
        "is_allowed": True,
        "full_name": "Signal Contact",
        "company": "ANONYM BUILD Co",
        "email": "casey.smith@anon.invalid",
        "phone": "+999-700-100-10",
        "address": "",
        "website": "",
    }
    mail = """
From: Testteam <jobs@anon.invalid>
Gesendet: Mittwoch, 25. Maerz 2026 16:20
To: Team <team@anon.invalid>
Subject: test_signatur

Dear Sir or Madam

als Anlage erhalten Sie

Kind regards

Casey Smith

ANONYM BUILD Co
Anonymweg 21
99999 Rivertown
Phone: +999-700-100-10
Telefax: +999-700-100-11
E-Mail: casey.smith@anon.invalid
Web: www.northshore-build.invalid
CEO: Jordan Smith
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Casey Smith"


def test_normalize_result_rejects_role_based_name_when_no_person_name():
    parsed = {
        "is_allowed": True,
        "full_name": "Jordan Smith",
        "company": "ANONYM BUILD Co",
        "phone": "+999-700-100-10",
    }
    mail = """
ANONYM BUILD Co
    CEO: Jordan Smith
    Phone: +999-700-100-10
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == ""
    assert result["company"] == "ANONYM BUILD Co"
    assert result["_display_name_fallback"] == "ANONYM BUILD Co"


def test_normalize_result_keeps_name_when_role_line_exists_but_name_also_appears_as_signature():
    parsed = {
        "is_allowed": True,
        "full_name": "Joerg Smith",
        "company": "ANONYM BUILD Co",
        "email": "joerg.smith@anon.invalid",
        "phone": "+999-700-100-10",
    }
    mail = """
Kind regards
Joerg Smith
ANONYM BUILD Co
Phone: +999-700-100-10
E-Mail: joerg.smith@anon.invalid
Managing Director: Joerg Smith
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Joerg Smith"
    assert result["email"] == "joerg.smith@anon.invalid"


def test_normalize_result_drops_mismatched_single_token_personal_email():
    parsed = {
        "is_allowed": True,
        "full_name": "Taylor Smith",
        "email": "alpha@vendor.invalid",
        "phone": "+999 700 1000",
    }
    mail = """
Taylor Smith
Phone: +999 700 1000
E-Mail: alpha@vendor.invalid
"""

    result = _normalize_llm_result(parsed, mail)

    assert result["is_allowed"] is True
    assert result["full_name"] == "Taylor Smith"
    assert result["email"] == ""


def test_normalize_result_infers_name_from_contact_label_when_phone_present():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Co",
        "phone": "+999 300 123456",
    }
    mail = """
Contact: Robin Smith
Acme Co
Phone: +999 300 123456
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Robin Smith"


def test_normalize_result_strips_titles_from_full_name():
    parsed = {
        "is_allowed": True,
        "full_name": "Dr. Taylor Smith",
        "company": "Acme LLC",
        "phone": "+49 30 123456",
    }
    mail = """
Dr. Taylor Smith
Acme LLC
Telefon: +49 30 123456
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Taylor Smith"


def test_normalize_result_infers_name_from_comma_order_label():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme LLC",
        "phone": "+49 30 123456",
    }
    mail = """
Name: Smith, Taylor
Acme LLC
Telefon: +49 30 123456
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Taylor Smith"


def test_normalize_result_infers_name_with_ing_title_from_anrede_label():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme LLC",
        "phone": "+49 30 555666",
    }
    mail = """
Contact: Robin Smith
Acme LLC
Phone: +49 30 555666
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Robin Smith"


def test_normalize_result_infers_name_from_company_dash_contact_line():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Org Alpha Services",
        "email": "morgan.smith@anon.invalid",
        "phone": "+999 170 1112233",
    }
    mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Morgan Smith"


def test_normalize_result_matches_name_to_phone_when_multiple_contact_lines():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Org Beta Tech",
        "email": "service@anon.invalid",
        "phone": "+999 351 5558800",
    }
    mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid
Org Beta Tech - Riley Smith; +999 351 5558800; service@anon.invalid
Org Gamma Care - Avery Smith; +999 341 7788991; avery.smith@anon.invalid
Org Delta Construction - Quinn Smith; +999 221 4455667; quinn.smith@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Riley Smith"


def test_normalize_result_matches_labeled_name_to_target_phone():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Co",
        "phone": "+999 222222",
    }
    mail = """
Contact: Robin Smith
Phone: +999 111111
Contact: Parker Smith
Phone: +999 222222
Acme Co
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Parker Smith"


def test_normalize_result_prioritizes_signature_name_with_phone_and_email_match():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme LLC",
        "email": "robin.nadir@anon.invalid",
        "phone": "+49 40 888999",
    }
    mail = """
Contact: Jamie Smith
Phone: +49 30 111111

Kind regards
Robin Nadir
Acme LLC
Phone: +49 40 888999
E-Mail: robin.nadir@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Robin Nadir"


def test_normalize_result_does_not_treat_best_gruesse_as_person_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "ANONYM Software AG",
        "email": "contact@anon.invalid",
        "phone": "+49 160 0004525",
    }
    mail = """
Best regards
ANONYM Software AG
Phone: +49 160 0004525
E-Mail: contact@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == ""
    assert result["company"] == "ANONYM Software AG"
    assert result["_display_name_fallback"] == "ANONYM Software AG"


def test_normalize_result_prefers_name_matching_email_localpart():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme LLC",
        "phone": "+49 30 777888",
    }
    mail = """
Contact: Robin Smith
Contact: Dakota Nadir
Acme LLC
Phone: +49 30 777888
E-Mail: dakota.nadir@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Dakota Nadir"


def test_normalize_result_prefers_email_matched_name_over_unrelated_signature_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "ANONYM Strom LLC",
        "email": "alpha.bravo.extern@anon.invalid",
        "phone": "+49 171 0005343",
    }
    mail = """
Best regards
Sky Demo
ANONYM Strom LLC
Phone: +49 171 0005343
Mobil: +49 1590 7660023
E-Mail: alpha.bravo.extern@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Alpha Bravo Extern"


def test_normalize_result_ignores_fachbereich_as_person_name_and_uses_email_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Administration Rivertown",
        "email": "delta.echo@anon.invalid",
        "phone": "03000 70128",
    }
    mail = """
Fachbereich Innere
Phone: 03000 70128
4268802
E-Mail: delta.echo@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Delta Echo"


def test_person_name_filter_rejects_address_and_organization_lines():
    assert _looks_like_person_name_line("Am Test Way") is False
    assert _looks_like_person_name_line("Rivertown Department Office") is False


def test_normalize_result_ignores_hallo_name_and_infers_from_compound_email():
    parsed = {
        "is_allowed": True,
        "full_name": "Dear Robin",
        "company": "ANONYM Planning LLC",
        "email": "charlienadir@nadir.invalid",
        "phone": "+49 3000 27100",
    }
    mail = """
Hello Robin
ANONYM Planning LLC
Phone: +49 3000 27100
Mobil: +49 171 0005543
E-Mail: charlienadir@nadir.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Charlie Nadir"
    assert result["email"] == "charlienadir@nadir.invalid"


def test_normalize_result_ignores_netzbetrieb_waerme_and_uses_person_signature_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Netz Acme LLC",
        "email": "lars.ziegler@netzsample.invalid",
        "phone": "0170 0002023",
    }
    mail = """
Kind regards
i. A. Lars Ziegler
Betriebsingenieur Fernwaerme
Netzbetrieb Waerme
Netz Acme LLC
Mobil: 0170 0002023
lars.ziegler@netzsample.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Lars Ziegler"


def test_normalize_result_ignores_projektleitung_development_as_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "ANONYM Constructiontraeger LLC",
        "email": "juliane.reinhardt-mueller@samplegruppe.invalid",
        "phone": "+49 (30) 1000 4342",
    }
    mail = """
Dear Mr. Smith,
Kind regards
Juliane Reinhardt-Mueller
Projektleitung Development
ANONYM Constructiontraeger LLC
T: +49 (30) 1000 4342
M: +49 (1520) 1882 792
E: juliane.reinhardt-mueller@samplegruppe.invalid
Handelsregisternummer: HRB 134441 B
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Juliane Reinhardt Mueller"


def test_normalize_result_prefers_email_name_when_llm_full_name_is_hallo():
    parsed = {
        "is_allowed": True,
        "full_name": "Dear Mr. Smith",
        "company": "Planning Office Acme LLC",
        "email": "jordan.smith@anon.invalid",
        "phone": "+49 177 0002663",
    }
    mail = """
Dear Mr. Smith,
Kind regards
Dipl.-Ing.
ppa. Bernd Fischer
Mobil: +49 177 0002663
E-Mail: backup.person@anon.invalid

From: Smith, Jordan <jordan.smith@anon.invalid>
Kind regards
ppa. Jordan
Sample
PLANUNGSBUERO BEISPIEL LLC
Phone: +49 30 100012
Mobil: +49 151 0003316
E-Mail: jordan.smith@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Jordan Smith"
    assert result["email"] == "jordan.smith@anon.invalid"


def test_normalize_result_uses_company_display_fallback_when_no_person_name_exists():
    parsed = {
        "is_allowed": True,
        "full_name": "Fuer Fragen",
        "company": "ANONYM Print",
        "email": "service@anon.invalid",
        "phone": "0351 20 44 444",
        "website": "https://www.anon.invalid",
    }
    mail = """
Vielen Dank.

Fuer Fragen steht Ihnen unser Team unter service@anon.invalid oder 0351 20 44 444 gern zur Verfuegung.

ANONYM Print LLC
https://www.anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == ""
    assert result["company"] == "ANONYM Print"
    assert result["_display_name_fallback"] == "ANONYM Print"


def test_normalize_result_drops_personal_email_when_name_does_not_match():
    parsed = {
        "is_allowed": True,
        "full_name": "Gamma Delta",
        "company": "ANONYM Contact LLC",
        "email": "charlieecho@anon.invalid",
        "phone": "+49 89 51265100",
    }
    mail = """
Gamma Delta
ANONYM Contact LLC
Phone: +49 89 51265100
E-Mail: charlieecho@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Gamma Delta"
    assert result["email"] == ""


def test_normalize_result_keeps_generic_mailbox_when_name_differs():
    parsed = {
        "is_allowed": True,
        "full_name": "Gamma Delta",
        "company": "ANONYM Contact LLC",
        "email": "info@anon.invalid",
        "phone": "+49 89 51265100",
    }
    mail = """
Gamma Delta
ANONYM Contact LLC
Phone: +49 89 51265100
E-Mail: info@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["email"] == "info@anon.invalid"


def test_normalize_result_infers_name_from_email_localpart_when_phone_present():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Logistics LLC",
        "email": "taylor.smith@anon.invalid",
        "phone": "+999 400 765432",
    }
    mail = """
Acme Logistics LLC
Phone: +999 400 765432
E-Mail: taylor.smith@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Taylor Smith"


def test_normalize_result_rejects_generic_email_localpart_without_person_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Logistics LLC",
        "email": "info@anon.invalid",
        "phone": "+999 400 765432",
    }
    mail = """
Acme Logistics LLC
Phone: +999 400 765432
E-Mail: info@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == ""
    assert result["company"] == "Acme Logistics LLC"
    assert result["_display_name_fallback"] == "Acme Logistics LLC"


def test_extract_structured_contacts_from_mail_returns_all_contacts():
    mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid
Org Beta Tech - Riley Smith; +999 351 5558800; service@anon.invalid
Org Gamma Care - Avery Smith; +999 341 7788991; avery.smith@anon.invalid
Org Delta Construction - Quinn Smith; +999 221 4455667; quinn.smith@anon.invalid
"""
    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 4
    assert [contact["full_name"] for contact in contacts] == [
        "Morgan Smith",
        "Riley Smith",
        "Avery Smith",
        "Quinn Smith",
    ]
    assert [contact["phone"] for contact in contacts] == [
        "+999 170 1112233",
        "+999 351 5558800",
        "+999 341 7788991",
        "+999 221 4455667",
    ]


def test_extract_structured_contacts_from_mail_normalizes_title_names():
    mail = """
Acme LLC - Dr. Robin Smith; +49 30 123456; robin.smith@anon.invalid
"""
    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 1
    assert contacts[0]["full_name"] == "Robin Smith"


def test_extract_structured_contacts_from_mail_reads_email_from_following_line():
    mail = """
Org Alpha Services - Morgan Smith; +999 170 1112233;
morgan.smith@anon.invalid
Org Beta Tech - Riley Smith; +999 351 5558800;
service@anon.invalid
"""
    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 2
    assert contacts[0]["email"] == "morgan.smith@anon.invalid"
    assert contacts[1]["email"] == "service@anon.invalid"


def test_extract_structured_contacts_from_mail_attaches_local_source_text():
    mail = """
Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid
Org Beta Tech - Riley Smith; +999 351 5558800; service@anon.invalid
"""

    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 2
    assert contacts[0]["_source_text"] == (
        "Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid"
    )
    assert contacts[1]["_source_text"] == (
        "Org Beta Tech - Riley Smith; +999 351 5558800; service@anon.invalid"
    )


def test_extract_structured_contacts_from_mail_keeps_following_phone_lines_per_contact():
    mail = """
Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid
Mobil: +999 171 2223344
Fax: +999 351 5558801
Org Beta Tech - Riley Smith; +999 351 5558800; service@anon.invalid
"""

    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 2
    assert contacts[0]["_source_text"] == (
        "Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid\n"
        "Mobil: +999 171 2223344\n"
        "Fax: +999 351 5558801"
    )
    assert contacts[0]["phone_numbers"] == [
        {"type": "business", "raw": "+999 170 1112233"},
        {"type": "mobile", "raw": "+999 171 2223344"},
        {"type": "fax", "raw": "+999 351 5558801"},
    ]
    assert contacts[1]["_source_text"] == (
        "Org Beta Tech - Riley Smith; +999 351 5558800; service@anon.invalid"
    )


def test_extract_signature_contacts_from_mail_detects_signature_contact_block():
    mail = """
Hello team,

Kind regards
Robin Smith
PLANUNGSBUERO BEISPIEL LLC
Teststrasse 1
Telefon: +999-700-100-00
Telefax: +999-700-100-30
E-Mail:
robin.smith@anon.invalid
"""
    contacts = _extract_signature_contacts_from_mail(mail)
    assert len(contacts) >= 1
    assert any(
        contact["full_name"] == "Robin Smith"
        and contact["phone"] == "+999-700-100-00"
        and contact["email"] == "robin.smith@anon.invalid"
        for contact in contacts
    )
    robin_contact = next(
        contact for contact in contacts if contact["full_name"] == "Robin Smith"
    )
    assert robin_contact["phone_numbers"] == [
        {"type": "business", "raw": "+999-700-100-00"},
        {"type": "fax", "raw": "+999-700-100-30"},
    ]


def test_extract_signature_contacts_from_mail_aggregates_mobile_and_fax_into_one_contact():
    mail = """
Hello team,

Kind regards
Robin Smith
PLANUNGSBUERO BEISPIEL LLC
Teststrasse 1
Telefon: +49 30 123456
Mobil: +49 171 555000
Telefax: +49 30 123457
E-Mail: robin.smith@anon.invalid
"""

    contacts = _extract_signature_contacts_from_mail(mail)

    assert contacts == [
        {
            "is_allowed": True,
            "full_name": "Robin Smith",
            "company": "",
            "email": "robin.smith@anon.invalid",
            "phone": "+49 30 123456",
            "address": "",
            "website": "",
            "phone_numbers": [
                {"type": "business", "raw": "+49 30 123456"},
                {"type": "mobile", "raw": "+49 171 555000"},
                {"type": "fax", "raw": "+49 30 123457"},
            ],
            "_source_text": (
                "Kind regards\n"
                "Robin Smith\n"
                "PLANUNGSBUERO BEISPIEL LLC\n"
                "Teststrasse 1\n"
                "Telefon: +49 30 123456\n"
                "Mobil: +49 171 555000\n"
                "Telefax: +49 30 123457\n"
                "E-Mail: robin.smith@anon.invalid"
            ),
        }
    ]


def test_extract_signature_contacts_from_mail_ignores_legal_register_footer_numbers():
    mail = """
Dear Mr. Smith,

Kind regards
on behalf of Alex Smith
NorthWorks Nord LLC
Dokumentation
Telefon: 03943 555-281
E-Mail:
alex.smith@anon.invalid
NorthWorks Nord LLC * Test Way 38 * 38855 Rivertown * Tel. 03943 555-0 * Fax. 03943 555-441
* www.anon.invalid * Vorsitzender des Aufsichtsrates: Person Eins * Managing Director: Person Zwei * Amtsgericht Rivertown HRB 101732 * Sitz der Gesellschaft: Rivertown
"""

    contacts = _extract_signature_contacts_from_mail(mail)

    assert contacts == [
        {
            "is_allowed": True,
            "full_name": "Alex Smith",
            "company": "",
            "email": "alex.smith@anon.invalid",
            "phone": "03943 555-281",
            "address": "",
            "website": "",
            "phone_numbers": [
                {"type": "business", "raw": "03943 555-281"},
                {"type": "fax", "raw": "03943 555-0"},
                {"type": "fax", "raw": "03943 555-441"},
            ],
            "_source_text": (
                "Kind regards\n"
                "on behalf of Alex Smith\n"
                "NorthWorks Nord LLC\n"
                "Dokumentation\n"
                "Telefon: 03943 555-281\n"
                "E-Mail:\n"
                "alex.smith@anon.invalid\n"
                "NorthWorks Nord LLC * Test Way 38 * 38855 Rivertown * Tel. 03943 555-0 * Fax. 03943 555-441\n"
                "* www.anon.invalid * Vorsitzender des Aufsichtsrates: Person Eins * Managing Director: Person Zwei * Amtsgericht Rivertown HRB 101732 * Sitz der Gesellschaft: Rivertown"
            ),
        }
    ]


def test_extract_signature_contacts_from_mail_ignores_recipient_distribution_names():
    mail = """
From:
Smith <taylor.smith@anon.invalid>
To:
Smith, Jordan <jordan.smith@anon.invalid>; Weber <robin.smith@anon.invalid>; Testrolle <testrolle@anon.invalid>
Subject:
Urlaub
Taylor Smith
PLANUNGSBUERO BEISPIEL LLC
Teststrasse 1
Telefon: +999-700-100-18
Mobil: +49-160-0002207
E-Mail:
taylor.smith@anon.invalid
"""
    contacts = _extract_signature_contacts_from_mail(mail)
    assert len(contacts) >= 1
    assert any(contact["full_name"] == "Taylor Smith" for contact in contacts)
    assert all(contact["full_name"] != "Jordan Smith" for contact in contacts)


def test_extract_signature_contacts_from_mail_prefers_local_signature_name_in_forward_chain():
    mail = """
From:
morgan.smith@anon.invalid <morgan.smith@anon.invalid>
To:
Weber <robin.smith@anon.invalid>; Smith, Jordan <jordan.smith@anon.invalid>
Kind regards
Robin Smith
PLANUNGSBUERO BEISPIEL LLC
Telefon: +999-700-100-00
E-Mail:
robin.smith@anon.invalid
"""
    contacts = _extract_signature_contacts_from_mail(mail)
    assert len(contacts) >= 1
    assert any(
        contact["full_name"] == "Robin Smith"
        and contact["phone"] == "+999-700-100-00"
        and contact["email"] == "robin.smith@anon.invalid"
        for contact in contacts
    )


def test_dedupe_contacts_merges_same_name_and_phone_when_email_is_added_later():
    contacts = _dedupe_contacts(
        [
            {
                "is_allowed": True,
                "full_name": "Taylor Smith",
                "phone": "+999 700 1000",
            },
            {
                "is_allowed": True,
                "full_name": "Taylor Smith",
                "email": "taylor.smith@anon.invalid",
                "phone": "+999 700 1000",
            },
        ]
    )

    assert contacts == [
        {
            "is_allowed": True,
            "full_name": "Taylor Smith",
            "phone": "+999 700 1000",
            "email": "taylor.smith@anon.invalid",
        }
    ]


def test_dedupe_contacts_prefers_more_specific_source_text_when_merging():
    contacts = _dedupe_contacts(
        [
            {
                "is_allowed": True,
                "full_name": "Taylor Smith",
                "phone": "+999 700 1000",
                "_source_text": "Intro\nTaylor Smith\nPhone: +999 700 1000\nOther Contact\nPhone: +999 700 2000",
            },
            {
                "is_allowed": True,
                "full_name": "Taylor Smith",
                "email": "taylor.smith@anon.invalid",
                "phone": "+999 700 1000",
                "_source_text": "Taylor Smith\nPhone: +999 700 1000\nE-Mail: taylor.smith@anon.invalid",
            },
        ]
    )

    assert contacts == [
        {
            "is_allowed": True,
            "full_name": "Taylor Smith",
            "phone": "+999 700 1000",
            "email": "taylor.smith@anon.invalid",
            "_source_text": "Taylor Smith\nPhone: +999 700 1000\nE-Mail: taylor.smith@anon.invalid",
        }
    ]


def test_dedupe_contacts_merges_phone_numbers_from_richer_duplicate():
    contacts = _dedupe_contacts(
        [
            {
                "is_allowed": True,
                "full_name": "Taylor Smith",
                "phone": "+999 700 1000",
            },
            {
                "is_allowed": True,
                "full_name": "Taylor Smith",
                "phone": "+999 700 1000",
                "phone_numbers": [
                    {"type": "business", "raw": "+999 700 1000"},
                    {"type": "mobile", "raw": "+999 170 200300"},
                ],
            },
        ]
    )

    assert contacts == [
        {
            "is_allowed": True,
            "full_name": "Taylor Smith",
            "phone": "+999 700 1000",
            "phone_numbers": [
                {"type": "business", "raw": "+999 700 1000"},
                {"type": "mobile", "raw": "+999 170 200300"},
            ],
        }
    ]


def test_dedupe_contacts_merges_same_name_and_email_with_multiple_phones():
    contacts = _dedupe_contacts(
        [
            {
                "is_allowed": True,
                "full_name": "Taylor Smith",
                "email": "taylor.smith@anon.invalid",
                "phone": "+999 700 1000",
            },
            {
                "is_allowed": True,
                "full_name": "Taylor Smith",
                "email": "taylor.smith@anon.invalid",
                "phone": "+999 170 200300",
            },
        ]
    )

    assert contacts == [
        {
            "is_allowed": True,
            "full_name": "Taylor Smith",
            "email": "taylor.smith@anon.invalid",
            "phone": "+999 700 1000",
            "phone_numbers": [
                {"type": "business", "raw": "+999 700 1000"},
                {"type": "business", "raw": "+999 170 200300"},
            ],
        }
    ]


def test_dedupe_contacts_prefers_person_contact_over_company_fallback_when_email_or_phone_overlaps():
    contacts = _dedupe_contacts(
        [
            {
                "is_allowed": True,
                "full_name": "",
                "company": "ANONYM Build LLC",
                "email": "taylor.smith@anon.invalid",
                "phone": "+999 170 200300",
                "_display_name_fallback": "ANONYM Build LLC",
                "website": "www.anon.invalid",
            },
            {
                "is_allowed": True,
                "full_name": "Taylor Smith",
                "email": "taylor.smith@anon.invalid",
                "phone": "+999 700 1000",
                "phone_numbers": [
                    {"type": "business", "raw": "+999 700 1000"},
                    {"type": "mobile", "raw": "+999 170 200300"},
                ],
            },
        ]
    )

    assert contacts == [
        {
            "is_allowed": True,
            "full_name": "Taylor Smith",
            "company": "ANONYM Build LLC",
            "email": "taylor.smith@anon.invalid",
            "phone": "+999 700 1000",
            "website": "www.anon.invalid",
            "_display_name_fallback": "ANONYM Build LLC",
            "phone_numbers": [
                {"type": "business", "raw": "+999 700 1000"},
                {"type": "business", "raw": "+999 170 200300"},
                {"type": "mobile", "raw": "+999 170 200300"},
            ],
        }
    ]


def test_strip_mail_headers_everywhere_removes_split_header_fragments():
    mail = """
From:
" <
alex@anon.invalid
>
To:
Jordan Smith <jordan@anon.invalid>

Hello everyone

Kind regards
Robin Smith
Telefon: +49 30 123456
"""

    cleaned = _strip_mail_headers_everywhere(mail)

    assert cleaned == "Hello everyone\n\nKind regards\nRobin Smith\nTelefon: +49 30 123456"


def test_parse_llm_json_keeps_keyword_words_inside_string_values():
    raw = """
{"is_allowed": true, "company": "None LLC", "full_name": "Alex Smith", "phone": "+999 333444"}
"""
    parsed = parse_llm_json(raw)
    assert parsed["is_allowed"] is True
    assert parsed["company"] == "None LLC"


def test_parse_first_llm_json_returns_false_object():
    raw = """
```json
{"is_allowed": false, "reason": "newsletter"}
```
"""
    parsed = parse_first_llm_json(raw)
    assert parsed == {"is_allowed": False, "reason": "newsletter"}


def test_parse_first_llm_json_coerces_string_boolean_false():
    parsed = parse_first_llm_json('{"is_allowed": "false", "reason": "newsletter"}')
    assert parsed == {"is_allowed": False, "reason": "newsletter"}


def test_parse_first_llm_json_returns_none_for_non_json_text():
    assert parse_first_llm_json("plain output without braces") is None








