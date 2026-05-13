import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

from app.models import Base  # importujemy nasze modele

config = context.config
fileConfig(config.config_file_name)

# Alembic wie o wszystkich tabelach przez Base.metadata
target_metadata = Base.metadata


def get_database_url() -> str:
    def read_secret(name: str) -> str:
        path = f"/run/secrets/{name}"
        with open(path) as f:
            return f.read().strip()

    db_pass = read_secret("db-pass")
    return (
        f"postgresql+psycopg2://appuser:{db_pass}"
        f"@pg_primary:5432/parental_app"
    )


def run_migrations_offline() -> None:
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        version_table_schema="app",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            version_table_schema="app",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()