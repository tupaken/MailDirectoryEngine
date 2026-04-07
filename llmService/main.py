"""Application entry point for the Python inbox post-processing worker."""

from .DB.DBadapter import DB_adapter
from .HTMLClean.htmlCleaner import html_to_text
from .LLM.Connection import DISPOSITION_IRRELEVANT, llm_connection_with_disposition
from .contact_sync import build_canonical_contact_payload, send_canonical_contact_payload


def _normalize_contacts(value: object) -> list[dict]:
    """Normalize decision payload contacts to a list of dictionaries."""

    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _sync_contacts(message_id: int, contacts: list[dict], source_text: str) -> None:
    """Send all extracted contacts for one message to ContactService."""

    for contact in contacts:
        payload = build_canonical_contact_payload(
            contact,
            source_message_id=message_id,
            source_text=source_text,
        )
        response = send_canonical_contact_payload(payload)
        if isinstance(response, dict):
            print(response)
        else:
            print(contact.get("full_name"))


def main() -> None:
    """Process inbox rows and mark operated only for final, trusted outcomes."""

    db = DB_adapter()
    while True:
        messages = db.get_new_messages_inbox()
        if len(messages) == 0:
            continue

        for message in messages:
            try:
                text = html_to_text(message.content or "")
                decision = llm_connection_with_disposition(text)
                contacts = _normalize_contacts(decision.get("contacts"))
                disposition = decision.get("disposition")

                if contacts:
                    _sync_contacts(message.id, contacts, text)
                    db.mark_operated("Inbox", message.id)
                    continue

                if disposition == DISPOSITION_IRRELEVANT:
                    db.mark_operated("Inbox", message.id)
                    print(f"Message {message.id} marked operated: irrelevant")
                    continue

                print(f"Message {message.id} left unoperated: no clear decision")

            except Exception as exc:
                print(f"Message {message.id} failed: {exc}")


if __name__ == "__main__":
    main()
