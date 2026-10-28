from sqlalchemy import (
    JSON,
    Column,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

metadata = MetaData()


def scoped_columns():
    return (
        Column("id", String, primary_key=True),
        Column("owner_id", String, nullable=False, index=True),
        Column("chat_id", String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True),
        Column("created", Float, nullable=False),
    )


chats = Table(
    "chats",
    metadata,
    Column("id", String, primary_key=True),
    Column("owner_id", String, nullable=False, index=True),
    Column("title", String, nullable=False),
    Column("model_id", String, nullable=False),
    Column("created", Float, nullable=False),
    Column("deleting", Integer, nullable=False, default=0),
)
turns = Table(
    "turns",
    metadata,
    *scoped_columns(),
    Column("client_request_id", String, nullable=False),
    Column("request", JSON, nullable=False),
    Column("state", String, nullable=False),
    Column("mode", String, nullable=False),
    Column("answer", String, nullable=False, default=""),
    Column("error", String),
    UniqueConstraint("owner_id", "chat_id", "client_request_id"),
)
attachments = Table(
    "attachments",
    metadata,
    *scoped_columns(),
    Column("filename", String, nullable=False),
    Column("state", String, nullable=False),
    Column("pages", JSON, nullable=False, default=list),
    Column("warnings", JSON, nullable=False, default=list),
    Column("error", String),
)
tasks = Table(
    "tasks",
    metadata,
    *scoped_columns(),
    Column("turn_id", String, ForeignKey("turns.id", ondelete="CASCADE"), nullable=False),
    Column("model_id", String, nullable=False),
    Column("skill_id", String),
    Column("fingerprint", String, nullable=False),
    Column("state", String, nullable=False),
    Column("stage", String, nullable=False, default="Queued"),
    Column("worker_id", String),
    Column("heartbeat", Float),
    Column("error", String),
    Column("retry_of", String),
    Column("finished", Float),
)
events = Table(
    "events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("owner_id", String, nullable=False),
    Column("chat_id", String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
    Column("turn_id", String, ForeignKey("turns.id", ondelete="CASCADE"), nullable=False),
    Column("type", String, nullable=False),
    Column("data", JSON, nullable=False),
)
artifacts = Table(
    "artifacts",
    metadata,
    *scoped_columns(),
    Column("task_id", String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False),
    Column("turn_id", String, ForeignKey("turns.id", ondelete="CASCADE"), nullable=False),
    Column("title", String, nullable=False),
    Column("parent_version_id", String),
    Column("version", Integer, nullable=False),
    Column("text_content", String, nullable=False),
    Column("state", String, nullable=False, default="staged"),
)
worker_status = Table(
    "worker_status",
    metadata,
    Column("id", String, primary_key=True),
    Column("heartbeat", Float, nullable=False),
)
investigations = Table(
    "investigations", metadata, *scoped_columns(),
    Column("creation_request_id", String, nullable=False),
    Column("model_id", String, nullable=False),
    Column("revision", Integer, nullable=False),
    Column("state", JSON, nullable=False),
    UniqueConstraint("owner_id", "chat_id"),
    UniqueConstraint("owner_id", "creation_request_id"),
)
investigation_commands = Table(
    "investigation_commands", metadata, *scoped_columns(),
    Column("client_request_id", String, nullable=False),
    Column("request", JSON, nullable=False),
    Column("receipt", JSON, nullable=False),
    UniqueConstraint("owner_id", "chat_id", "client_request_id"),
)
investigation_revisions = Table(
    "investigation_revisions", metadata, *scoped_columns(),
    Column("revision", Integer, nullable=False),
    Column("record", JSON, nullable=False),
)
investigation_ui_events = Table(
    "investigation_ui_events", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("owner_id", String, nullable=False, index=True),
    Column("chat_id", String, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True),
    Column("created", Float, nullable=False),
    Column("payload", JSON, nullable=False),
)
investigation_candidates = Table(
    "investigation_candidates", metadata, *scoped_columns(),
    Column("task_id", String, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True),
    Column("base_revision", Integer, nullable=False),
    Column("payload", JSON, nullable=False),
)
