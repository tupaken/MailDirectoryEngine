"""Unit tests for the Ollama wrapper helper."""

import json
import unittest
from unittest.mock import Mock, patch

from llm_service.LLM.testConnection import test_connection as run_llm_connection


class TestConnectionTests(unittest.TestCase):
    """Ensure the wrapper calls Ollama with expected parameters."""

    @patch.dict("os.environ", {}, clear=True)
    @patch("llm_service.LLM.testConnection.Client")
    def test_test_connection_calls_ollama_and_returns_response(self, client_cls):
        """The helper should return the ``response`` field from ``generate``."""
        fake_client = Mock()
        fake_client.generate.return_value = {"response": "True"}
        client_cls.return_value = fake_client

        mail = "Firma ACME GmbH, kontakt@acme.example"
        result = run_llm_connection(mail)

        client_cls.assert_called_once_with(host="http://localhost:11434")
        fake_client.generate.assert_called_once()
        kwargs = fake_client.generate.call_args.kwargs
        self.assertEqual("llama3.2:1b", kwargs["model"])
        self.assertIn(mail, kwargs["prompt"])
        self.assertEqual("True", result)

    @patch.dict(
        "os.environ",
        {
            "LLM_BACKEND": "llama_cpp",
            "LLM_ENDPOINT": "http://localhost:8080",
            "LLM_MODEL": "tiny-test-model",
        },
        clear=True,
    )
    @patch("llm_service.LLM.testConnection.request.urlopen")
    def test_test_connection_calls_llamacpp_and_returns_response(self, urlopen_mock):
        """llama.cpp backend should use OpenAI-compatible chat endpoint."""
        fake_http_response = Mock()
        fake_http_response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": "False"}}]}
        ).encode("utf-8")
        urlopen_mock.return_value.__enter__.return_value = fake_http_response

        result = run_llm_connection("Max Mustermann")

        self.assertEqual("False", result)
        request_obj = urlopen_mock.call_args.args[0]
        payload = json.loads(request_obj.data.decode("utf-8"))
        self.assertEqual("http://localhost:8080/v1/chat/completions", request_obj.full_url)
        self.assertEqual("tiny-test-model", payload["model"])

    @patch.dict("os.environ", {"LLM_BACKEND": "unknown"}, clear=True)
    def test_test_connection_raises_for_unknown_backend(self):
        """Unexpected backend names should fail fast with a clear error."""
        with self.assertRaises(ValueError):
            run_llm_connection("Any Mail")


if __name__ == "__main__":
    unittest.main()
