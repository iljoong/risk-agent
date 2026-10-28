"""Versioned investigation demo state and replay log."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def scoped():
    return [
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("chat_id", sa.String(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
    ]


def upgrade():
    op.create_table(
        "investigations", *scoped(),
        sa.Column("creation_request_id", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.UniqueConstraint("owner_id", "chat_id"),
        sa.UniqueConstraint("owner_id", "creation_request_id"),
    )
    op.create_table(
        "investigation_commands", *scoped(),
        sa.Column("client_request_id", sa.String(), nullable=False),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("receipt", sa.JSON(), nullable=False),
        sa.UniqueConstraint("owner_id", "chat_id", "client_request_id"),
    )
    op.create_table(
        "investigation_revisions", *scoped(),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("record", sa.JSON(), nullable=False),
    )
    op.create_table(
        "investigation_ui_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("owner_id", sa.String(), nullable=False),
        sa.Column("chat_id", sa.String(), sa.ForeignKey("chats.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    op.create_table(
        "investigation_candidates", *scoped(),
        sa.Column("task_id", sa.String(), sa.ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
    )
    for name in (
        "investigations", "investigation_commands", "investigation_revisions",
        "investigation_ui_events", "investigation_candidates",
    ):
        for field in ("owner_id", "chat_id"):
            op.create_index(f"ix_{name}_{field}", name, [field])


def downgrade():
    for name in (
        "investigation_candidates", "investigation_ui_events", "investigation_revisions",
        "investigation_commands", "investigations",
    ):
        op.drop_table(name)
