"""Alembic migration environment.

Reads DATABASE_URL_SYNC directly from the environment (which docker-compose,
Coolify and CI all populate from .env) so this file has zero dependency on
``app.config`` and runs cleanly even before app deps are installed.
Migrations are intentionally synchronous - asyncpg drivers don't compose
well with Alembic's batch ops.

Phase 1 will register the SQLAlchemy ``Base.metadata`` here so autogenerate
sees ORM models. Until then, migrations are hand-written SQL files.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

config = context.config

DEFAULT_SYNC_URL = "postgresql://agro:agro@localhost:5432/agro"
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("DATABASE_URL_SYNC", DEFAULT_SYNC_URL),
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Phase 1 hook: import Base + register tables here.
#   from app.infra.persistence.base import Base
#   target_metadata = Base.metadata
target_metadata = None


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode against a live connection."""
    section = config.get_section(config.config_ini_section, {})
    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
