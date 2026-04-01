"""Unit tests for backend dispatch in LLM.Connection."""

import json
import unittest
from unittest.mock import Mock, patch

from llmService.LLM.Connection import test_connection as run_llm_connection


class TestConnectionTests(unittest.TestCase):
    """Ensure backend selection and parsing/normalization flow works."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("llm_service.LLM.Connection._normalize_llm_result")
    @patch("llm_service.LLM.Connection.parse_llm_json")
    @patch("llm_service.LLM.Connection.Client")
    def test_test_connection_calls_ollama_backend(
        self,
        client_cls,
        parse_mock,
        normalize_mock,
    ):
        """Ollama should be called with default host/model and parsed output."""

        fake_client = Mock()
        fake_client.generate.return_value = {"response": "RAW-OLLAMA"}
        client_cls.return_value = fake_client
        parse_mock.return_value = {"is_allowed": True}
        normalize_mock.return_value = {"is_allowed": True, "full_name": "John Doe"}

        mail = "John Doe ACME +49 123456"
        result = run_llm_connection(mail)

        client_cls.assert_called_once_with(host="http://localhost:11434")
        fake_client.generate.assert_called_once()
        kwargs = fake_client.generate.call_args.kwargs
        self.assertEqual("llama3.2:1b", kwargs["model"])
        self.assertIn(mail, kwargs["prompt"])
        parse_mock.assert_called_once_with("RAW-OLLAMA")
        normalize_mock.assert_called_once_with({"is_allowed": True}, mail)
        self.assertEqual({"is_allowed": True, "full_name": "John Doe"}, result)

    @patch.dict(
        "os.environ",
        {
            "LLM_BACKEND": "llama_cpp",
            "LLM_ENDPOINT": "http://localhost:8080",
            "LLM_MODEL": "tiny-test-model",
        },
        clear=True,
    )
    @patch("llm_service.LLM.Connection._normalize_llm_result")
    @patch("llm_service.LLM.Connection.parse_llm_json")
    @patch("llm_service.LLM.Connection.request.urlopen")
    def test_test_connection_calls_llamacpp_backend(
        self,
        urlopen_mock,
        parse_mock,
        normalize_mock,
    ):
        """llama.cpp backend should use OpenAI-compatible chat endpoint."""

        fake_http_response = Mock()
        fake_http_response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "RAW-LLAMACPP"}}]}
        ).encode("utf-8")
        urlopen_mock.return_value.__enter__.return_value = fake_http_response
        parse_mock.return_value = {"is_allowed": True}
        normalize_mock.return_value = {"is_allowed": True, "full_name": "Jane Doe"}

        mail = "Jane Doe ACME +49 555000"
        result = run_llm_connection(mail)

        request_obj = urlopen_mock.call_args.args[0]
        payload = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual("http://localhost:8080/v1/chat/completions", request_obj.full_url)
        self.assertEqual("tiny-test-model", payload["model"])
        parse_mock.assert_called_once_with("RAW-LLAMACPP")
        normalize_mock.assert_called_once_with({"is_allowed": True}, mail)
        self.assertEqual({"is_allowed": True, "full_name": "Jane Doe"}, result)

    @patch.dict("os.environ", {"LLM_BACKEND": "unknown"}, clear=True)
    def test_test_connection_raises_for_unknown_backend(self):
        """Unexpected backend names should fail fast with a clear error."""

        with self.assertRaises(ValueError):
            run_llm_connection("Any Mail")

    @patch.dict("os.environ", {}, clear=True)
    @patch("llm_service.LLM.Connection.parse_llm_json", side_effect=RuntimeError("bad output"))
    @patch("llm_service.LLM.Connection.Client")
    def test_test_connection_returns_none_when_parser_fails(self, client_cls, _parse_mock):
        """Parser failures should be treated as filtered/invalid output."""

        fake_client = Mock()
        fake_client.generate.return_value = {"response": "RAW-OLLAMA"}
        client_cls.return_value = fake_client

        result = run_llm_connection("John Doe")
        self.assertIsNone(result)

    @patch.dict("os.environ", {}, clear=True)
    @patch("llm_service.LLM.Connection.parse_llm_json", side_effect=RuntimeError("bad output"))
    @patch("llm_service.LLM.Connection.Client")
    def test_test_connection_extracts_all_structured_contacts_when_parser_fails(
        self, client_cls, _parse_mock
    ):
        """Structured contact lists should still be extracted without valid LLM JSON."""

        fake_client = Mock()
        fake_client.generate.return_value = {"response": "RAW-OLLAMA"}
        client_cls.return_value = fake_client

        mail = """
Nordwerk Services - Nina Becker; +999 170 1112233; nina.becker@nordwerk-services.de
Astera Technik - Leon Hartmann; +999 351 5558800; service@astera-technik.de
"""
        result = run_llm_connection(mail)

        self.assertIsInstance(result, list)
        self.assertEqual(2, len(result))
        self.assertEqual(["Nina Becker", "Leon Hartmann"], [item["full_name"] for item in result])


if __name__ == "__main__":
    unittest.main()
