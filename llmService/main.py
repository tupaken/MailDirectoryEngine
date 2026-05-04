"""Application entry point for the Python inbox post-processing worker."""


from .API.StorageService import (
    STORAGE_MESSAGE_DESTINATION_NOT_FOUND,
    STORAGE_MESSAGE_SOURCE_NOT_FOUND,
    StorageServiceError,
    send_storage_payload,
)
from .DB.DBadapter import DB_adapter
from .HTMLClean.htmlCleaner import html_to_text, subject_from_send, content_from_send
from .LLM.Connection import DISPOSITION_IRRELEVANT, llm_connection_with_disposition
from .contact_sync import build_canonical_contact_payload, send_canonical_contact_payload
from .LLM.sent_analyze import prj_number_extraction,sent_filename_extraction
from .LLM.mail_preprocessing import _split_mail_context_and_signature_segments, _strip_mail_headers_everywhere

def _normalize_contacts(value: object) -> list[dict]:
    """Normalize decision payload contacts to a list of dictionaries."""

    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _sync_contacts(message_id: int, contacts: list[dict], source_text: str) -> None:
    """Send all extracted contacts for one message to ContactService."""

    failures: list[str] = []

    for contact in contacts:
        contact_source_text = contact.get("_source_text")
        if not isinstance(contact_source_text, str) or not contact_source_text.strip():
            contact_source_text = source_text

        try:
            payload = build_canonical_contact_payload(
                contact,
                source_message_id=message_id,
                source_text=contact_source_text,
            )
            response = send_canonical_contact_payload(payload)
            if isinstance(response, dict):
                print(response)
            else:
                print(contact.get("full_name"))
        except Exception as exc:
            full_name = str(contact.get("full_name") or "").strip() or "<unknown>"
            failures.append(f"{full_name}: {exc}")

    if failures:
        raise RuntimeError("; ".join(failures))


def main() -> None:
    """Process inbox rows and mark operated only for final, trusted outcomes."""

    db = DB_adapter()
    while True:
        messages = db.get_new_messages_inbox()
        sent_messages = db.get_new_messages_sent()

        if sent_messages:
            save_sent(db, sent_messages)

        if messages:
            contact_sync(db, messages)


def contact_sync(db: DB_adapter, messages: list) -> None:
    """Process inbox messages for contact extraction and persistence."""

    for message in messages:
        try:
            text = html_to_text(message.content or "")
            decision = llm_connection_with_disposition(text)
            contacts = _normalize_contacts(decision.get("contacts"))
            disposition = decision.get("disposition")
            disposition_label = (
                disposition
                if isinstance(disposition, str) and disposition.strip()
                else "unknown"
            )

            if contacts:
                _sync_contacts(message.id, contacts, text)
                db.mark_operated("Inbox", message.id)
                continue

            if disposition_label == DISPOSITION_IRRELEVANT:
                db.mark_operated("Inbox", message.id)
                print(f"Message {message.id} marked operated: irrelevant")
                continue

            result_signature = disposition_label
            count = db.record_unknown_result(message.id, result_signature)

            if count >= 3:
                print(f"Message {message.id} marked operated: no clear decision 3 times ({disposition_label})")
            else:
                print(f"Message {message.id} left unoperated: no clear decision ({disposition_label}), retry {count}/3")


        except Exception as exc:
            print(f"Message {message.id} failed: {exc}")


def save_sent(db: DB_adapter, sent_messages: list) -> None:
    """Forward sent-message files to StorageService and mark handled rows."""

    for message in sent_messages:
        try:
            sbj = subject_from_send(message.path)

            if not sbj:
                db.mark_operated("Sent", message.id)
                continue

            nmb = prj_number_extraction(sbj)

            if not nmb:
                db.mark_operated("Sent", message.id)
                continue

            content = content_from_send(message.path)
            cleaned = _strip_mail_headers_everywhere(content)
            context, _, _ = _split_mail_context_and_signature_segments(cleaned)

            target_name=sent_filename_extraction(context)
            
            
            send_storage_payload(message.path, nmb,target_name)
            db.mark_operated("Sent", message.id)
        except FileNotFoundError:
            db.mark_operated("Sent", message.id)
            print(
                f"Sent message {message.id} marked operated: "
                f"{STORAGE_MESSAGE_SOURCE_NOT_FOUND}: {message.path}"
            )
        except StorageServiceError as exc:
            if (
                exc.status_code == 404
                and exc.response_message == STORAGE_MESSAGE_DESTINATION_NOT_FOUND
            ):
                db.mark_operated("Sent", message.id)
                print(f"Sent message {message.id} marked operated: destination not found")
                continue

            print(f"Sent message {message.id} failed: {exc}")
        except Exception as exc:
            print(f"Sent message {message.id} failed: {exc}")


if __name__ == "__main__":
    main()
