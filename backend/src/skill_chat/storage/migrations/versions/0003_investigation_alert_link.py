"""Link an investigation to the alert it was opened from."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("investigations") as batch:
        batch.add_column(sa.Column("alert_id", sa.String(), nullable=True))
        batch.create_unique_constraint("uq_investigations_owner_alert", ["owner_id", "alert_id"])


def downgrade():
    with op.batch_alter_table("investigations") as batch:
        batch.drop_constraint("uq_investigations_owner_alert", type_="unique")
        batch.drop_column("alert_id")
