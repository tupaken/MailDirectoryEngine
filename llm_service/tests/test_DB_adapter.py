"""Unit tests for DB_adapter.

These tests are pure unit tests:
- no real PostgreSQL connection
- no real .env file access
- no real SQLAlchemy Session interaction

The import helper supports both execution styles used in this repository:
- running tests from repository root (`llm_service.DB.DBadapter`)
- running tests from inside `llm_service` (`DB.DBadapter`)
"""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError


def _import_db_module():
    """Import DBadapter from whichever package root pytest uses."""
    for module_name in ("llm_service.DB.DBadapter", "DB.DBadapter"):
        try:
            return importlib.import_module(module_name)
        except ModuleNotFoundError:
            continue
    raise ModuleNotFoundError(
        "Could not import DBadapter as 'llm_service.DB.DBadapter' or 'DB.DBadapter'."
    )


db_module = _import_db_module()
DB_adapter = db_module.DB_adapter

BASE_ENV = {
    "POSTGRES_USER": "user",
    "POSTGRES_PASSWORD": "pass",
    "POSTGRES_HOST": "localhost",
    "POSTGRES_PORT": "5432",
    "POSTGRES_DB": "testdb",
}


def _set_env(monkeypatch, **overrides):
    """Patch ``os.getenv`` values used by ``DB_adapter.__init__``."""
    env = {**BASE_ENV, **overrides}
    monkeypatch.setattr(db_module.os, "getenv", lambda key: env.get(key))


def _mock_path_and_dotenv(monkeypatch, path_exists=False):
    """Patch .env discovery and return the mocked ``load_dotenv`` callable."""
    load_dotenv_mock = MagicMock()
    monkeypatch.setattr(db_module.Path, "exists", lambda _self: path_exists)
    monkeypatch.setattr(db_module, "load_dotenv", load_dotenv_mock)
    return load_dotenv_mock


def _mock_session(monkeypatch, rows=None):
    """Patch SQLAlchemy ``Session`` constructor and return session mocks."""
    session = MagicMock()
    if rows is not None:
        session.execute.return_value.mappings.return_value.all.return_value = rows
    session_cm = MagicMock()
    session_cm.__enter__.return_value = session
    session_cm.__exit__.return_value = False
    session_ctor = MagicMock(return_value=session_cm)
    monkeypatch.setattr(db_module, "Session", session_ctor)
    return session_ctor, session


class _FakeSelect:
    """Tiny stand-in for SQLAlchemy ``select`` statements."""

    def __init__(self, columns):
        self.columns = columns
        self.where_condition = None

    def where(self, condition):
        self.where_condition = condition
        return self


class _FakeUpdate:
    """Tiny stand-in for SQLAlchemy ``update`` statements."""

    def __init__(self, table):
        self.table = table
        self.where_condition = None
        self.values_payload = None

    def where(self, condition):
        self.where_condition = condition
        return self

    def values(self, **kwargs):
        self.values_payload = kwargs
        return self


def _table_for_inbox():
    """Build a minimal inbox table mock with required columns."""
    operated_col = MagicMock()
    operated_col.is_.return_value = "inbox-filter"
    return SimpleNamespace(
        c=SimpleNamespace(
            id=object(),
            content=object(),
            operated=operated_col,
        )
    )


def _table_for_sent():
    """Build a minimal sent table mock with required columns."""
    operated_col = MagicMock()
    operated_col.is_.return_value = "sent-filter"
    return SimpleNamespace(
        c=SimpleNamespace(
            id=object(),
            path=object(),
            operated=operated_col,
        )
    )


def _table_for_mark_operated(condition="id-condition"):
    """Build a minimal table mock needed by ``mark_operated`` tests."""
    id_col = MagicMock()
    id_col.is_.return_value = condition
    return SimpleNamespace(c=SimpleNamespace(id=id_col))


def _bare_adapter():
    """Create a ``DB_adapter`` instance without running ``__init__``."""
    adapter = DB_adapter.__new__(DB_adapter)
    adapter.db = object()
    return adapter


def test_init_raises_when_required_env_missing(monkeypatch):
    """Missing required POSTGRES variables should raise RuntimeError."""
    _set_env(monkeypatch, POSTGRES_USER=None, POSTGRES_DB="")
    _mock_path_and_dotenv(monkeypatch, path_exists=False)

    with pytest.raises(RuntimeError) as exc:
        DB_adapter()

    message = str(exc.value)
    assert "Missing required environment variables" in message
    assert "POSTGRES_USER" in message
    assert "POSTGRES_DB" in message


def test_init_creates_engine_and_reflects_tables(monkeypatch):
    """A valid setup should create engine and reflect inbox/sent tables."""
    _set_env(monkeypatch)
    load_dotenv_mock = _mock_path_and_dotenv(monkeypatch, path_exists=False)

    engine = MagicMock()
    engine.connect.return_value = MagicMock()
    create_engine_mock = MagicMock(return_value=engine)
    monkeypatch.setattr(db_module, "create_engine", create_engine_mock)

    inbox_table = object()
    sent_table = object()
    table_mock = MagicMock(side_effect=[inbox_table, sent_table])
    monkeypatch.setattr(db_module, "Table", table_mock)

    adapter = DB_adapter()

    assert adapter.db is engine
    assert adapter.inbox is inbox_table
    assert adapter.sent is sent_table

    load_dotenv_mock.assert_called_once_with(dotenv_path=None)
    create_engine_mock.assert_called_once()
    args, kwargs = create_engine_mock.call_args
    db_url = args[0]
    assert db_url.drivername == "postgresql+psycopg"
    assert db_url.username == BASE_ENV["POSTGRES_USER"]
    assert db_url.password == BASE_ENV["POSTGRES_PASSWORD"]
    assert db_url.host == BASE_ENV["POSTGRES_HOST"]
    assert db_url.port == int(BASE_ENV["POSTGRES_PORT"])
    assert db_url.database == BASE_ENV["POSTGRES_DB"]
    assert kwargs == {
        "pool_pre_ping": True,
        "connect_args": {"connect_timeout": 5},
    }
    assert table_mock.call_count == 2
    assert table_mock.call_args_list[0].args[0] == "e_mails_inbox"
    assert table_mock.call_args_list[1].args[0] == "e_mails_send"


def test_init_uses_provided_engine_without_create_engine(monkeypatch):
    """Passing an engine should skip ``create_engine`` construction."""
    _set_env(monkeypatch)
    _mock_path_and_dotenv(monkeypatch, path_exists=False)

    provided_engine = MagicMock()
    provided_engine.connect.return_value = MagicMock()
    create_engine_mock = MagicMock()
    monkeypatch.setattr(db_module, "create_engine", create_engine_mock)

    table_mock = MagicMock(side_effect=[object(), object()])
    monkeypatch.setattr(db_module, "Table", table_mock)

    adapter = DB_adapter(engine=provided_engine)

    assert adapter.db is provided_engine
    create_engine_mock.assert_not_called()
    assert table_mock.call_count == 2


def test_init_wraps_connection_errors(monkeypatch):
    """Connection errors should be wrapped into RuntimeError with cause."""
    _set_env(monkeypatch)
    _mock_path_and_dotenv(monkeypatch, path_exists=False)

    engine = MagicMock()
    engine.connect.side_effect = SQLAlchemyError("connection failed")
    monkeypatch.setattr(db_module, "create_engine", MagicMock(return_value=engine))
    table_mock = MagicMock()
    monkeypatch.setattr(db_module, "Table", table_mock)

    with pytest.raises(RuntimeError, match="Database connection/schema check failed") as exc:
        DB_adapter()

    assert isinstance(exc.value.__cause__, SQLAlchemyError)
    table_mock.assert_not_called()


def test_init_wraps_table_reflection_errors(monkeypatch):
    """Table reflection errors should be wrapped into RuntimeError."""
    _set_env(monkeypatch)
    _mock_path_and_dotenv(monkeypatch, path_exists=False)

    engine = MagicMock()
    engine.connect.return_value = MagicMock()
    monkeypatch.setattr(db_module, "create_engine", MagicMock(return_value=engine))
    monkeypatch.setattr(db_module, "Table", MagicMock(side_effect=SQLAlchemyError("missing table")))

    with pytest.raises(RuntimeError, match="Database connection/schema check failed") as exc:
        DB_adapter()

    assert isinstance(exc.value.__cause__, SQLAlchemyError)


def test_get_new_messages_inbox_returns_message_models(monkeypatch):
    """Inbox rows should be mapped into Message(id, content)."""
    adapter = _bare_adapter()
    adapter.inbox = _table_for_inbox()
    rows = [{"id": "1", "content": "<p>A</p>"}, {"id": "2", "content": "<p>B</p>"}]
    session_ctor, session = _mock_session(monkeypatch, rows=rows)

    select_calls = []

    def fake_select(*columns):
        stmt = _FakeSelect(columns)
        select_calls.append(stmt)
        return stmt

    monkeypatch.setattr(db_module, "select", fake_select)

    messages = adapter.get_new_messages_inbox()

    assert [m.id for m in messages] == ["1", "2"]
    assert [m.content for m in messages] == ["<p>A</p>", "<p>B</p>"]
    assert all(isinstance(m, db_module.Message) for m in messages)
    session_ctor.assert_called_once_with(adapter.db)
    adapter.inbox.c.operated.is_.assert_called_once_with(False)
    session.execute.assert_called_once_with(select_calls[0])


def test_get_new_messages_sent_returns_message_models(monkeypatch):
    """Sent rows should be mapped into Message(id, path)."""
    adapter = _bare_adapter()
    adapter.sent = _table_for_sent()
    rows = [{"id": "11", "path": "/tmp/a.txt"}, {"id": "12", "path": "/tmp/b.txt"}]
    session_ctor, session = _mock_session(monkeypatch, rows=rows)

    select_calls = []

    def fake_select(*columns):
        stmt = _FakeSelect(columns)
        select_calls.append(stmt)
        return stmt

    monkeypatch.setattr(db_module, "select", fake_select)

    messages = adapter.get_new_messages_sent()

    assert [m.id for m in messages] == ["11", "12"]
    assert [m.path for m in messages] == ["/tmp/a.txt", "/tmp/b.txt"]
    assert all(isinstance(m, db_module.Message) for m in messages)
    session_ctor.assert_called_once_with(adapter.db)
    adapter.sent.c.operated.is_.assert_called_once_with(False)
    session.execute.assert_called_once_with(select_calls[0])


def test_mark_operated_updates_inbox_and_commits(monkeypatch):
    """Inbox direction should update inbox table and commit once."""
    adapter = _bare_adapter()
    adapter.inbox = _table_for_mark_operated()
    adapter.sent = _table_for_mark_operated()
    _, session = _mock_session(monkeypatch)

    update_calls = []

    def fake_update(table):
        stmt = _FakeUpdate(table)
        update_calls.append(stmt)
        return stmt

    monkeypatch.setattr(db_module, "update", fake_update)

    adapter.mark_operated("Inbox", "abc")

    assert len(update_calls) == 1
    assert update_calls[0].table is adapter.inbox
    adapter.inbox.c.id.is_.assert_called_once_with("abc")
    assert update_calls[0].where_condition == "id-condition"
    assert update_calls[0].values_payload == {"operated": True}
    session.execute.assert_called_once_with(update_calls[0])
    session.commit.assert_called_once()


def test_mark_operated_updates_sent_and_commits(monkeypatch):
    """Sent direction should update sent table and commit once."""
    adapter = _bare_adapter()
    adapter.inbox = _table_for_mark_operated()
    adapter.sent = _table_for_mark_operated(condition="sent-id-condition")
    _, session = _mock_session(monkeypatch)

    update_calls = []

    def fake_update(table):
        stmt = _FakeUpdate(table)
        update_calls.append(stmt)
        return stmt

    monkeypatch.setattr(db_module, "update", fake_update)

    adapter.mark_operated("Sent", "xyz")

    assert len(update_calls) == 1
    assert update_calls[0].table is adapter.sent
    adapter.sent.c.id.is_.assert_called_once_with("xyz")
    assert update_calls[0].where_condition == "sent-id-condition"
    assert update_calls[0].values_payload == {"operated": True}
    session.execute.assert_called_once_with(update_calls[0])
    session.commit.assert_called_once()


def test_mark_operated_raises_for_unknown_direction(monkeypatch):
    """Unknown direction should fail early without DB interaction."""
    adapter = _bare_adapter()
    adapter.inbox = _table_for_mark_operated()
    adapter.sent = _table_for_mark_operated()
    update_mock = MagicMock()
    session_ctor = MagicMock()
    monkeypatch.setattr(db_module, "update", update_mock)
    monkeypatch.setattr(db_module, "Session", session_ctor)

    with pytest.raises(ValueError, match="Unknown messageDirection"):
        adapter.mark_operated("Draft", "1")

    update_mock.assert_not_called()
    session_ctor.assert_not_called()
