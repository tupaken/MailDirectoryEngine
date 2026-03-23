"""Unit tests for the llm_service main processing entry point."""

import unittest
from unittest.mock import Mock, call, patch

from llm_service.DB.messageModel import Message
from llm_service.main import main


class MainTests(unittest.TestCase):
    """Behavioral tests for ``main()`` orchestration."""

    @patch("builtins.print")
    @patch("llm_service.main.test_connection")
    @patch("llm_service.main.html_to_text")
    @patch("llm_service.main.DB_adapter")
    def test_main_processes_all_inbox_messages(
        self,
        db_adapter_cls,
        html_to_text_mock,
        test_connection_mock,
        print_mock,
    ):
        """Each inbox message should be cleaned, classified, and printed."""
        fake_db = Mock()
        fake_db.get_new_messages_inbox.return_value = [
            Message(id=1, content="<p>One</p>"),
            Message(id=2, content="<p>Two</p>"),
        ]
        db_adapter_cls.return_value = fake_db
        html_to_text_mock.side_effect = ["One", "Two"]
        test_connection_mock.side_effect = ["True", "False"]

        main()

        html_to_text_mock.assert_has_calls([call("<p>One</p>"), call("<p>Two</p>")])
        test_connection_mock.assert_has_calls([call("One"), call("Two")])
        print_mock.assert_has_calls([call("True\n"), call("False\n")])

    @patch("builtins.print")
    @patch("llm_service.main.test_connection")
    @patch("llm_service.main.html_to_text")
    @patch("llm_service.main.DB_adapter")
    def test_main_skips_processing_when_no_messages(
        self,
        db_adapter_cls,
        html_to_text_mock,
        test_connection_mock,
        print_mock,
    ):
        """No processing should happen when no inbox rows are returned."""
        fake_db = Mock()
        fake_db.get_new_messages_inbox.return_value = []
        db_adapter_cls.return_value = fake_db

        main()

        html_to_text_mock.assert_not_called()
        test_connection_mock.assert_not_called()
        print_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
