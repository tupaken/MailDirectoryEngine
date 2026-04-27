"""Unit tests for StorageService HTTP client helpers."""

from urllib import error
from unittest.mock import Mock

import pytest

from llmService.API import StorageService as storage_module
from llmService.API.StorageService import (
    STORAGE_MESSAGE_DESTINATION_NOT_FOUND,
    StorageServiceError,
)


def test_send_storage_payload_returns_parsed_json(monkeypatch):
    """Successful HTTP responses should return parsed JSON payloads."""

    response_mock = Mock()
    response_mock.read.return_value = b'{"message":"200"}'
    response_mock.__enter__ = Mock(return_value=response_mock)
    response_mock.__exit__ = Mock(return_value=False)

    urlopen_mock = Mock(return_value=response_mock)
    monkeypatch.setattr(storage_module.request, "urlopen", urlopen_mock)
    monkeypatch.setenv("STORAGE_SERVICE_ENDPOINT", "http://localhost:5001/store")
    monkeypatch.setenv("STORAGE_SERVICE_TIMEOUT_SECONDS", "12")

    response = storage_module.send_storage_payload("/mail-export/12.eml", "12-345")

    assert response == {"message": "200"}
    request_obj = urlopen_mock.call_args[0][0]
    assert request_obj.full_url == "http://localhost:5001/store"
    assert request_obj.get_method() == "POST"
    assert request_obj.data == b'{"sourcePath": "/mail-export/12.eml", "number": "12-345"}'
    assert urlopen_mock.call_args.kwargs["timeout"] == 12


def test_send_storage_payload_requires_endpoint(monkeypatch):
    """A missing endpoint should fail before any HTTP request is attempted."""

    monkeypatch.delenv("STORAGE_SERVICE_ENDPOINT", raising=False)

    with pytest.raises(RuntimeError, match="STORAGE_SERVICE_ENDPOINT is empty"):
        storage_module.send_storage_payload("/mail-export/12.eml", "12-345")


def test_send_storage_payload_wraps_http_error_with_status_and_message(monkeypatch):
    """HTTP failures should preserve the response code and structured message for callers."""

    class FakeHttpError(error.HTTPError):
        def __init__(self):
            super().__init__(
                url="http://localhost:5001/store",
                code=404,
                msg="Not Found",
                hdrs=None,
                fp=None,
            )

        def read(self):
            return b'{"message":"destination_not_found"}'

    monkeypatch.setattr(storage_module.request, "urlopen", Mock(side_effect=FakeHttpError()))
    monkeypatch.setenv("STORAGE_SERVICE_ENDPOINT", "http://localhost:5001/store")

    with pytest.raises(StorageServiceError, match="HTTP 404") as exc_info:
        storage_module.send_storage_payload("/mail-export/13.eml", "13-456")

    assert exc_info.value.status_code == 404
    assert exc_info.value.response_message == STORAGE_MESSAGE_DESTINATION_NOT_FOUND
