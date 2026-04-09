"""Unit tests for LLM parsing and normalization helpers."""

import pytest

from llmService.LLM.Connection import (
    _extract_signature_contacts_from_mail,
    _extract_structured_contacts_from_mail,
    _normalize_llm_result,
    parse_first_llm_json,
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


def test_parse_llm_json_coerces_string_boolean_true():
    raw = '{"is_allowed": "true", "company": "Company Inc."}'
    parsed = parse_llm_json(raw)
    assert parsed["is_allowed"] is True
    assert parsed["company"] == "Company Inc."


def test_parse_llm_json_raises_when_no_allowed_json_object():
    with pytest.raises(RuntimeError, match="Could not parse JSON object"):
        parse_llm_json('{"is_allowed": false}')


def test_normalize_result_returns_false_when_not_allowed():
    parsed = {"is_allowed": False, "full_name": "Alex Beispiel"}
    result = _normalize_llm_result(parsed, "Alex Beispiel")
    assert result == {"is_allowed": False}


def test_normalize_result_rejects_hallucinated_values():
    parsed = {
        "is_allowed": True,
        "full_name": "Alex Beispiel",
        "company": "ABC Corporation",
        "email": "alpha.person@anon.invalid",
        "phone": "+999 100 200300",
    }
    result = _normalize_llm_result(parsed, "Reach us at info@anon.invalid")
    assert result == {"is_allowed": False}


def test_normalize_result_keeps_only_values_found_in_mail():
    parsed = {
        "is_allowed": True,
        "full_name": "Alex Beispiel",
        "company": "Fake Corp",
        "email": "alex.beispiel@anon.invalid",
        "phone": "+999 200 300 4000",
        "address": "Invented Street 9",
        "website": "anon.invalid",
    }
    mail = "Contact: Alex Beispiel, alex.beispiel@anon.invalid, phone +999 (200) 300-4000, website https://anon.invalid"
    result = _normalize_llm_result(parsed, mail)
    assert result == {
        "is_allowed": True,
        "full_name": "Alex Beispiel",
        "company": "",
        "email": "alex.beispiel@anon.invalid",
        "phone": "+999 (200) 300-4000",
        "address": "",
        "website": "anon.invalid",
    }


def test_normalize_result_requires_phone_for_allowed_result():
    parsed = {
        "is_allowed": True,
        "full_name": "Alex Beispiel",
        "company": "Acme Co",
        "phone": "",
    }
    mail = "Alex Beispiel\nAcme Co"
    result = _normalize_llm_result(parsed, mail)
    assert result == {"is_allowed": False}


def test_normalize_result_recovers_swapped_email_and_phone_fields():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Logistics GmbH",
        "email": "+49 341 33204342",
        "phone": "taylor.beispiel@anon.invalid",
    }
    mail = """
Acme Logistics GmbH
Telefon: +49 (341) 3320 4342
E-Mail: taylor.beispiel@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["email"] == "taylor.beispiel@anon.invalid"
    assert result["phone"] == "+49 (341) 3320 4342"
    assert result["full_name"] == "Taylor Beispiel"


def test_normalize_result_recovers_phone_from_swapped_full_name_field():
    parsed = {
        "is_allowed": True,
        "full_name": "+49 30 123456",
        "company": "Muster GmbH",
        "email": "robin.beispiel@anon.invalid",
        "phone": "Robin Beispiel",
    }
    mail = """
Robin Beispiel
Muster GmbH
Telefon: +49 30 123456
E-Mail: robin.beispiel@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["phone"] == "+49 30 123456"
    assert result["full_name"] == "Robin Beispiel"


def test_normalize_result_infers_signature_name_not_recipient_list_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Machern bei Leipzig",
        "email": "taylor.beispiel@anon.invalid",
        "phone": "+49-160-7592207",
    }
    mail = """
Von:
Beispiel <taylor.beispiel@anon.invalid>
An:
Beispiel, Jordan <jordan.beispiel@anon.invalid>; Weber <robin.beispiel@anon.invalid>; Praktikant <praktikant@anon.invalid>
Betreff:
Urlaub
Taylor Beispiel
PLANUNGSBUERO BEISPIEL GmbH
Polenzer Strasse 6b
04827 Machern bei Leipzig
Telefon: +49-34292-710-18
Mobil: +49-160-7592207
E-Mail:
taylor.beispiel@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Taylor Beispiel"
    assert result["phone"] == "+49-160-7592207"
    assert result["email"] == "taylor.beispiel@anon.invalid"


def test_normalize_result_infers_name_from_signature_near_phone():
    parsed = {
        "is_allowed": True,
        "full_name": "Signal Contact",
        "company": "ANONYM BUILD Co",
        "email": "casey.beispiel@anon.invalid",
        "phone": "+999-700-100-10",
        "address": "",
        "website": "",
    }
    mail = """
Von: Bewerbungen <jobs@anon.invalid>
Gesendet: Mittwoch, 25. März 2026 16:20
An: Team <team@anon.invalid>
Betreff: test_signatur

Sehr geehrte Damen und Herren

als Anlage erhalten Sie

Mit freundlichen Grüßen

Casey Beispiel

ANONYM BUILD Co
Anonymweg 21
99999 Beispielstadt
Telefon: +999-700-100-10
Telefax: +999-700-100-11
E-Mail: casey.beispiel@anon.invalid
Web: www.northshore-build.invalid
Geschäftsführer: Jordan Beispiel
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Casey Beispiel"


def test_normalize_result_rejects_role_based_name_when_no_person_name():
    parsed = {
        "is_allowed": True,
        "full_name": "Jordan Beispiel",
        "company": "ANONYM BUILD Co",
        "phone": "+999-700-100-10",
    }
    mail = """
ANONYM BUILD Co
Geschaeftsfuehrer: Jordan Beispiel
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
Kontakt: Robin Beispiel
Acme Co
Telefon: +999 300 123456
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Robin Beispiel"


def test_normalize_result_strips_titles_from_full_name():
    parsed = {
        "is_allowed": True,
        "full_name": "Herr Dr. Taylor Beispiel",
        "company": "Acme GmbH",
        "phone": "+49 30 123456",
    }
    mail = """
Herr Dr. Taylor Beispiel
Acme GmbH
Telefon: +49 30 123456
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Taylor Beispiel"


def test_normalize_result_infers_name_from_comma_order_label():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme GmbH",
        "phone": "+49 30 123456",
    }
    mail = """
Name: Beispiel, Taylor
Acme GmbH
Telefon: +49 30 123456
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Taylor Beispiel"


def test_normalize_result_infers_name_with_ing_title_from_anrede_label():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme GmbH",
        "phone": "+49 30 555666",
    }
    mail = """
Anrede: Ing. Robin Beispiel
Acme GmbH
Telefon: +49 30 555666
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Robin Beispiel"


def test_normalize_result_infers_name_from_company_dash_contact_line():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Org Alpha Services",
        "email": "morgan.beispiel@anon.invalid",
        "phone": "+999 170 1112233",
    }
    mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Org Alpha Services - Morgan Beispiel; +999 170 1112233; morgan.beispiel@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Morgan Beispiel"


def test_normalize_result_matches_name_to_phone_when_multiple_contact_lines():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Org Beta Technik",
        "email": "service@anon.invalid",
        "phone": "+999 351 5558800",
    }
    mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Org Alpha Services - Morgan Beispiel; +999 170 1112233; morgan.beispiel@anon.invalid
Org Beta Technik - Riley Beispiel; +999 351 5558800; service@anon.invalid
Org Gamma Pflege - Avery Beispiel; +999 341 7788991; avery.beispiel@anon.invalid
Org Delta Bau - Quinn Beispiel; +999 221 4455667; quinn.beispiel@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Riley Beispiel"


def test_normalize_result_matches_labeled_name_to_target_phone():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Co",
        "phone": "+999 222222",
    }
    mail = """
Kontakt: Robin Beispiel
Telefon: +999 111111
Kontakt: Parker Beispiel
Telefon: +999 222222
Acme Co
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Parker Beispiel"


def test_normalize_result_prioritizes_signature_name_with_phone_and_email_match():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Muster GmbH",
        "email": "robin.nadir@anon.invalid",
        "phone": "+49 40 888999",
    }
    mail = """
Kontakt: Jamie Beispiel
Telefon: +49 30 111111

Mit freundlichen Gruessen
Robin Nadir
Muster GmbH
Telefon: +49 40 888999
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
        "phone": "+49 160 8894525",
    }
    mail = """
Beste Gruesse
ANONYM Software AG
Telefon: +49 160 8894525
E-Mail: contact@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result == {"is_allowed": False}


def test_normalize_result_prefers_name_matching_email_localpart():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Muster GmbH",
        "phone": "+49 30 777888",
    }
    mail = """
Kontakt: Robin Beispiel
Kontakt: Dakota Nadir
Muster GmbH
Telefon: +49 30 777888
E-Mail: dakota.nadir@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Dakota Nadir"


def test_normalize_result_prefers_email_matched_name_over_unrelated_signature_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "ANONYM Strom GmbH",
        "email": "alpha.bravo.extern@anon.invalid",
        "phone": "+49 171 4535343",
    }
    mail = """
Beste Gruesse
Sky Demo
ANONYM Strom GmbH
Telefon: +49 171 4535343
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
        "company": "Verwaltung Beispielstadt",
        "email": "delta.echo@anon.invalid",
        "phone": "034298 70128",
    }
    mail = """
Fachbereich Innere
Telefon: 034298 70128
4268802
E-Mail: delta.echo@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Delta Echo"


def test_normalize_result_ignores_hallo_name_and_infers_from_compound_email():
    parsed = {
        "is_allowed": True,
        "full_name": "Hallo Robin",
        "company": "ANONYM Planning GmbH",
        "email": "charlienadir@pbnadir.invalid",
        "phone": "+49 3429 27100",
    }
    mail = """
Hallo Robin
ANONYM Planning GmbH
Telefon: +49 3429 27100
Mobil: +49 171 4555343
E-Mail: charlienadir@pbnadir.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Charlie Nadir"
    assert result["email"] == "charlienadir@pbnadir.invalid"


def test_normalize_result_ignores_netzbetrieb_waerme_and_uses_person_signature_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Netz Beispiel GmbH",
        "email": "lars.ziegler@netzbeispiel.invalid",
        "phone": "0173 3982023",
    }
    mail = """
Freundliche Gruesse
i. A. Lars Ziegler
Betriebsingenieur Fernwaerme
Netzbetrieb Waerme
Netz Beispiel GmbH
Mobil: 0173 3982023
lars.ziegler@netzbeispiel.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Lars Ziegler"


def test_normalize_result_ignores_projektleitung_development_as_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "ANONYM Bautraeger GmbH",
        "email": "juliane.reinhardt-mueller@beispielgruppe.invalid",
        "phone": "+49 (341) 3320 4342",
    }
    mail = """
Hallo Herr Beispiel,
Freundliche Gruesse
Juliane Reinhardt-Mueller
Projektleitung Development
ANONYM Bautraeger GmbH
T: +49 (341) 3320 4342
M: +49 (1520) 1882 792
E: juliane.reinhardt-mueller@beispielgruppe.invalid
Handelsregisternummer: HRB 134441 B
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Juliane Reinhardt Mueller"


def test_normalize_result_prefers_email_name_when_llm_full_name_is_hallo():
    parsed = {
        "is_allowed": True,
        "full_name": "Hallo Herr Beispiel",
        "company": "Planungsbuero Beispiel GmbH",
        "email": "jordan.beispiel@anon.invalid",
        "phone": "+49 177 8112663",
    }
    mail = """
Hallo Herr Beispiel,
Mit freundlichen Gruessen
Dipl.-Ing.
ppa. Bernd Fischer
Mobil: +49 177 8112663
E-Mail: backup.person@anon.invalid

Von: Beispiel, Jordan <jordan.beispiel@anon.invalid>
Mit freundlichen Gruessen
ppa. Jordan
Beispiel
PLANUNGSBUERO BEISPIEL GmbH
Telefon: +49-34292-710-12
Mobil: +49-151-15343316
E-Mail: jordan.beispiel@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Jordan Beispiel"
    assert result["email"] == "jordan.beispiel@anon.invalid"


def test_normalize_result_drops_personal_email_when_name_does_not_match():
    parsed = {
        "is_allowed": True,
        "full_name": "Gamma Delta",
        "company": "ANONYM Contact GmbH",
        "email": "charlieecho@anon.invalid",
        "phone": "+49 89 51265100",
    }
    mail = """
Gamma Delta
ANONYM Contact GmbH
Telefon: +49 89 51265100
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
        "company": "ANONYM Contact GmbH",
        "email": "info@anon.invalid",
        "phone": "+49 89 51265100",
    }
    mail = """
Gamma Delta
ANONYM Contact GmbH
Telefon: +49 89 51265100
E-Mail: info@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["email"] == "info@anon.invalid"


def test_normalize_result_infers_name_from_email_localpart_when_phone_present():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Logistics GmbH",
        "email": "taylor.beispiel@anon.invalid",
        "phone": "+999 400 765432",
    }
    mail = """
Acme Logistics GmbH
Telefon: +999 400 765432
E-Mail: taylor.beispiel@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result["is_allowed"] is True
    assert result["full_name"] == "Taylor Beispiel"


def test_normalize_result_rejects_generic_email_localpart_without_person_name():
    parsed = {
        "is_allowed": True,
        "full_name": "",
        "company": "Acme Logistics GmbH",
        "email": "info@anon.invalid",
        "phone": "+999 400 765432",
    }
    mail = """
Acme Logistics GmbH
Telefon: +999 400 765432
E-Mail: info@anon.invalid
"""
    result = _normalize_llm_result(parsed, mail)
    assert result == {"is_allowed": False}


def test_extract_structured_contacts_from_mail_returns_all_contacts():
    mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Org Alpha Services - Morgan Beispiel; +999 170 1112233; morgan.beispiel@anon.invalid
Org Beta Technik - Riley Beispiel; +999 351 5558800; service@anon.invalid
Org Gamma Pflege - Avery Beispiel; +999 341 7788991; avery.beispiel@anon.invalid
Org Delta Bau - Quinn Beispiel; +999 221 4455667; quinn.beispiel@anon.invalid
"""
    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 4
    assert [contact["full_name"] for contact in contacts] == [
        "Morgan Beispiel",
        "Riley Beispiel",
        "Avery Beispiel",
        "Quinn Beispiel",
    ]
    assert [contact["phone"] for contact in contacts] == [
        "+999 170 1112233",
        "+999 351 5558800",
        "+999 341 7788991",
        "+999 221 4455667",
    ]


def test_extract_structured_contacts_from_mail_normalizes_title_names():
    mail = """
Muster GmbH - Dr. Robin Beispiel; +49 30 123456; robin.beispiel@anon.invalid
"""
    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 1
    assert contacts[0]["full_name"] == "Robin Beispiel"


def test_extract_structured_contacts_from_mail_reads_email_from_following_line():
    mail = """
Org Alpha Services - Morgan Beispiel; +999 170 1112233;
morgan.beispiel@anon.invalid
Org Beta Technik - Riley Beispiel; +999 351 5558800;
service@anon.invalid
"""
    contacts = _extract_structured_contacts_from_mail(mail)

    assert len(contacts) == 2
    assert contacts[0]["email"] == "morgan.beispiel@anon.invalid"
    assert contacts[1]["email"] == "service@anon.invalid"


def test_extract_signature_contacts_from_mail_detects_signature_contact_block():
    mail = """
Hallo Team,

Mit freundlichen Gruessen
Robin Beispiel
PLANUNGSBUERO BEISPIEL GmbH
Polenzer Strasse 6b
Telefon: +49-34292-710-0
Telefax: +49-34292-710-30
E-Mail:
robin.beispiel@anon.invalid
"""
    contacts = _extract_signature_contacts_from_mail(mail)
    assert len(contacts) >= 1
    assert any(
        contact["full_name"] == "Robin Beispiel"
        and contact["phone"] == "+49-34292-710-0"
        and contact["email"] == "robin.beispiel@anon.invalid"
        for contact in contacts
    )


def test_extract_signature_contacts_from_mail_ignores_recipient_distribution_names():
    mail = """
Von:
Beispiel <taylor.beispiel@anon.invalid>
An:
Beispiel, Jordan <jordan.beispiel@anon.invalid>; Weber <robin.beispiel@anon.invalid>; Praktikant <praktikant@anon.invalid>
Betreff:
Urlaub
Taylor Beispiel
PLANUNGSBUERO BEISPIEL GmbH
Polenzer Strasse 6b
Telefon: +49-34292-710-18
Mobil: +49-160-7592207
E-Mail:
taylor.beispiel@anon.invalid
"""
    contacts = _extract_signature_contacts_from_mail(mail)
    assert len(contacts) >= 1
    assert any(contact["full_name"] == "Taylor Beispiel" for contact in contacts)
    assert all(contact["full_name"] != "Jordan Beispiel" for contact in contacts)


def test_extract_signature_contacts_from_mail_prefers_local_signature_name_in_forward_chain():
    mail = """
Von:
morgan.beispiel@anon.invalid <morgan.beispiel@anon.invalid>
An:
Weber <robin.beispiel@anon.invalid>; Beispiel, Jordan <jordan.beispiel@anon.invalid>
Mit freundlichen Gruessen
Robin Beispiel
PLANUNGSBUERO BEISPIEL GmbH
Telefon: +49-34292-710-0
E-Mail:
robin.beispiel@anon.invalid
"""
    contacts = _extract_signature_contacts_from_mail(mail)
    assert len(contacts) >= 1
    assert any(
        contact["full_name"] == "Robin Beispiel"
        and contact["phone"] == "+49-34292-710-0"
        and contact["email"] == "robin.beispiel@anon.invalid"
        for contact in contacts
    )


def test_parse_llm_json_keeps_keyword_words_inside_string_values():
    raw = """
{"is_allowed": true, "company": "None GmbH", "full_name": "Alex Beispiel", "phone": "+999 333444"}
"""
    parsed = parse_llm_json(raw)
    assert parsed["is_allowed"] is True
    assert parsed["company"] == "None GmbH"


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




