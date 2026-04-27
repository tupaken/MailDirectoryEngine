"""PostgreSQL adapter used by llm_service to read and update message rows."""

import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, select, update
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .messageModel import Message


class DB_adapter:
    """Database access wrapper for inbox and sent mail tables."""

    def __init__(self, engine=None):
        """Initialize engine and reflect required tables.

        Args:
            engine: Optional preconfigured SQLAlchemy engine for testing or reuse.

        Raises:
            RuntimeError: If required environment variables are missing or database
                connection/schema reflection fails.
        """
        env_path = Path(__file__).resolve().parents[2] / ".env"
        load_dotenv(dotenv_path=env_path if env_path.exists() else None)

        user = os.getenv("POSTGRES_USER")
        password = os.getenv("POSTGRES_PASSWORD")
        host = os.getenv("POSTGRES_HOST")
        port = os.getenv("POSTGRES_PORT")
        dbname = os.getenv("POSTGRES_DB")

        required_env = {
            "POSTGRES_USER": user,
            "POSTGRES_PASSWORD": password,
            "POSTGRES_HOST": host,
            "POSTGRES_PORT": port,
            "POSTGRES_DB": dbname,
        }
        missing = [key for key, value in required_env.items() if not value]
        if missing:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")

        url = URL.create(
            drivername="postgresql+psycopg",
            username=user,
            password=password,
            host=host,
            port=int(port),
            database=dbname,
        )
        self.db = engine or create_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )

        meta = MetaData()
        try:
            with self.db.connect():
                pass
            self.inbox = Table("e_mails_inbox", meta, autoload_with=self.db)
            self.sent = Table("e_mails_send", meta, autoload_with=self.db)
        except SQLAlchemyError as exc:
            raise RuntimeError(
                "Database connection/schema check failed. "
                f"host={host} port={port} db={dbname}. "
                f"Root cause: {exc.__class__.__name__}: {exc}. "
                "Ensure PostgreSQL is running and run migrations with "
                "`docker compose run --rm migrate`."
            ) from exc

    def get_new_messages_inbox(self):
        """Return unprocessed inbox rows as Message objects."""
        with Session(self.db) as session:
            column = self.inbox.c
            stmt = select(column.id, column.content).where(column.operated.is_(False))
            rows = session.execute(stmt).mappings().all()
            return [Message(id=row["id"], content=row["content"]) for row in rows]

    def get_new_messages_sent(self):
        """Return unprocessed sent rows as Message objects."""
        with Session(self.db) as session:
            column = self.sent.c
            stmt = select(column.id, column.path).where(column.operated.is_(False))
            rows = session.execute(stmt).mappings().all()
            return [Message(id=row["id"], path=row["path"]) for row in rows]

    def mark_operated(self, messageDirection: str, id: str):
        """Mark an inbox or sent message row as operated.

        Args:
            messageDirection: Either ``Inbox`` or ``Sent``.
            id: Primary key value of the row to update.

        Raises:
            ValueError: If ``messageDirection`` is unknown.
        """
        if messageDirection == "Inbox":
            table = self.inbox
        elif messageDirection == "Sent":
            table = self.sent
        else:
            raise ValueError(f"Unknown messageDirection: {messageDirection}")

        stmt = update(table).where(table.c.id == id).values(operated=True)

        with Session(self.db) as sessioin:
            sessioin.execute(stmt)
            sessioin.commit()

    def record_unknown_result(self, message_id: int, result_signature: str) -> int:
        """Persist one unclear inbox result and return the updated retry count.

        The inbox row keeps track of the last unclear result signature plus how
        often it appeared consecutively. A matching signature increments the
        counter, a changed signature resets it to ``1``. The row is marked
        operated automatically once the counter reaches three.

        Args:
            message_id: Primary key value of the inbox row to update.
            result_signature: Stable signature representing the unclear result.

        Returns:
            The updated consecutive-match count for the stored signature.

        Raises:
            ValueError: If the inbox row does not exist.
        """
        with Session(self.db) as session:
            column = self.inbox.c

            stmt = (
                select(column.same_result_count, column.last_result_signature)
                .where(column.id == message_id)
                .with_for_update()
            )
            row = session.execute(stmt).one_or_none()
            if row is None:
                raise ValueError(f"Inbox message not found: {message_id}")

            new_count = (
                row.same_result_count + 1
                if row.last_result_signature == result_signature
                else 1
            )

            update_stmt = (
                update(self.inbox)
                .where(column.id == message_id)
                .values(
                    same_result_count=new_count,
                    last_result_signature=result_signature,
                    operated=(new_count >= 3),
                )
            )

            session.execute(update_stmt)
            session.commit()
            return new_count
