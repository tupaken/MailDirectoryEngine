"""Unit tests for the llmService main processing entry point."""

import builtins
from unittest.mock import Mock, call

import pytest

from llmService.DB.messageModel import Message
from llmService import main as main_module


def test_main_marks_operated_for_synced_or_explicitly_irrelevant(monkeypatch):
    """Rows are marked only for successful syncs or explicit irrelevant decisions."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [
        [Message(id=1, content="<p>One</p>"), Message(id=2, content="<p>Two</p>")],
        KeyboardInterrupt(),
    ]
    db_adapter_cls = Mock(return_value=fake_db)
    html_to_text_mock = Mock(side_effect=["One", "Two"])
    decision_mock = Mock(
        side_effect=[
            {
                "contacts": [{"is_allowed": True, "full_name": "Alex Beispiel", "phone": "+999 100200"}],
                "disposition": "relevant",
            },
            {"contacts": [], "disposition": "irrelevant"},
        ]
    )
    sync_mock = Mock()
    print_mock = Mock()

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "html_to_text", html_to_text_mock)
    monkeypatch.setattr(main_module, "llm_connection_with_disposition", decision_mock)
    monkeypatch.setattr(main_module, "_sync_contacts", sync_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    decision_mock.assert_has_calls([call("One"), call("Two")])
    sync_mock.assert_called_once_with(
        1,
        [{"is_allowed": True, "full_name": "Alex Beispiel", "phone": "+999 100200"}],
        "One",
    )
    fake_db.mark_operated.assert_has_calls([call("Inbox", 1), call("Inbox", 2)])
    assert call("Message 2 marked operated: irrelevant") in print_mock.mock_calls


def test_main_leaves_unknown_messages_unoperated(monkeypatch):
    """Unknown decision state must not mark a row as operated."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [
        [Message(id=7, content="<p>Unknown</p>")],
        KeyboardInterrupt(),
    ]
    db_adapter_cls = Mock(return_value=fake_db)
    html_to_text_mock = Mock(return_value="Unknown")
    decision_mock = Mock(return_value={"contacts": [], "disposition": "unknown"})
    sync_mock = Mock()
    print_mock = Mock()

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "html_to_text", html_to_text_mock)
    monkeypatch.setattr(main_module, "llm_connection_with_disposition", decision_mock)
    monkeypatch.setattr(main_module, "_sync_contacts", sync_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    sync_mock.assert_not_called()
    fake_db.mark_operated.assert_not_called()
    assert call("Message 7 left unoperated: no clear decision (unknown)") in print_mock.mock_calls


def test_main_skips_processing_when_no_messages(monkeypatch):
    """No classification/syncing should happen when inbox polling is empty."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [[], KeyboardInterrupt()]
    db_adapter_cls = Mock(return_value=fake_db)
    html_to_text_mock = Mock()
    decision_mock = Mock()
    sync_mock = Mock()

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "html_to_text", html_to_text_mock)
    monkeypatch.setattr(main_module, "llm_connection_with_disposition", decision_mock)
    monkeypatch.setattr(main_module, "_sync_contacts", sync_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    html_to_text_mock.assert_not_called()
    decision_mock.assert_not_called()
    sync_mock.assert_not_called()
    fake_db.mark_operated.assert_not_called()


def test_main_uses_contact_list_when_classifier_returns_list(monkeypatch):
    """List responses should be forwarded unchanged to the sync layer."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [
        [Message(id=1, content="<p>List Case</p>")],
        KeyboardInterrupt(),
    ]
    db_adapter_cls = Mock(return_value=fake_db)
    html_to_text_mock = Mock(return_value="List Case")
    decision_mock = Mock(
        return_value={
            "contacts": [
                {"is_allowed": True, "full_name": "Morgan Beispiel", "phone": "+999 170 1112233"},
                {"is_allowed": True, "full_name": "Riley Beispiel", "phone": "+999 351 5558800"},
            ],
            "disposition": "relevant",
        }
    )
    sync_mock = Mock()

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "html_to_text", html_to_text_mock)
    monkeypatch.setattr(main_module, "llm_connection_with_disposition", decision_mock)
    monkeypatch.setattr(main_module, "_sync_contacts", sync_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    sync_mock.assert_called_once_with(
        1,
        [
            {"is_allowed": True, "full_name": "Morgan Beispiel", "phone": "+999 170 1112233"},
            {"is_allowed": True, "full_name": "Riley Beispiel", "phone": "+999 351 5558800"},
        ],
        "List Case",
    )
    fake_db.mark_operated.assert_called_once_with("Inbox", 1)


def test_main_logs_error_and_skips_mark_operated_for_failed_message(monkeypatch):
    """A sync failure should log and avoid marking the failed row as operated."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [
        [Message(id=1, content="<p>Bad</p>"), Message(id=2, content="<p>Good</p>")],
        KeyboardInterrupt(),
    ]
    db_adapter_cls = Mock(return_value=fake_db)
    html_to_text_mock = Mock(side_effect=["Bad", "Good"])
    decision_mock = Mock(
        side_effect=[
            {
                "contacts": [{"is_allowed": True, "full_name": "Bad Case", "phone": "+999 1"}],
                "disposition": "relevant",
            },
            {
                "contacts": [{"is_allowed": True, "full_name": "Good Case", "phone": "+999 2"}],
                "disposition": "relevant",
            },
        ]
    )
    sync_mock = Mock(side_effect=[RuntimeError("network error"), None])
    print_mock = Mock()

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "html_to_text", html_to_text_mock)
    monkeypatch.setattr(main_module, "llm_connection_with_disposition", decision_mock)
    monkeypatch.setattr(main_module, "_sync_contacts", sync_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    fake_db.mark_operated.assert_called_once_with("Inbox", 2)
    assert call("Message 1 failed: network error") in print_mock.mock_calls


