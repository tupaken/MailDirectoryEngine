"""Unit tests for canonical contact payload and API client helpers."""

from urllib import error
from unittest.mock import Mock

import pytest

from llmService.contact_sync import (
    DEFAULT_CONTACT_SERVICE_ENDPOINT,
    build_canonical_contact_payload,
    send_canonical_contact_payload,
)


def test_build_canonical_contact_payload_maps_llm_shape(monkeypatch):
    """LLM normalized contact should map to the shared canonical schema."""

    monkeypatch.setenv("EWS_ACCOUNT_KEY", "bewerbung")

    payload = build_canonical_contact_payload(
        {
            "is_allowed": True,
            "full_name": "Robin Beispiel",
            "company": "Acme",
            "email": "robin.beispiel@anon.invalid",
            "phone": "+49 (151) 111222",
            "address": "Musterstrasse 1",
            "website": "anon.invalid",
        },
        source_message_id=42,
    )

    assert payload["schema_version"] == "1.0"
    assert payload["account_key"] == "bewerbung"
    assert payload["source_message_id"] == "42"
    assert payload["contact"]["given_name"] == "Robin"
    assert payload["contact"]["surname"] == "Beispiel"
    assert payload["contact"]["phones"] == [
        {"type": "business", "raw": "+49 151 111222", "e164": "+49151111222"}
    ]


def test_build_canonical_contact_payload_extracts_fax_mobile_and_other_from_source_text(
    monkeypatch,
):
    """Source text should contribute additional labeled phone numbers."""

    monkeypatch.setenv("EWS_ACCOUNT_KEY", "bewerbung")

    payload = build_canonical_contact_payload(
        {
            "is_allowed": True,
            "full_name": "Robin Beispiel",
            "phone": "+49 30 123456",
        },
        source_message_id=7,
        source_text="""
Telefon: +49 30 123456
Telefax: +49 30 123457
Mobil: +49 171 555000
Zentrale: +49 30 123458
""",
    )

    phones = payload["contact"]["phones"]
    assert {"type": "business", "raw": "+49 301 23456", "e164": "+4930123456"} in phones
    assert {"type": "fax", "raw": "+49 301 23457", "e164": "+4930123457"} in phones
    assert {"type": "mobile", "raw": "+49 171 555000", "e164": "+49171555000"} in phones
    assert {"type": "business", "raw": "+49 301 23458", "e164": "+4930123458"} in phones


def test_build_canonical_contact_payload_formats_0049_and_e164_phone_sources(monkeypatch):
    """German numbers from 0049 and e164 inputs should use the shared raw display format."""

    monkeypatch.setenv("EWS_ACCOUNT_KEY", "bewerbung")

    payload = build_canonical_contact_payload(
        {
            "is_allowed": True,
            "full_name": "Robin Beispiel",
            "phone": "0049 151 111222",
            "phone_numbers": [
                {"type": "mobile", "e164": "+491701234567"},
            ],
        },
        source_message_id=8,
    )

    phones = payload["contact"]["phones"]
    assert {"type": "business", "raw": "+49 151 111222", "e164": "+49151111222"} in phones
    assert {"type": "mobile", "raw": "+49 170 1234567", "e164": "+491701234567"} in phones


def test_build_canonical_contact_payload_keeps_non_german_international_display(monkeypatch):
    """Non-German international numbers should keep their original raw display text."""

    monkeypatch.setenv("EWS_ACCOUNT_KEY", "bewerbung")

    payload = build_canonical_contact_payload(
        {
            "is_allowed": True,
            "full_name": "Robin Beispiel",
            "phone": "+43 1 2345678",
        },
        source_message_id=10,
    )

    assert payload["contact"]["phones"] == [
        {"type": "business", "raw": "+43 1 2345678", "e164": "+4312345678"}
    ]


def test_build_canonical_contact_payload_ignores_glued_long_phone_numbers(monkeypatch):
    """Unreasonably long digit strings from source text must be filtered out."""

    monkeypatch.setenv("EWS_ACCOUNT_KEY", "bewerbung")

    payload = build_canonical_contact_payload(
        {
            "is_allowed": True,
            "full_name": "Alpha Bravo Extern",
            "phone": "+49 171 4535343",
        },
        source_message_id=9,
        source_text="""
Telefon: +49 171 4535343
Mobil: +49159076600234915907660023
""",
    )

    phones = payload["contact"]["phones"]
    assert {"type": "business", "raw": "+49 171 4535343", "e164": "+491714535343"} in phones
    assert all("6002349159" not in item["raw"] for item in phones)


def test_build_canonical_contact_payload_skips_register_numbers_and_keeps_mobile(monkeypatch):
    """Register IDs like HRB must not be extracted as phone numbers."""

    monkeypatch.setenv("EWS_ACCOUNT_KEY", "bewerbung")

    payload = build_canonical_contact_payload(
        {
            "is_allowed": True,
            "full_name": "Juliane Reinhardt-Mueller",
            "phone": "+49 (341) 3320 4342",
        },
        source_message_id=11,
        source_text="""
T: +49 (341) 3320 4342
M: 0173 3982023
Handelsregisternummer: HRB 134441 B
""",
    )

    phones = payload["contact"]["phones"]
    assert {"type": "business", "raw": "+49 341 33204342", "e164": "+4934133204342"} in phones
    assert {"type": "mobile", "raw": "+49 173 3982023", "e164": "+491733982023"} in phones
    assert all("134441" not in item["raw"] for item in phones)


def test_build_canonical_contact_payload_limits_text_phone_extraction_to_contact_context(
    monkeypatch,
):
    """Phone extraction should avoid unrelated numbers from other signature blocks."""

    monkeypatch.setenv("EWS_ACCOUNT_KEY", "bewerbung")

    payload = build_canonical_contact_payload(
        {
            "is_allowed": True,
            "full_name": "Jordan Beispiel",
            "email": "jordan.beispiel@anon.invalid",
            "phone": "+49-34292-710-12",
        },
        source_message_id=12,
        source_text="""
Mobil: +49 177 8112663
E-Mail: backup.person@anon.invalid

Von: Beispiel, Jordan <jordan.beispiel@anon.invalid>
Telefon: +49-34292-710-12
Mobil: +49-151-15343316
E-Mail: jordan.beispiel@anon.invalid
""",
    )

    phones = payload["contact"]["phones"]
    assert {"type": "business", "raw": "+49 342 9271012", "e164": "+493429271012"} in phones
    assert {"type": "mobile", "raw": "+49 151 15343316", "e164": "+4915115343316"} in phones
    assert all("+49 177 8112663" not in item["raw"] for item in phones)


def test_build_canonical_contact_payload_requires_phone():
    """Phone number is mandatory for canonical payload creation."""

    with pytest.raises(ValueError, match="contact.phone is required"):
        build_canonical_contact_payload(
            {"is_allowed": True, "full_name": "No Phone", "phone": ""},
            source_message_id=1,
        )


def test_send_canonical_contact_payload_returns_parsed_json(monkeypatch):
    """Successful HTTP responses should be parsed into dictionaries."""

    response_mock = Mock()
    response_mock.read.return_value = b'{"status":"created"}'
    response_mock.__enter__ = Mock(return_value=response_mock)
    response_mock.__exit__ = Mock(return_value=False)

    urlopen_mock = Mock(return_value=response_mock)
    monkeypatch.setattr("llmService.contact_sync.request.urlopen", urlopen_mock)
    monkeypatch.delenv("CONTACT_SERVICE_ENDPOINT", raising=False)

    response = send_canonical_contact_payload({"schema_version": "1.0"})

    assert response == {"status": "created"}
    request_obj = urlopen_mock.call_args[0][0]
    assert request_obj.full_url == DEFAULT_CONTACT_SERVICE_ENDPOINT


def test_send_canonical_contact_payload_wraps_http_error(monkeypatch):
    """HTTP failures should produce a readable RuntimeError."""

    class FakeHttpError(error.HTTPError):
        def __init__(self):
            super().__init__(
                url="http://localhost:5000/api/contacts/canonical",
                code=400,
                msg="Bad Request",
                hdrs=None,
                fp=None,
            )

        def read(self):
            return b'{"error":"bad payload"}'

    monkeypatch.setattr(
        "llmService.contact_sync.request.urlopen",
        Mock(side_effect=FakeHttpError()),
    )

    with pytest.raises(RuntimeError, match="HTTP 400"):
        send_canonical_contact_payload({"schema_version": "1.0"})



