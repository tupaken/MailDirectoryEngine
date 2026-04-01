"""JSON parsing helpers for extracting structured LLM output."""

import ast
import json
import re


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences around JSON-like model output."""

    cleaned = re.sub(r"```(?:json)?", "", text, flags=re.IGNORECASE)
    return cleaned.replace("```", "").strip()


def _extract_json_object_candidates(text: str) -> list[str]:
    """Extract balanced JSON object substrings from arbitrary text."""

    candidates: list[str] = []
    depth = 0
    start = None
    in_string = False
    quote_char = ""
    escaped = False

    for idx, char in enumerate(text):
        if in_string:
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote_char:
                in_string = False
            continue

        if char in {'"', "'"}:
            in_string = True
            quote_char = char
            continue

        if char == "{":
            if depth == 0:
                start = idx
            depth += 1
            continue

        if char == "}" and depth > 0:
            depth -= 1
            if depth == 0 and start is not None:
                candidates.append(text[start : idx + 1])
                start = None

    return candidates


def _replace_unquoted_keywords(value: str, replacements: dict[str, str]) -> str:
    """Replace literal keywords only outside quoted strings."""

    result: list[str] = []
    idx = 0
    in_string = False
    quote_char = ""
    escaped = False
    ordered_replacements = sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True)

    while idx < len(value):
        char = value[idx]

        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote_char:
                in_string = False
            idx += 1
            continue

        if char in {'"', "'"}:
            in_string = True
            quote_char = char
            result.append(char)
            idx += 1
            continue

        replaced = False
        for source, target in ordered_replacements:
            if not value.startswith(source, idx):
                continue

            before = value[idx - 1] if idx > 0 else ""
            end_idx = idx + len(source)
            after = value[end_idx] if end_idx < len(value) else ""
            if (before.isalnum() or before == "_") or (after.isalnum() or after == "_"):
                continue

            result.append(target)
            idx = end_idx
            replaced = True
            break

        if replaced:
            continue

        result.append(char)
        idx += 1

    return "".join(result)


def _load_json_object(text: str) -> dict | None:
    """Parse one JSON/Python-like object string into a JSON-compatible dict."""

    normalized = text.strip()
    if not normalized:
        return None

    # Normalize common JSON-like output patterns from LLMs.
    normalized = normalized.replace("\u201c", '"').replace("\u201d", '"')
    normalized = normalized.replace("\u2018", "'").replace("\u2019", "'")
    normalized = _replace_unquoted_keywords(
        normalized,
        {"True": "true", "False": "false", "None": "null"},
    )
    normalized = re.sub(r",\s*([}\]])", r"\1", normalized)

    try:
        parsed = json.loads(normalized)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    # Fallback for single quotes / Python literal style output.
    pythonish = _replace_unquoted_keywords(
        normalized,
        {"true": "True", "false": "False", "null": "None"},
    )
    try:
        parsed = ast.literal_eval(pythonish)
    except (SyntaxError, ValueError):
        return None

    if isinstance(parsed, dict):
        return json.loads(json.dumps(parsed))
    return None


def parse_llm_json(raw: str) -> dict:
    """Parse and return the first allowed JSON object found in LLM output."""

    if not raw or raw.strip() == "":
        raise RuntimeError("LLM returned empty response")

    cleaned = _strip_markdown_fences(raw.strip())
    candidate_texts = [cleaned]

    # Handle quoted JSON blobs (e.g. "\"{\\\"is_allowed\\\": true}\"").
    try:
        unwrapped = json.loads(cleaned)
        if isinstance(unwrapped, str):
            candidate_texts.append(unwrapped)
    except json.JSONDecodeError:
        pass

    for candidate_text in candidate_texts:
        object_candidates = _extract_json_object_candidates(candidate_text)
        if not object_candidates:
            parsed = _load_json_object(candidate_text)
            if parsed is not None and parsed.get("is_allowed") is True:
                return parsed
            continue

        for obj in object_candidates:
            parsed = _load_json_object(obj)
            if parsed is not None and parsed.get("is_allowed") is True:
                return parsed

    raise RuntimeError(f"Could not parse JSON object from LLM output:\n{raw}")
