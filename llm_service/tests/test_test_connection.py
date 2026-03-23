"""Unit tests for the Ollama wrapper helper."""

import unittest
from unittest.mock import Mock, patch

from llm_service.LLM.testConnection import test_connection


class TestConnectionTests(unittest.TestCase):
    """Ensure the wrapper calls Ollama with expected parameters."""

    @patch("llm_service.LLM.testConnection.Client")
    def test_test_connection_calls_ollama_and_returns_response(self, client_cls):
        """The helper should return the ``response`` field from ``generate``."""
        fake_client = Mock()
        fake_client.generate.return_value = {"response": "True"}
        client_cls.return_value = fake_client

        mail = "Firma ACME GmbH, kontakt@acme.example"
        result = test_connection(mail)

        client_cls.assert_called_once_with(host="http://localhost:11434")
        fake_client.generate.assert_called_once()
        kwargs = fake_client.generate.call_args.kwargs
        self.assertEqual("llama3.2", kwargs["model"])
        self.assertIn(mail, kwargs["prompt"])
        self.assertEqual("True", result)


if __name__ == "__main__":
    unittest.main()
