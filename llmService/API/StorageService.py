"""HTTP client helpers for forwarding sent-mail files to StorageService."""

import json
import os
from urllib import error, request

STORAGE_MESSAGE_DESTINATION_NOT_FOUND = "destination_not_found"
STORAGE_MESSAGE_SOURCE_NOT_FOUND = "source_not_found"
STORAGE_MESSAGE_SHARE_UNAVAILABLE = "share_unavailable"
STORAGE_MESSAGE_COPY_FAILED = "copy_failed"


class StorageServiceError(RuntimeError):
    """Raised when StorageService returns a structured HTTP error response."""

    def __init__(self, endpoint: str, status_code: int, response_message: str):
        """Store the failed endpoint, HTTP status, and structured error message."""

        self.endpoint = endpoint
        self.status_code = status_code
        self.response_message = response_message
        super().__init__(
            f"StorageService returned HTTP {status_code} for {endpoint}: {response_message}"
        )


def send_storage_payload(source_path: str, number: str, target_file_name:str) -> dict:
    """Send one sent-mail file path, project number and targetFileName to StorageService."""

    endpoint = os.getenv("STORAGE_SERVICE_ENDPOINT")
    if not endpoint:
        raise RuntimeError("STORAGE_SERVICE_ENDPOINT is empty")

    timeout = int(os.getenv("STORAGE_SERVICE_TIMEOUT_SECONDS", "30"))

    payload = {
        "sourcePath": source_path,
        "number": number,
        "targetFileName": target_file_name,
    }

    req = request.Request(
        url=endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(error_text)
        except json.JSONDecodeError:
            payload = None

        response_message = (
            str(payload.get("message"))
            if isinstance(payload, dict) and payload.get("message") is not None
            else error_text
        )
        raise StorageServiceError(endpoint, exc.code, response_message) from exc
    except error.URLError as exc:
        raise RuntimeError(
            f"Could not reach StorageService endpoint {endpoint}: {exc}"
        ) from exc

    return json.loads(body)
