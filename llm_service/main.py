from .DB.DBadapter import DB_adapter
from .htmlCleaner import html_to_text

def main():
    db=DB_adapter()
    messages=db.get_new_messages_inbox()
    for message in messages:
        text=html_to_text(message.content)
        print (text+"\n")

if __name__ == "__main__":
    main()
