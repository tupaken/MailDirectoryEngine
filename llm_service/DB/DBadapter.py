import os
from sqlalchemy import create_engine,select,MetaData,Table
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from .messageModel import Message

class DB_adapter():
    def __init__(self):
        load_dotenv()
        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT")
        dbname = os.getenv("POSTGRES_DB")
        self.db = create_engine(
            f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}")
        meta=MetaData()
        self.inbox=Table("e_mails_inbox",meta,autoload_with=self.db)

    def get_new_messages_inbox(self):
        with Session(self.db) as session:
            column=self.inbox.c
            stmt=select(column.id,column.content).where(column.operated.is_(False))
            rows=session.execute(stmt).mappings().all()
            return [Message(id=row["id"], content=row["content"]) for row in rows]
    
