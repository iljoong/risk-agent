from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine, event, inspect

from skill_chat.config import Settings
from skill_chat.storage.models import metadata


class Database:
    def __init__(self, settings: Settings):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{settings.data_dir / 'chat.sqlite3'}",
            connect_args={"check_same_thread": False, "timeout": 15},
        )

        @event.listens_for(self.engine, "connect")
        def configure(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

        self.migrate()

    def migrate(self):
        configuration = Config()
        configuration.set_main_option(
            "script_location",
            str(Path(__file__).with_name("migrations")).replace("%", "%%"),
        )
        with self.transaction() as connection:
            configuration.attributes["connection"] = connection
            tables = inspect(connection).get_table_names()
            if tables and "alembic_version" not in tables:
                if compare_metadata(MigrationContext.configure(connection), metadata):
                    raise RuntimeError(
                        "Unknown unversioned database schema; back up the data and migrate explicitly"
                    )
                command.stamp(configuration, "0001")
            command.upgrade(configuration, "head")

    @contextmanager
    def transaction(self):
        with self.engine.connect() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
