import pytest
from sqlalchemy import inspect, text

from skill_chat.storage.database import Database
from skill_chat.storage.models import metadata
from skill_chat.storage.repository import Repository


def test_migrations_are_versioned_and_preserve_existing_chats(settings):
    first = Repository(settings)
    chat = first.create_chat("a", "openai")
    first.db.engine.dispose()
    second = Repository(settings)
    assert second.list_chats("a")[0]["id"] == chat["id"]
    with second.db.engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001"
    second.db.engine.dispose()


def test_adopts_matching_unversioned_initial_schema(settings):
    from sqlalchemy import create_engine

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{settings.data_dir / 'chat.sqlite3'}")
    metadata.create_all(engine)
    engine.dispose()
    database = Database(settings)
    assert "alembic_version" in inspect(database.engine).get_table_names()
    database.engine.dispose()


def test_refuses_an_unknown_unversioned_schema(settings):
    from sqlalchemy import create_engine

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{settings.data_dir / 'chat.sqlite3'}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE chats (id TEXT PRIMARY KEY)"))
    engine.dispose()
    with pytest.raises(RuntimeError, match="unversioned database"):
        Database(settings)
