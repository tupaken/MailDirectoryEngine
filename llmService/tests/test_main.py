"""Unit tests for the llm_service main processing entry point."""

import builtins
from unittest.mock import Mock, call

import pytest

from llm_service.DB.messageModel import Message
from llm_service import main as main_module


def test_main_processes_messages_and_prints_only_allowed(monkeypatch):
    """Each inbox message should be cleaned and classified once."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [
        [Message(id=1, content="<p>One</p>"), Message(id=2, content="<p>Two</p>")],
        KeyboardInterrupt(),
    ]
    db_adapter_cls = Mock(return_value=fake_db)
    html_to_text_mock = Mock(side_effect=["One", "Two"])
    llm_connection_mock = Mock(
        side_effect=[{"is_allowed": True, "full_name": "John Doe"}, None]
    )
    print_mock = Mock()

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "html_to_text", html_to_text_mock)
    monkeypatch.setattr(main_module, "llm_connection", llm_connection_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    html_to_text_mock.assert_has_calls([call("<p>One</p>"), call("<p>Two</p>")])
    llm_connection_mock.assert_has_calls([call("One"), call("Two")])
    print_mock.assert_called_once_with({"is_allowed": True, "full_name": "John Doe"})


def test_main_skips_processing_when_no_messages(monkeypatch):
    """No classification/printing should happen when inbox polling is empty."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [[], KeyboardInterrupt()]
    db_adapter_cls = Mock(return_value=fake_db)
    html_to_text_mock = Mock()
    llm_connection_mock = Mock()
    print_mock = Mock()

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "html_to_text", html_to_text_mock)
    monkeypatch.setattr(main_module, "llm_connection", llm_connection_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    html_to_text_mock.assert_not_called()
    llm_connection_mock.assert_not_called()
    print_mock.assert_not_called()


def test_main_prints_each_contact_when_classifier_returns_list(monkeypatch):
    """List responses should be printed as one line per contact."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [
        [Message(id=1, content="<p>List Case</p>")],
        KeyboardInterrupt(),
    ]
    db_adapter_cls = Mock(return_value=fake_db)
    html_to_text_mock = Mock(return_value="List Case")
    llm_connection_mock = Mock(
        return_value=[
            {"is_allowed": True, "full_name": "Nina Becker", "phone": "+999 170 1112233"},
            {"is_allowed": True, "full_name": "Leon Hartmann", "phone": "+999 351 5558800"},
        ]
    )
    print_mock = Mock()

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "html_to_text", html_to_text_mock)
    monkeypatch.setattr(main_module, "llm_connection", llm_connection_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    llm_connection_mock.assert_called_once_with("List Case")
    assert print_mock.call_count == 2
    print_mock.assert_has_calls(
        [
            call({"is_allowed": True, "full_name": "Nina Becker", "phone": "+999 170 1112233"}),
            call({"is_allowed": True, "full_name": "Leon Hartmann", "phone": "+999 351 5558800"}),
        ]
    )
