"""Application entry point for the Python inbox post-processing worker."""

from .DB.DBadapter import DB_adapter
from .HTMLClean.htmlCleaner import html_to_text
from .LLM.Connection import llm_connection


def main() -> None:
    """Load unprocessed inbox messages and print one LLM result per message."""

    db = DB_adapter()
    while(True):
        messages = db.get_new_messages_inbox()
        if len(messages) > 0:
            for message in messages:
                text = html_to_text(message.content or "")
                result = llm_connection(text)
                if result:
                    print(result)


if __name__ == "__main__":
    main()
