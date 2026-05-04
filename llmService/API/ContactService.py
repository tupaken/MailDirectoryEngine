"""HTTP client for ContactService integration."""

import json
import os
from urllib import error, request

DEFAULT_CONTACT_SERVICE_ENDPOINT = "http://localhost:5000/api/contacts/observations"


def _clean_text(value: object) -> str:
    """Normalize optional values to trimmed strings."""

    if value is None:
        return ""
    return str(value).strip()


def send_canonical_contact_payload(payload: dict) -> dict:
    """Send one canonical contact payload to ContactService API."""

    endpoint = os.getenv("CONTACT_SERVICE_ENDPOINT", DEFAULT_CONTACT_SERVICE_ENDPOINT).strip()
    if not endpoint:
        raise RuntimeError("CONTACT_SERVICE_ENDPOINT is empty")

    timeout = int(os.getenv("CONTACT_SERVICE_TIMEOUT_SECONDS", "30"))
    api_key = _clean_text(os.getenv("CONTACT_SERVICE_API_KEY"))

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    req = request.Request(
        url=endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        error_text = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"ContactService returned HTTP {exc.code} for {endpoint}: {error_text}"
        ) from exc
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach ContactService endpoint {endpoint}: {exc}") from exc

    if not response_body.strip():
        return {"status": "ok"}

    try:
        parsed = json.loads(response_body)
    except json.JSONDecodeError:
        return {"status": "ok", "raw_response": response_body}

    if isinstance(parsed, dict):
        return parsed
    return {"status": "ok", "response": parsed}
