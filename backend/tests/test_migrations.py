import pytest
from sqlalchemy import inspect, text

from skill_chat.contracts import Scope
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
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0003"
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


def test_upgrades_initial_revision_without_losing_chats(settings):
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine

    import skill_chat.storage.database as database_module

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = create_engine(f"sqlite:///{settings.data_dir / 'chat.sqlite3'}")
    configuration = Config()
    configuration.set_main_option("script_location", str(Path(database_module.__file__).with_name("migrations")))
    with engine.begin() as connection:
        configuration.attributes["connection"] = connection
        command.upgrade(configuration, "0001")
        connection.execute(text(
            "INSERT INTO chats (id, owner_id, title, model_id, created, deleting) "
            "VALUES ('old', 'a', 'Existing evidence', 'openai', 1, 0)"
        ))
    engine.dispose()
    repository = Repository(settings)
    assert repository.get_chat(Scope("a", "old"))["title"] == "Existing evidence"
    assert "investigations" in inspect(repository.db.engine).get_table_names()
