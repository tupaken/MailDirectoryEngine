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
            "full_name": "Anna Meyer",
            "company": "Acme",
            "email": "anna@acme.de",
            "phone": "+49 (151) 111222",
            "address": "Musterstrasse 1",
            "website": "acme.de",
        },
        source_message_id=42,
    )

    assert payload["schema_version"] == "1.0"
    assert payload["account_key"] == "bewerbung"
    assert payload["source_message_id"] == "42"
    assert payload["contact"]["given_name"] == "Anna"
    assert payload["contact"]["surname"] == "Meyer"
    assert payload["contact"]["phones"] == [
        {"type": "business", "raw": "+49 (151) 111222", "e164": "+49151111222"}
    ]


def test_build_canonical_contact_payload_extracts_fax_mobile_and_other_from_source_text(
    monkeypatch,
):
    """Source text should contribute additional labeled phone numbers."""

    monkeypatch.setenv("EWS_ACCOUNT_KEY", "bewerbung")

    payload = build_canonical_contact_payload(
        {
            "is_allowed": True,
            "full_name": "Anna Meyer",
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
    assert {"type": "business", "raw": "+49 30 123456", "e164": "+4930123456"} in phones
    assert {"type": "fax", "raw": "+49 30 123457", "e164": "+4930123457"} in phones
    assert {"type": "mobile", "raw": "+49 171 555000", "e164": "+49171555000"} in phones
    assert {"type": "business", "raw": "+49 30 123458", "e164": "+4930123458"} in phones


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
