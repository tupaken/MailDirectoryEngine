"""Unit tests for StorageService HTTP client helpers."""

from urllib import error
from unittest.mock import Mock

import pytest

from llmService.API import StorageService as storage_module


def test_send_storage_payload_returns_parsed_json(monkeypatch):
    """Successful HTTP responses should return parsed JSON payloads."""

    response_mock = Mock()
    response_mock.read.return_value = b'{"status":"stored"}'
    response_mock.__enter__ = Mock(return_value=response_mock)
    response_mock.__exit__ = Mock(return_value=False)

    urlopen_mock = Mock(return_value=response_mock)
    monkeypatch.setattr(storage_module.request, "urlopen", urlopen_mock)
    monkeypatch.setattr(
        storage_module,
        "STORAGE_SERVICE_ENDPOINT",
        "http://localhost:5001/store",
    )
    monkeypatch.setenv("STORAGE_SERVICE_TIMEOUT_SECONDS", "12")

    response = storage_module.send_storage_payload("/mail-export/12.eml", "12-345")

    assert response == {"status": "stored"}
    request_obj = urlopen_mock.call_args[0][0]
    assert request_obj.full_url == "http://localhost:5001/store"
    assert request_obj.get_method() == "POST"
    assert request_obj.data == b'{"sourcePath": "/mail-export/12.eml", "number": "12-345"}'
    assert urlopen_mock.call_args.kwargs["timeout"] == 12


def test_send_storage_payload_requires_endpoint(monkeypatch):
    """A missing endpoint should fail before any HTTP request is attempted."""

    monkeypatch.setattr(storage_module, "STORAGE_SERVICE_ENDPOINT", None)

    with pytest.raises(RuntimeError, match="STORAGE_SERVICE_ENDPOINT is empty"):
        storage_module.send_storage_payload("/mail-export/12.eml", "12-345")


def test_send_storage_payload_wraps_http_error(monkeypatch):
    """HTTP failures should raise a readable RuntimeError for callers."""

    class FakeHttpError(error.HTTPError):
        def __init__(self):
            super().__init__(
                url="http://localhost:5001/store",
                code=500,
                msg="Internal Server Error",
                hdrs=None,
                fp=None,
            )

        def read(self):
            return b'{"error":"storage down"}'

    monkeypatch.setattr(storage_module.request, "urlopen", Mock(side_effect=FakeHttpError()))
    monkeypatch.setattr(
        storage_module,
        "STORAGE_SERVICE_ENDPOINT",
        "http://localhost:5001/store",
    )

    with pytest.raises(RuntimeError, match="HTTP 500"):
        storage_module.send_storage_payload("/mail-export/13.eml", "13-456")
