"""Unit tests for backend dispatch in LLM.Connection."""

import json
import unittest
from unittest.mock import Mock, patch

from llmService.LLM.Connection import (
    _split_mail_context_and_signature,
    _strip_mail_preamble,
    _strip_signature_preamble,
    llm_connection_with_disposition,
    test_connection as run_llm_connection,
)


class TestConnectionTests(unittest.TestCase):
    """Ensure backend selection and parsing/normalization flow works."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("llmService.LLM.Connection._normalize_llm_result")
    @patch("llmService.LLM.Connection._extract_signature_contacts_from_mail", return_value=[])
    @patch("llmService.LLM.Connection.parse_llm_json")
    @patch("llmService.LLM.Connection.Client")
    def test_test_connection_calls_ollama_backend(
        self,
        client_cls,
        parse_mock,
        _signature_extract_mock,
        normalize_mock,
    ):
        """Ollama should be called with default host/model and parsed output."""

        fake_client = Mock()
        fake_client.generate.return_value = {"response": "RAW-OLLAMA"}
        client_cls.return_value = fake_client
        parse_mock.return_value = {"is_allowed": True}
        normalize_mock.return_value = {"is_allowed": True, "full_name": "Alex Beispiel"}

        mail = """Alex Beispiel ACME +49 123456
Mit freundlichen Gruessen
Alex Beispiel
Telefon: +49 123456"""
        result = run_llm_connection(mail)

        self.assertEqual(2, client_cls.call_count)
        client_cls.assert_any_call(host="http://localhost:11434")
        self.assertEqual(2, fake_client.generate.call_count)
        prompt_calls = fake_client.generate.call_args_list
        self.assertEqual("llama3.2:1b", prompt_calls[0].kwargs["model"])
        self.assertIn("Alex Beispiel ACME +49 123456", prompt_calls[0].kwargs["prompt"])
        self.assertIn("Telefon: +49 123456", prompt_calls[1].kwargs["prompt"])
        self.assertNotIn("Mit freundlichen Gruessen", prompt_calls[1].kwargs["prompt"])
        self.assertIn("email context text", prompt_calls[0].kwargs["prompt"].lower())
        self.assertIn("email signature block", prompt_calls[1].kwargs["prompt"].lower())
        self.assertEqual(2, parse_mock.call_count)
        self.assertEqual(2, normalize_mock.call_count)
        normalize_mock.assert_any_call({"is_allowed": True}, mail)
        self.assertEqual({"is_allowed": True, "full_name": "Alex Beispiel"}, result)

    @patch.dict(
        "os.environ",
        {
            "LLM_BACKEND": "llama_cpp",
            "LLM_ENDPOINT": "http://localhost:8080",
            "LLM_MODEL": "tiny-test-model",
        },
        clear=True,
    )
    @patch("llmService.LLM.Connection._normalize_llm_result")
    @patch("llmService.LLM.Connection._extract_signature_contacts_from_mail", return_value=[])
    @patch("llmService.LLM.Connection.parse_llm_json")
    @patch("llmService.LLM.Connection.request.urlopen")
    def test_test_connection_calls_llamacpp_backend(
        self,
        urlopen_mock,
        parse_mock,
        _signature_extract_mock,
        normalize_mock,
    ):
        """llama.cpp backend should use OpenAI-compatible chat endpoint."""

        fake_http_response = Mock()
        fake_http_response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "RAW-LLAMACPP"}}]}
        ).encode("utf-8")
        urlopen_mock.return_value.__enter__.return_value = fake_http_response
        parse_mock.return_value = {"is_allowed": True}
        normalize_mock.return_value = {"is_allowed": True, "full_name": "Blair Beispiel"}

        mail = """Blair Beispiel ACME +49 555000
Mit freundlichen Gruessen
Blair Beispiel
Telefon: +49 555000"""
        result = run_llm_connection(mail)

        self.assertEqual(2, urlopen_mock.call_count)
        request_obj = urlopen_mock.call_args_list[0].args[0]
        payload = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual("http://localhost:8080/v1/chat/completions", request_obj.full_url)
        self.assertEqual("tiny-test-model", payload["model"])
        self.assertIn("Blair Beispiel ACME +49 555000", payload["messages"][0]["content"])
        self.assertEqual(2, parse_mock.call_count)
        self.assertEqual(2, normalize_mock.call_count)
        normalize_mock.assert_any_call({"is_allowed": True}, mail)
        self.assertEqual({"is_allowed": True, "full_name": "Blair Beispiel"}, result)

    @patch.dict("os.environ", {"LLM_BACKEND": "unknown"}, clear=True)
    def test_test_connection_raises_for_unknown_backend(self):
        """Unexpected backend names should fail fast with a clear error."""

        with self.assertRaises(ValueError):
            run_llm_connection("Any Mail")

    @patch.dict("os.environ", {}, clear=True)
    @patch("llmService.LLM.Connection.parse_llm_json", side_effect=RuntimeError("bad output"))
    @patch("llmService.LLM.Connection.Client")
    def test_test_connection_returns_none_when_parser_fails(self, client_cls, _parse_mock):
        """Parser failures should be treated as filtered/invalid output."""

        fake_client = Mock()
        fake_client.generate.return_value = {"response": "RAW-OLLAMA"}
        client_cls.return_value = fake_client

        result = run_llm_connection("Alex Beispiel")
        self.assertIsNone(result)

    @patch.dict("os.environ", {}, clear=True)
    @patch("llmService.LLM.Connection.parse_llm_json", side_effect=RuntimeError("bad output"))
    @patch("llmService.LLM.Connection.Client")
    def test_test_connection_extracts_all_structured_contacts_when_parser_fails(
        self, client_cls, _parse_mock
    ):
        """Structured contact lists should still be extracted without valid LLM JSON."""

        fake_client = Mock()
        fake_client.generate.return_value = {"response": "RAW-OLLAMA"}
        client_cls.return_value = fake_client

        mail = """
Org Alpha Services - Morgan Beispiel; +999 170 1112233; morgan.beispiel@anon.invalid
Org Beta Technik - Riley Beispiel; +999 351 5558800; service@anon.invalid
"""
        result = run_llm_connection(mail)

        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(["Morgan Beispiel", "Riley Beispiel"], [item["full_name"] for item in result])

    @patch("llmService.LLM.Connection._generate_raw_response", return_value='{"is_allowed": false}')
    @patch("llmService.LLM.Connection.parse_first_llm_json", return_value={"is_allowed": False})
    @patch("llmService.LLM.Connection.parse_llm_json", side_effect=RuntimeError("bad output"))
    @patch("llmService.LLM.Connection._extract_structured_contacts_from_mail", return_value=[])
    def test_llm_connection_with_disposition_sets_irrelevant_when_explicit_false(
        self,
        _extract_structured_mock,
        _parse_allowed_mock,
        _parse_any_mock,
        _raw_mock,
    ):
        decision = llm_connection_with_disposition("mail")
        self.assertEqual("irrelevant", decision["disposition"])
        self.assertEqual([], decision["contacts"])

    @patch("llmService.LLM.Connection._generate_raw_response", return_value="no json")
    @patch("llmService.LLM.Connection.parse_first_llm_json", return_value=None)
    @patch("llmService.LLM.Connection.parse_llm_json", side_effect=RuntimeError("bad output"))
    @patch("llmService.LLM.Connection._extract_structured_contacts_from_mail", return_value=[])
    def test_llm_connection_with_disposition_sets_unknown_when_no_clear_signal(
        self,
        _extract_structured_mock,
        _parse_allowed_mock,
        _parse_any_mock,
        _raw_mock,
    ):
        decision = llm_connection_with_disposition("mail")
        self.assertEqual("unknown", decision["disposition"])
        self.assertEqual([], decision["contacts"])

    @patch(
        "llmService.LLM.Connection._generate_raw_response",
        side_effect=['{"is_allowed": false}', "no json"],
    )
    @patch(
        "llmService.LLM.Connection.parse_first_llm_json",
        side_effect=[{"is_allowed": False}, None],
    )
    @patch("llmService.LLM.Connection.parse_llm_json", side_effect=RuntimeError("bad output"))
    @patch("llmService.LLM.Connection._extract_structured_contacts_from_mail", return_value=[])
    def test_llm_connection_with_disposition_stays_unknown_when_only_one_segment_false(
        self,
        _extract_structured_mock,
        _parse_allowed_mock,
        _parse_any_mock,
        _raw_mock,
    ):
        decision = llm_connection_with_disposition(
            """mail
Mit freundlichen Gruessen
Name
Telefon: +49 1"""
        )
        self.assertEqual("unknown", decision["disposition"])
        self.assertEqual([], decision["contacts"])

    @patch(
        "llmService.LLM.Connection._generate_raw_response",
        side_effect=[
            '{"is_allowed": true, "full_name": "", "company": "", "email": "", "phone": ""}',
            '{"is_allowed": true, "full_name": "", "company": "", "email": "", "phone": ""}',
        ],
    )
    @patch(
        "llmService.LLM.Connection.parse_first_llm_json",
        side_effect=[{"is_allowed": True}, {"is_allowed": True}],
    )
    @patch(
        "llmService.LLM.Connection.parse_llm_json",
        side_effect=[
            {"is_allowed": True, "full_name": "", "company": "", "email": "", "phone": ""},
            {"is_allowed": True, "full_name": "", "company": "", "email": "", "phone": ""},
        ],
    )
    @patch("llmService.LLM.Connection._extract_structured_contacts_from_mail", return_value=[])
    def test_llm_connection_with_disposition_sets_irrelevant_when_all_segments_true_but_invalid(
        self,
        _extract_structured_mock,
        _parse_allowed_mock,
        _parse_any_mock,
        _raw_mock,
    ):
        decision = llm_connection_with_disposition(
            """mail
Mit freundlichen Gruessen
signature"""
        )
        self.assertEqual("irrelevant", decision["disposition"])
        self.assertEqual([], decision["contacts"])

    @patch("llmService.LLM.Connection._generate_raw_response", return_value='{"is_allowed": false}')
    @patch("llmService.LLM.Connection.parse_first_llm_json", return_value={"is_allowed": False})
    @patch("llmService.LLM.Connection.parse_llm_json", side_effect=RuntimeError("bad output"))
    @patch("llmService.LLM.Connection._extract_structured_contacts_from_mail", return_value=[])
    def test_llm_connection_with_disposition_sets_irrelevant_when_context_false_and_no_signature(
        self,
        _extract_structured_mock,
        _parse_allowed_mock,
        _parse_any_mock,
        _raw_mock,
    ):
        decision = llm_connection_with_disposition("mail without signature")
        self.assertEqual("irrelevant", decision["disposition"])
        self.assertEqual([], decision["contacts"])

    def test_split_mail_context_and_signature_keeps_signature_separate(self):
        mail = """
        Hallo Team,
        bitte ruft mich zurueck.

Mit freundlichen Gruessen
Herr Dr. Taylor Beispiel
Muster GmbH
Telefon: +49 30 123456
"""
        context, signature = _split_mail_context_and_signature(mail)
        self.assertIn("bitte ruft mich zurueck", context)
        self.assertNotIn("Mit freundlichen Gruessen", signature)
        self.assertNotIn("Taylor Beispiel", signature)
        self.assertTrue(signature.startswith("Muster GmbH"))
        self.assertIn("Telefon: +49 30 123456", signature)

    def test_strip_signature_preamble_removes_signoff_and_name(self):
        signature = """
Mit freundlichen Gruessen
Herr Dr. Taylor Beispiel
Muster GmbH
Telefon: +49 30 123456
"""
        result = _strip_signature_preamble(signature)

        self.assertEqual("Muster GmbH\nTelefon: +49 30 123456", result)

    def test_strip_mail_preamble_removes_headers_and_greeting(self):
        mail = """
Von: Max Mustermann
Gesendet: Dienstag, 28. April 2026 09:15
An: Info
Betreff: Rueckruf

Sehr geehrte Damen und Herren,

bitte rufen Sie mich zurueck.
"""
        result = _strip_mail_preamble(mail)

        self.assertEqual("bitte rufen Sie mich zurueck.", result)

    def test_strip_mail_preamble_removes_greeting_with_typo(self):
        mail = """
Sehr gehrte Damen und Herren,

anbei erhalten Sie unsere Kontaktdaten.
"""
        result = _strip_mail_preamble(mail)

        self.assertEqual("anbei erhalten Sie unsere Kontaktdaten.", result)

    def test_strip_mail_preamble_keeps_inline_content(self):
        mail = "Hallo Herr Mueller, bitte rufen Sie mich zurueck."

        result = _strip_mail_preamble(mail)

        self.assertEqual(mail, result)


if __name__ == "__main__":
    unittest.main()


