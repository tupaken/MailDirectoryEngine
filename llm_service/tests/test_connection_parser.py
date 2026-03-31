"""Unit tests for parsing LLM JSON output."""

import pytest

from llm_service.LLM.Connection import _normalize_llm_result, parse_llm_json


def test_parse_llm_json_accepts_clean_json():
    raw = '{"is_allowed": true, "contacts": [{"company": "Company Inc."}]}'
    parsed = parse_llm_json(raw)
    assert parsed["is_allowed"] is True
    assert parsed["contacts"][0]["company"] == "Company Inc."


def test_parse_llm_json_handles_markdown_fences_and_trailing_text():
    raw = """```json
{"is_allowed": false}
```
extra text that should be ignored
{"is_allowed": true}
"""
    parsed = parse_llm_json(raw)
    assert parsed == {"is_allowed": False}


def test_parse_llm_json_handles_python_literal_output():
    raw = "{'is_allowed': True, 'contacts': [{'company': 'Company Inc.'}]}"
    parsed = parse_llm_json(raw)
    assert parsed["is_allowed"] is True
    assert parsed["contacts"][0]["company"] == "Company Inc."


def test_parse_llm_json_handles_quoted_multiline_json_blob():
    raw = (
        "\"{\n"
        "  \\\"is_allowed\\\": true,\n"
        "  \\\"contacts\\\": [\n"
        "    {\n"
        "      \\\"full_name\\\": \\\"John Doe\\\",\n"
        "      \\\"company\\\": \\\"Example Inc.\\\"\n"
        "    }\n"
        "  ]\n"
        "}\""
    )
    parsed = parse_llm_json(raw)
    assert parsed["is_allowed"] is True
    assert parsed["contacts"][0]["full_name"] == "John Doe"


def test_parse_llm_json_raises_when_no_json_object():
    with pytest.raises(RuntimeError, match="No JSON object found"):
        parse_llm_json("no object here")


def test_normalize_result_drops_contacts_when_not_allowed():
    parsed = {
        "is_allowed": False,
        "contacts": [{"full_name": "John Doe", "email": "john@example.com"}],
    }
    result = _normalize_llm_result(parsed, "John Doe john@example.com")
    assert result == {"is_allowed": False}


def test_normalize_result_rejects_root_contact_shape():
    parsed = {"full_name": "John Doe", "company": "ABC Corporation"}
    result = _normalize_llm_result(parsed, "John Doe at ABC Corporation")
    assert result == {"is_allowed": False}


def test_normalize_result_removes_hallucinated_values():
    parsed = {
        "is_allowed": True,
        "contacts": [
            {"full_name": "John Doe", "company": "ABC Corporation", "email": "john@example.com"}
        ],
    }
    result = _normalize_llm_result(parsed, "Reach us at info@real-company.com")
    assert result == {"is_allowed": False}


def test_normalize_result_keeps_only_values_found_in_mail():
    parsed = {
        "is_allowed": True,
        "contacts": [
            {
                "full_name": "John Doe",
                "company": "Fake Corp",
                "email": "john.doe@abc.com",
                "phone": "+1 555 123 4567",
                "address": "Invented Street 9",
                "website": "abc.com",
            }
        ],
    }
    mail = "Contact: John Doe, john.doe@abc.com, phone +1 (555) 123-4567, website https://abc.com"
    result = _normalize_llm_result(parsed, mail)
    assert result == {
        "is_allowed": True,
        "contacts": [
            {
                "full_name": "John Doe",
                "company": "",
                "email": "john.doe@abc.com",
                "phone": "+1 555 123 4567",
                "address": "",
                "website": "abc.com",
            }
        ],
    }
