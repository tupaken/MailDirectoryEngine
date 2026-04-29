"""Unit tests for the llmService main processing entry point."""

import builtins
from unittest.mock import Mock, call

import pytest

from llmService.API.StorageService import (
    STORAGE_MESSAGE_DESTINATION_NOT_FOUND,
    STORAGE_MESSAGE_SOURCE_NOT_FOUND,
    StorageServiceError,
)
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
                "contacts": [{"is_allowed": True, "full_name": "Alex Smith", "phone": "+999 100200"}],
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
        [{"is_allowed": True, "full_name": "Alex Smith", "phone": "+999 100200"}],
        "One",
    )
    fake_db.mark_operated.assert_has_calls([call("Inbox", 1), call("Inbox", 2)])
    assert call("Message 2 marked operated: irrelevant") in print_mock.mock_calls


def test_sync_contacts_uses_per_contact_source_text(monkeypatch):
    """Each contact should be enriched from its own mail part, not the full thread."""

    build_mock = Mock(
        side_effect=[
            {"payload": "one"},
            {"payload": "two"},
        ]
    )
    send_mock = Mock(return_value={"status": "created"})

    contacts = [
        {
            "is_allowed": True,
            "full_name": "Contact One",
            "phone": "+49 111 111111",
            "_source_text": "mail part one\nPhone: +49 111 111111",
        },
        {
            "is_allowed": True,
            "full_name": "Contact Two",
            "phone": "+49 222 222222",
            "_source_text": "mail part two\nPhone: +49 222 222222",
        },
    ]

    monkeypatch.setattr(main_module, "build_canonical_contact_payload", build_mock)
    monkeypatch.setattr(main_module, "send_canonical_contact_payload", send_mock)

    main_module._sync_contacts(1661, contacts, "full thread with both phone numbers")

    assert build_mock.call_args_list[0].kwargs["source_text"] == contacts[0]["_source_text"]
    assert build_mock.call_args_list[1].kwargs["source_text"] == contacts[1]["_source_text"]
    assert send_mock.call_args_list == [call({"payload": "one"}), call({"payload": "two"})]


def test_sync_contacts_continues_after_one_contact_fails(monkeypatch):
    """One bad contact must not stop later contacts from being attempted."""

    build_mock = Mock(
        side_effect=[
            ValueError("broken payload"),
            {"payload": "two"},
        ]
    )
    send_mock = Mock(return_value={"status": "created"})

    contacts = [
        {
            "is_allowed": True,
            "full_name": "Contact One",
            "phone": "+49 111 111111",
        },
        {
            "is_allowed": True,
            "full_name": "Contact Two",
            "phone": "+49 222 222222",
        },
    ]

    monkeypatch.setattr(main_module, "build_canonical_contact_payload", build_mock)
    monkeypatch.setattr(main_module, "send_canonical_contact_payload", send_mock)

    with pytest.raises(RuntimeError, match="Contact One: broken payload"):
        main_module._sync_contacts(1661, contacts, "thread text")

    assert build_mock.call_count == 2
    assert send_mock.call_args_list == [call({"payload": "two"})]


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
    fake_db.record_unknown_result.return_value = 1

    monkeypatch.setattr(main_module, "DB_adapter", db_adapter_cls)
    monkeypatch.setattr(main_module, "html_to_text", html_to_text_mock)
    monkeypatch.setattr(main_module, "llm_connection_with_disposition", decision_mock)
    monkeypatch.setattr(main_module, "_sync_contacts", sync_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    with pytest.raises(KeyboardInterrupt):
        main_module.main()

    sync_mock.assert_not_called()
    fake_db.mark_operated.assert_not_called()
    fake_db.record_unknown_result.assert_called_once_with(7, "unknown")
    assert (
        call("Message 7 left unoperated: no clear decision (unknown), retry 1/3")
        in print_mock.mock_calls
    )


def test_main_marks_unknown_message_operated_after_third_matching_result(monkeypatch):
    """The third matching unknown result should be treated as final."""

    fake_db = Mock()
    fake_db.get_new_messages_inbox.side_effect = [
        [Message(id=8, content="<p>Unknown</p>")],
        KeyboardInterrupt(),
    ]
    fake_db.get_new_messages_sent.return_value = []
    fake_db.record_unknown_result.return_value = 3
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
    fake_db.record_unknown_result.assert_called_once_with(8, "unknown")
    fake_db.mark_operated.assert_not_called()
    assert (
        call("Message 8 marked operated: no clear decision 3 times (unknown)")
        in print_mock.mock_calls
    )


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
                {"is_allowed": True, "full_name": "Morgan Smith", "phone": "+999 170 1112233"},
                {"is_allowed": True, "full_name": "Riley Smith", "phone": "+999 351 5558800"},
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
            {"is_allowed": True, "full_name": "Morgan Smith", "phone": "+999 170 1112233"},
            {"is_allowed": True, "full_name": "Riley Smith", "phone": "+999 351 5558800"},
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


def test_save_sent_marks_operated_when_subject_is_missing(monkeypatch):
    """Sent rows without a Subject header should be marked without parsing or storage."""

    fake_db = Mock()
    subject_mock = Mock(return_value=None)
    project_mock = Mock()
    storage_mock = Mock()

    monkeypatch.setattr(main_module, "subject_from_send", subject_mock)
    monkeypatch.setattr(main_module, "prj_number_extraction", project_mock)
    monkeypatch.setattr(main_module, "send_storage_payload", storage_mock)

    main_module.save_sent(fake_db, [Message(id=14, path="C:/mail-export/14.eml")])

    subject_mock.assert_called_once_with("C:/mail-export/14.eml")
    project_mock.assert_not_called()
    storage_mock.assert_not_called()
    fake_db.mark_operated.assert_called_once_with("Sent", 14)


def test_save_sent_marks_operated_when_storage_destination_is_missing(monkeypatch):
    """Missing destination folders should be treated as final non-retryable sent rows."""

    fake_db = Mock()
    subject_mock = Mock(return_value="12 345 Angebot")
    project_mock = Mock(return_value="12-345")
    storage_mock = Mock(
        side_effect=StorageServiceError(
            "http://localhost:5001/store",
            404,
            STORAGE_MESSAGE_DESTINATION_NOT_FOUND,
        )
    )
    print_mock = Mock()

    monkeypatch.setattr(main_module, "subject_from_send", subject_mock)
    monkeypatch.setattr(main_module, "prj_number_extraction", project_mock)
    monkeypatch.setattr(main_module, "send_storage_payload", storage_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    main_module.save_sent(fake_db, [Message(id=13, path="C:/mail-export/13.eml")])

    storage_mock.assert_called_once_with("C:/mail-export/13.eml", "12-345")
    fake_db.mark_operated.assert_called_once_with("Sent", 13)
    assert call("Sent message 13 marked operated: destination not found") in print_mock.mock_calls


def test_save_sent_marks_operated_when_local_source_file_is_missing(monkeypatch):
    """Missing local `.eml` files should be treated as final and marked operated."""

    fake_db = Mock()
    subject_mock = Mock(
        side_effect=FileNotFoundError(2, "No such file or directory", "C:/mail-export/16.eml")
    )
    project_mock = Mock()
    storage_mock = Mock()
    print_mock = Mock()

    monkeypatch.setattr(main_module, "subject_from_send", subject_mock)
    monkeypatch.setattr(main_module, "prj_number_extraction", project_mock)
    monkeypatch.setattr(main_module, "send_storage_payload", storage_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    main_module.save_sent(fake_db, [Message(id=16, path="C:/mail-export/16.eml")])

    project_mock.assert_not_called()
    storage_mock.assert_not_called()
    fake_db.mark_operated.assert_called_once_with("Sent", 16)
    assert call(
        "Sent message 16 marked operated: source_not_found: C:/mail-export/16.eml"
    ) in print_mock.mock_calls


def test_save_sent_leaves_retryable_storage_error_unoperated(monkeypatch):
    """Retryable storage errors should keep sent rows unoperated for later retries."""

    fake_db = Mock()
    subject_mock = Mock(return_value="12 345 Angebot")
    project_mock = Mock(return_value="12-345")
    storage_mock = Mock(
        side_effect=StorageServiceError(
            "http://localhost:5001/store",
            404,
            STORAGE_MESSAGE_SOURCE_NOT_FOUND,
        )
    )
    print_mock = Mock()

    monkeypatch.setattr(main_module, "subject_from_send", subject_mock)
    monkeypatch.setattr(main_module, "prj_number_extraction", project_mock)
    monkeypatch.setattr(main_module, "send_storage_payload", storage_mock)
    monkeypatch.setattr(builtins, "print", print_mock)

    main_module.save_sent(fake_db, [Message(id=15, path="C:/mail-export/15.eml")])

    storage_mock.assert_called_once_with("C:/mail-export/15.eml", "12-345")
    fake_db.mark_operated.assert_not_called()
    assert call(
        "Sent message 15 failed: StorageService returned HTTP 404 for "
        "http://localhost:5001/store: source_not_found"
    ) in print_mock.mock_calls


