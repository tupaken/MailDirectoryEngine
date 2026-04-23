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
    fake_db.get_new_messages_sent.return_value = []
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
    fake_db.get_new_messages_sent.return_value = []
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
    fake_db.get_new_messages_sent.return_value = []
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
    fake_db.get_new_messages_sent.return_value = []
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
    fake_db.get_new_messages_sent.return_value = []
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


def test_main_processes_sent_messages_via_storage_and_marks_operated(monkeypatch):
    """Sent rows with a project number should be stored and then marked operated."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [[], KeyboardInterrupt()]
    fake_db.get_new_messages_sent.return_value = [Message(id=11, path="C:/mail-export/11.eml")]
    db_adapter_cls = Mock(return_value=fake_db)
    subject_mock = Mock(return_value="12 345 Angebot")
    project_mock = Mock(return_value="12-345")
    storage_mock = Mock(return_value={"message": "200"})

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "subject_from_send", subject_mock)
    monkeypatch.setattr(main_module, "prj_number_extraction", project_mock)
    monkeypatch.setattr(main_module, "send_storage_payload", storage_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    subject_mock.assert_called_once_with("C:/mail-export/11.eml")
    project_mock.assert_called_once_with("12 345 Angebot")
    storage_mock.assert_called_once_with("C:/mail-export/11.eml", "12-345")
    fake_db.mark_operated.assert_called_once_with("Sent", 11)


def test_save_sent_marks_operated_when_no_project_number(monkeypatch):
    """Sent rows without a project number should be marked without a storage call."""

    fake_db = Mock()
    subject_mock = Mock(return_value="Ohne Projektnummer")
    project_mock = Mock(return_value=None)
    storage_mock = Mock()

    monkeypatch.setattr(main_module, "subject_from_send", subject_mock)
    monkeypatch.setattr(main_module, "prj_number_extraction", project_mock)
    monkeypatch.setattr(main_module, "send_storage_payload", storage_mock)

    main_module.save_sent(fake_db, [Message(id=12, path="C:/mail-export/12.eml")])

    subject_mock.assert_called_once_with("C:/mail-export/12.eml")
    project_mock.assert_called_once_with("Ohne Projektnummer")
    storage_mock.assert_not_called()
    fake_db.mark_operated.assert_called_once_with("Sent", 12)


def test_save_sent_leaves_failed_storage_unoperated(monkeypatch):
    """Failed storage calls should log and leave the sent row unoperated for retry."""

    fake_db = Mock()
    subject_mock = Mock(return_value="12 345 Angebot")
    project_mock = Mock(return_value="12-345")
    storage_mock = Mock(side_effect=RuntimeError("storage down"))
    print_mock = Mock()

    monkeypatch.setattr(main_module, "subject_from_send", subject_mock)
    monkeypatch.setattr(main_module, "prj_number_extraction", project_mock)
    monkeypatch.setattr(main_module, "send_storage_payload", storage_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    main_module.save_sent(fake_db, [Message(id=13, path="C:/mail-export/13.eml")])

    storage_mock.assert_called_once_with("C:/mail-export/13.eml", "12-345")
    fake_db.mark_operated.assert_not_called()
    assert call("Sent message 13 failed: storage down") in print_mock.mock_calls


