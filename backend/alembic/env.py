"""Alembic migration environment."""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from alembic.ddl import impl as alembic_impl
from sqlalchemy import Column, MetaData, PrimaryKeyConstraint, String, Table, pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from src.config import get_settings
from src.models.db import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
ALEMBIC_VERSION_NUM_LENGTH = 80


def _install_wide_alembic_version_table() -> None:
    """Allow project migration IDs longer than Alembic's 32 char default."""

    def version_table_impl(
        self: alembic_impl.DefaultImpl,
        *,
        version_table: str,
        version_table_schema: str | None,
        version_table_pk: bool,
        **kw: object,
    ) -> Table:
        _ = self, kw
        version_table_object = Table(
            version_table,
            MetaData(),
            Column(
                "version_num",
                String(ALEMBIC_VERSION_NUM_LENGTH),
                nullable=False,
            ),
            schema=version_table_schema,
        )
        if version_table_pk:
            version_table_object.append_constraint(
                PrimaryKeyConstraint(
                    "version_num",
                    name=f"{version_table}_pkc",
                )
            )

        return version_table_object

    alembic_impl.DefaultImpl.version_table_impl = version_table_impl


_install_wide_alembic_version_table()


def _database_url() -> str:
    """Return the application database URL for Alembic.

    Returns:
        Configured SQLAlchemy database URL.
    """
    return get_settings().database_url


def run_migrations_offline() -> None:
    """Run migrations without opening a database connection.

    Returns:
        None.
    """
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with an existing synchronous Alembic connection.

    Args:
        connection: Synchronous connection adapted from SQLAlchemy AsyncConnection.

    Returns:
        None.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run online Alembic migrations.

    Returns:
        None.

    Raises:
        RuntimeError: If Alembic cannot load its configured ini section.
    """
    configuration = config.get_section(config.config_ini_section)
    if configuration is None:
        raise RuntimeError("Alembic configuration section is missing.")

    configuration["sqlalchemy.url"] = _database_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations against the configured database.

    Returns:
        None.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
