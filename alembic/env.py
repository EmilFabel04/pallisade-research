from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from pallisade_core.db.base import Base
from pallisade_core.settings import get_settings

# Import models so they register with Base.metadata.
# (Imports added as each model is introduced in later tasks.)
import pallisade_core.users.models  # noqa: F401
import pallisade_core.deals.models  # noqa: F401
import pallisade_core.runs.models  # noqa: F401
import pallisade_core.documents.models  # noqa: F401
import pallisade_core.chat.models  # noqa: F401
import pallisade_core.watchlist.models  # noqa: F401
import pallisade_core.memo_checks.models  # noqa: F401
import pallisade_core.research_history.models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
