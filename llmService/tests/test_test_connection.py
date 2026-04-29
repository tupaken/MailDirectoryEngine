"""Unit tests for backend dispatch in LLM.Connection."""

import json
import unittest
from unittest.mock import Mock, patch

from llmService.LLM.Connection import (
    _split_mail_context_and_signature,
    _split_mail_thread,
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
        normalize_mock.return_value = {"is_allowed": True, "full_name": "Alex Smith"}

        mail = """Alex Smith ACME +49 123456
Kind regards
Alex Smith
Telefon: +49 123456"""
        result = run_llm_connection(mail)

        self.assertEqual(2, client_cls.call_count)
        client_cls.assert_any_call(host="http://localhost:11434")
        self.assertEqual(2, fake_client.generate.call_count)
        prompt_calls = fake_client.generate.call_args_list
        self.assertEqual("llama3.2:1b", prompt_calls[0].kwargs["model"])
        self.assertIn("Alex Smith ACME +49 123456", prompt_calls[0].kwargs["prompt"])
        self.assertIn("Telefon: +49 123456", prompt_calls[1].kwargs["prompt"])
        self.assertNotIn("Kind regards", prompt_calls[1].kwargs["prompt"])
        self.assertIn("email context text", prompt_calls[0].kwargs["prompt"].lower())
        self.assertIn("email signature block", prompt_calls[1].kwargs["prompt"].lower())
        self.assertEqual(2, parse_mock.call_count)
        self.assertEqual(2, normalize_mock.call_count)
        normalize_mock.assert_any_call({"is_allowed": True}, "Alex Smith ACME +49 123456")
        normalize_mock.assert_any_call({"is_allowed": True}, "Telefon: +49 123456")
        self.assertEqual({"is_allowed": True, "full_name": "Alex Smith"}, result)

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
        normalize_mock.return_value = {"is_allowed": True, "full_name": "Blair Smith"}

        mail = """Blair Smith ACME +49 555000
Kind regards
Blair Smith
Telefon: +49 555000"""
        result = run_llm_connection(mail)

        self.assertEqual(2, urlopen_mock.call_count)
        request_obj = urlopen_mock.call_args_list[0].args[0]
        payload = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual("http://localhost:8080/v1/chat/completions", request_obj.full_url)
        self.assertEqual("tiny-test-model", payload["model"])
        self.assertIn("Blair Smith ACME +49 555000", payload["messages"][0]["content"])
        self.assertEqual(2, parse_mock.call_count)
        self.assertEqual(2, normalize_mock.call_count)
        normalize_mock.assert_any_call({"is_allowed": True}, "Blair Smith ACME +49 555000")
        normalize_mock.assert_any_call({"is_allowed": True}, "Telefon: +49 555000")
        self.assertEqual({"is_allowed": True, "full_name": "Blair Smith"}, result)

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

        result = run_llm_connection("Alex Smith")
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
Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid
Org Beta Tech - Riley Smith; +999 351 5558800; service@anon.invalid
"""
        result = run_llm_connection(mail)

        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(["Morgan Smith", "Riley Smith"], [item["full_name"] for item in result])

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
Kind regards
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
Kind regards
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

    @patch("llmService.LLM.Connection._generate_raw_response", return_value='{"is_allowed": false}')
    @patch("llmService.LLM.Connection._extract_signature_contacts_from_mail", return_value=[])
    @patch("llmService.LLM.Connection._extract_structured_contacts_from_mail", return_value=[])
    def test_llm_connection_processes_each_thread_mail_as_own_segments(
        self,
        _extract_structured_mock,
        _extract_signature_mock,
        raw_mock,
    ):
        mail = """
Dear Ms. Smith,

please call me back.

Kind regards
Taylor Smith
Acme GmbH
Telefon: +49 30 123456

From: Old Contact <alt@example.invalid>
Gesendet: Montag, 27. April 2026 15:30
To: Max Sampleman
Subject: Old email

Dear Sir or Madam,
old email.

Best regards
Old Sender
Old GmbH
Telefon: +49 99 999999
"""
        decision = llm_connection_with_disposition(mail)

        self.assertEqual("irrelevant", decision["disposition"])
        self.assertEqual([], decision["contacts"])
        self.assertEqual(4, raw_mock.call_count)
        self.assertEqual(
            ["context", "signature", "context", "signature"],
            [call.kwargs["query_type"] for call in raw_mock.call_args_list],
        )

    @patch("llmService.LLM.Connection._generate_raw_response", return_value='{\"is_allowed\": false}')
    @patch("llmService.LLM.Connection._extract_signature_contacts_from_mail", return_value=[])
    def test_llm_connection_keeps_local_source_text_for_structured_contact_lists(
        self,
        _extract_signature_mock,
        _raw_mock,
    ):
        mail = """
Wie besprochen sind dies die jeweiligen Ansprechpartner:
Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid
Org Beta Tech - Riley Smith; +999 351 5558800; service@anon.invalid
"""

        decision = llm_connection_with_disposition(mail)

        self.assertEqual(2, len(decision["contacts"]))
        self.assertEqual(
            "Org Alpha Services - Morgan Smith; +999 170 1112233; morgan.smith@anon.invalid",
            decision["contacts"][0]["_source_text"],
        )
        self.assertEqual(
            "Org Beta Tech - Riley Smith; +999 351 5558800; service@anon.invalid",
            decision["contacts"][1]["_source_text"],
        )

    @patch(
        "llmService.LLM.Connection._generate_raw_response",
        side_effect=['{"is_allowed": false}', '{"is_allowed": false}'],
    )
    @patch(
        "llmService.LLM.Connection.parse_first_llm_json",
        side_effect=[{"is_allowed": False}, {"is_allowed": False}],
    )
    @patch(
        "llmService.LLM.Connection.parse_llm_json",
        side_effect=[{"is_allowed": False}, {"is_allowed": False}],
    )
    @patch("llmService.LLM.Connection._extract_structured_contacts_from_mail", return_value=[])
    def test_llm_connection_keeps_signature_name_for_deterministic_signature_extraction(
        self,
        _extract_structured_mock,
        _parse_allowed_mock,
        _parse_any_mock,
        _raw_mock,
    ):
        mail = """
Hello team,

in der Anlage erhalten Sie

Kind regards
Taylor Smith
-Vermessungstechniker-
PLANUNGSBUERO BEISPIEL LLC
Telefon: +49 30 123456
Mobil: +49 151 222333
E-Mail:
taylor.smith@anon.invalid
"""

        decision = llm_connection_with_disposition(mail)

        self.assertEqual("relevant", decision["disposition"])
        self.assertEqual(1, len(decision["contacts"]))
        self.assertEqual("Taylor Smith", decision["contacts"][0]["full_name"])
        self.assertIn("Taylor Smith", decision["contacts"][0]["_source_text"])

    @patch(
        "llmService.LLM.Connection._generate_raw_response",
        side_effect=['{"is_allowed": false}', '{"is_allowed": false}'],
    )
    @patch(
        "llmService.LLM.Connection.parse_first_llm_json",
        side_effect=[{"is_allowed": False}, {"is_allowed": False}],
    )
    @patch(
        "llmService.LLM.Connection.parse_llm_json",
        side_effect=[{"is_allowed": False}, {"is_allowed": False}],
    )
    @patch("llmService.LLM.Connection._extract_signature_contacts_from_mail", return_value=[])
    @patch("llmService.LLM.Connection._extract_structured_contacts_from_mail", return_value=[])
    def test_llm_connection_normalizes_context_and_signature_against_their_own_segments(
        self,
        _extract_structured_mock,
        _extract_signature_mock,
        _parse_allowed_mock,
        _parse_any_mock,
        _raw_mock,
    ):
        seen_sources: list[str] = []

        def fake_normalize(_parsed, source_mail):
            seen_sources.append(source_mail)
            return []

        mail = """
Hello team,
please call me back.

Kind regards
Taylor Smith
Acme GmbH
Telefon: +49 30 123456
"""

        with patch("llmService.LLM.Connection._normalize_llm_contacts", side_effect=fake_normalize):
            decision = llm_connection_with_disposition(mail)

        self.assertEqual("irrelevant", decision["disposition"])
        self.assertEqual([], decision["contacts"])
        self.assertEqual(2, len(seen_sources))
        self.assertIn("please call me back", seen_sources[0])
        self.assertNotIn("Telefon: +49 30 123456", seen_sources[0])
        self.assertIn("Acme GmbH", seen_sources[1])
        self.assertIn("Telefon: +49 30 123456", seen_sources[1])

    def test_split_mail_context_and_signature_keeps_signature_separate(self):
        mail = """
        Hello team,
        please call me back.

Kind regards
Dr. Taylor Smith
Acme GmbH
Telefon: +49 30 123456
"""
        context, signature = _split_mail_context_and_signature(mail)
        self.assertIn("please call me back", context)
        self.assertNotIn("Kind regards", signature)
        self.assertNotIn("Taylor Smith", signature)
        self.assertTrue(signature.startswith("Acme GmbH"))
        self.assertIn("Telefon: +49 30 123456", signature)

    def test_strip_signature_preamble_removes_signoff_and_name(self):
        signature = """
Kind regards
Dr. Taylor Smith
Acme GmbH
Telefon: +49 30 123456
"""
        result = _strip_signature_preamble(signature)

        self.assertEqual("Acme GmbH\nTelefon: +49 30 123456", result)

    def test_strip_mail_preamble_removes_headers_and_greeting(self):
        mail = """
From: Max Sampleman
Gesendet: Dienstag, 28. April 2026 09:15
To: Info
Subject: Callback

Dear Sir or Madam,

please call me back.
"""
        result = _strip_mail_preamble(mail)

        self.assertEqual("please call me back.", result)

    def test_strip_mail_preamble_removes_greeting_with_typo(self):
        mail = """
Dear Sir or Madam,

please find our contact details below.
"""
        result = _strip_mail_preamble(mail)

        self.assertEqual("please find our contact details below.", result)

    def test_strip_mail_preamble_removes_kopie_header_before_greeting(self):
        mail = """
Cc: "Contact" < kontakt@anon.invalid >

Dear Mr. Smith,

heute ist unsere Produktlizenz abgelaufen.
"""
        result = _strip_mail_preamble(mail)

        self.assertEqual("heute ist unsere Produktlizenz abgelaufen.", result)

    def test_strip_mail_preamble_removes_antwort_an_and_reply_to_headers(self):
        mail = """
Antwort an: lizenz@anon.invalid
Reply-To: service@anon.invalid

Dear Mr. Smith,

please send us the new license file.
"""
        result = _strip_mail_preamble(mail)

        self.assertEqual("please send us the new license file.", result)

    def test_strip_mail_preamble_removes_subject_prefix_fragments(self):
        mail = """
WG: Datencheck-Ergebnis

Dear Sir or Madam,

please review the case.
"""
        result = _strip_mail_preamble(mail)

        self.assertEqual("please review the case.", result)

    def test_strip_mail_preamble_keeps_inline_content(self):
        mail = "Hello Mr. Miller, please call me back."

        result = _strip_mail_preamble(mail)

        self.assertEqual(mail, result)

    def test_split_mail_thread_keeps_outlook_reply_chain_as_separate_mail(self):
        mail = """
Dear Ms. Smith,

please call me back.

From: Old Contact <alt@example.invalid>
Gesendet: Montag, 27. April 2026 15:30
To: Max Sampleman
Subject: Old email

old content
"""
        result = _split_mail_thread(mail)

        self.assertEqual(2, len(result))
        self.assertIn("please call me back.", result[0])
        self.assertIn("Old Contact", result[1])
        self.assertIn("old content", result[1])

    def test_split_mail_thread_keeps_forwarded_message_block_as_separate_mail(self):
        mail = """
Please review.

-----Original Message-----
From: Old Sender <old@example.invalid>
Sent: Monday, April 27, 2026 15:30
Subject: Old topic

old content
"""
        result = _split_mail_thread(mail)

        self.assertEqual(2, len(result))
        self.assertEqual("Please review.", result[0])
        self.assertIn("From: Old Sender", result[1])
        self.assertIn("old content", result[1])

    def test_split_mail_context_and_signature_cleans_one_mail_part(self):
        mail = """
Dear Ms. Smith,

please call me back.

Kind regards
Dr. Taylor Smith
Acme GmbH
Telefon: +49 30 123456

From: Old Contact <alt@example.invalid>
Gesendet: Montag, 27. April 2026 15:30
To: Max Sampleman
Subject: Old email

Dear Sir or Madam,
old email with wrong phone number +49 99 999999
"""
        context, signature = _split_mail_context_and_signature(mail)

        self.assertEqual("please call me back.", context)
        self.assertIn("Acme GmbH", signature)
        self.assertIn("Telefon: +49 30 123456", signature)

    def test_split_mail_thread_and_cleanup_processes_each_reply_as_own_mail(self):
        mail = """
Dear Ms. Smith,

please call me back.

Kind regards
Dr. Taylor Smith
Acme GmbH
Telefon: +49 30 123456

From: Old Contact <alt@example.invalid>
Gesendet: Montag, 27. April 2026 15:30
To: Max Sampleman
Subject: Old email

Dear Sir or Madam,
old email with wrong phone number +49 99 999999

Best regards
Old Sender
Old GmbH
Telefon: +49 99 999999
"""
        cleaned = [_split_mail_context_and_signature(part) for part in _split_mail_thread(mail)]

        self.assertEqual(2, len(cleaned))
        self.assertEqual("please call me back.", cleaned[0][0])
        self.assertIn("Acme GmbH", cleaned[0][1])
        self.assertIn("Telefon: +49 30 123456", cleaned[0][1])
        self.assertIn("old email with wrong phone number +49 99 999999", cleaned[1][0])
        self.assertIn("Old GmbH", cleaned[1][1])
        self.assertIn("Telefon: +49 99 999999", cleaned[1][1])

    def test_split_mail_thread_dequotes_quoted_reply_mail(self):
        mail = """
Please review.

> Dear Sir or Madam,
> please respond.
> 
> Kind regards
> Quote Sender
> Quote GmbH
> Telefon: +49 88 888888
"""
        cleaned = [_split_mail_context_and_signature(part) for part in _split_mail_thread(mail)]

        self.assertEqual(2, len(cleaned))
        self.assertEqual("Please review.", cleaned[0][0])
        self.assertEqual("please respond.", cleaned[1][0])
        self.assertIn("Quote GmbH", cleaned[1][1])

    def test_split_mail_context_removes_broken_html_header_fragments(self):
        mail = """
sender@anon.invalid
>
To: "
recipient.person@anon.invalid
" <
recipient.person@anon.invalid
>
Subject: Old thread
Datum: Mi, 1. Apr 2026 10:59
Dear Mr. Smith,
Die Fehlermeldung sehen wir weiterhin.

Kind regards
Alex Smith
ANONYM Plan GmbH
Telefon: +999 700 1000
E-Mail:
alex.smith@anon.invalid
"""

        context, signature = _split_mail_context_and_signature(mail)

        self.assertEqual("Die Fehlermeldung sehen wir weiterhin.", context)
        self.assertNotIn("recipient.person@anon.invalid", context)
        self.assertNotIn("Subject:", context)
        self.assertIn("ANONYM Plan GmbH", signature)

    def test_split_mail_context_recognizes_singular_signoff_before_signature(self):
        mail = """
ich hatte eine Datei geschickt.

Kind regards
Taylor Smith
Administrator
------------------------------------------------------------
City Administration Rivertown
Fachbereich Innere Administration
Test St. 13, 99999 Rivertown
Tel.: +999 700 1000
Mobiltelefon: +999 170 200300
E-Mail:
taylor.smith@anon.invalid
"""

        context, signature = _split_mail_context_and_signature(mail)

        self.assertEqual("ich hatte eine Datei geschickt.", context)
        self.assertNotIn("Taylor Smith", signature)
        self.assertIn("City Administration Rivertown", signature)
        self.assertIn("Tel.: +999 700 1000", signature)


if __name__ == "__main__":
    unittest.main()




