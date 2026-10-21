from alembic import context

from skill_chat.storage.models import metadata

context.configure(connection=context.config.attributes["connection"], target_metadata=metadata)
with context.begin_transaction():
    context.run_migrations()
