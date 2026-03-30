"""LLM prompt wrapper used to classify inbox text payloads."""

import json
import os
from pathlib import Path
from urllib import error, request

from dotenv import load_dotenv
from ollama import Client

ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=ENV_PATH if ENV_PATH.exists() else None)

PROMPT_TEMPLATE = """
You will receive exactly one email text.

Your task is to decide whether the email is clearly related to a real company, business, organization, office, agency, or other commercial entity.

Return True ONLY if there is clear evidence of a company, such as at least one of the following:
- a company name
- a business email domain
- a website
- a phone number together with business context
- a postal address together with business context
- legal entity terms such as GmbH, AG, Ltd, LLC, Inc, UG, KG, e.V.
- words indicating an organization or business context

Return False if:
- the text only contains a personal name
- the text only contains a generic email or placeholder
- the text only contains test data
- the text contains words like test, demo, sample, dummy, example without clear company evidence
- there is no clear company or organization reference

Output format:
If True, output exactly:

True
Name and surname:
Company:
Email:
Phone:
Address:
Website:

If False, output exactly:

False

Rules:
- Only one final answer
- No explanations
- No notes
- No extra text
- Missing fields must stay empty
- Generic placeholders like test, Test1, Test2, demo, sample do not count as company evidence
- A single email address alone does not make it company-related
- A single name alone does not make it company-related

Email:
\"\"\"{mail}\"\"\"
""".strip()


def _build_prompt(mail: str) -> str:
    return PROMPT_TEMPLATE.format(mail=mail)


def _ollama_generate(prompt: str) -> str:
    host = os.getenv("LLM_ENDPOINT", "http://localhost:11434")
    model = os.getenv("LLM_MODEL", "llama3.2:1b")
    client = Client(host=host)
    response = client.generate(model=model, prompt=prompt)
    return response["response"]


def _llamacpp_generate(prompt: str) -> str:
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


def test_connection(mail: str) -> str:
    """Send one mail text to configured LLM backend and return raw response text."""

    prompt = _build_prompt(mail)
    backend = os.getenv("LLM_BACKEND", "ollama").strip().lower().replace("-", "_")

    if backend == "ollama":
        return _ollama_generate(prompt)
    if backend in {"llama_cpp", "llama.cpp", "llamacpp"}:
        return _llamacpp_generate(prompt)

    raise ValueError(
        "Unsupported LLM_BACKEND. Use one of: ollama, llama_cpp, llama.cpp, llamacpp."
    )
