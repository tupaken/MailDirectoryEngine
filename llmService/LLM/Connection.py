"""LLM transport + orchestration entrypoint for inbox classification."""

import json
import os
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv
from ollama import Client

from .json_parser import parse_first_llm_json, parse_llm_json
from .normalization import (
    _dedupe_contacts,
    _extract_contacts,
    _extract_structured_contacts_from_mail,
    _normalize_llm_result as _normalize_llm_result_impl,
)
from .promtInbox import PROMPT_TEMPLATE

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH if ENV_PATH.exists() else None)

DISPOSITION_RELEVANT = "relevant"
DISPOSITION_IRRELEVANT = "irrelevant"
DISPOSITION_UNKNOWN = "unknown"


def _build_prompt(mail: str) -> str:
    """Render the inbox classification prompt with one mail payload."""

    return PROMPT_TEMPLATE.format(mail=mail)


def _ollama_generate(prompt: str) -> str:
    """Call Ollama generate endpoint and return raw model text."""

    host = os.getenv("LLM_ENDPOINT", "http://localhost:11434")
    model = os.getenv("LLM_MODEL", "llama3.2:1b")
    client = Client(host=host)
    response = client.generate(model=model, prompt=prompt)
    return response["response"]


def _llamacpp_generate(prompt: str) -> str:
    """Call llama.cpp OpenAI-compatible endpoint and return raw model text."""

    endpoint = os.getenv("LLM_ENDPOINT", "http://localhost:8080").rstrip("/")
    model = os.getenv("LLM_MODEL", "")
    request_url = (
        f"{endpoint}/chat/completions"
        if endpoint.endswith("/v1")
        else f"{endpoint}/v1/chat/completions"
    )

    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
    }
    if model:
        payload["model"] = model

    req = request.Request(
        url=request_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    try:
        with request.urlopen(req, timeout=timeout) as response:
            raw_response = json.loads(response.read().decode("utf-8"))
    except error.URLError as exc:
        raise RuntimeError(f"Could not reach llama.cpp endpoint at {request_url}: {exc}") from exc

    try:
        return raw_response["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise RuntimeError("llama.cpp response format is invalid.") from exc


def _normalize_llm_result(parsed: dict, mail: str) -> dict:
    """Compatibility wrapper around normalization logic."""

    return _normalize_llm_result_impl(parsed, mail)


def _normalize_llm_contacts(parsed: dict, mail: str) -> list[dict]:
    """Normalize every parsed contact and keep only allowed entries."""

    if not isinstance(parsed, dict):
        return []

    results: list[dict] = []
    for contact in _extract_contacts(parsed):
        candidate = dict(contact)
        if "is_allowed" not in candidate:
            candidate["is_allowed"] = parsed.get("is_allowed")
        normalized = _normalize_llm_result(candidate, mail)
        if normalized.get("is_allowed") is True:
            results.append(normalized)

    return _dedupe_contacts(results)


def _generate_raw_response(mail: str) -> str:
    """Generate one raw model response for the provided mail text."""

    prompt = _build_prompt(mail)
    backend = os.getenv("LLM_BACKEND", "ollama").strip().lower().replace("-", "_")

    if backend == "ollama":
        return _ollama_generate(prompt)
    if backend in {"llama_cpp", "llama.cpp", "llamacpp"}:
        return _llamacpp_generate(prompt)

    raise ValueError(
        "Unsupported LLM_BACKEND. Use one of: ollama, llama_cpp, llama.cpp, llamacpp."
    )


def llm_connection_with_disposition(mail: str) -> dict:
    """Return contacts plus disposition for downstream operated-flag decisions."""

    raw_response = _generate_raw_response(mail)
    parsed_any = parse_first_llm_json(raw_response)

    parsed_allowed: dict = {}
    try:
        parsed_allowed = parse_llm_json(raw_response)
    except RuntimeError:
        parsed_allowed = {}

    normalized_contacts = _normalize_llm_contacts(parsed_allowed, mail)
    list_contacts = _extract_structured_contacts_from_mail(mail)
    contacts = _dedupe_contacts(normalized_contacts + list_contacts)

    if contacts:
        disposition = DISPOSITION_RELEVANT
    elif isinstance(parsed_any, dict) and parsed_any.get("is_allowed") is False:
        disposition = DISPOSITION_IRRELEVANT
    else:
        disposition = DISPOSITION_UNKNOWN

    return {
        "contacts": contacts,
        "disposition": disposition,
    }


def llm_connection(mail: str) -> dict | list[dict] | None:
    """Send one mail text to configured LLM backend and return allowed result(s)."""

    decision = llm_connection_with_disposition(mail)
    contacts = decision.get("contacts", [])

    if not contacts:
        return None
    if len(contacts) == 1:
        return contacts[0]
    return contacts


def test_connection(mail: str) -> dict | list[dict] | None:
    """Backward-compatible wrapper kept for existing callers/tests."""

    return llm_connection(mail)
