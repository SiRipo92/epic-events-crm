"""
Alembic environment configuration.

This file is run by Alembic when generating or applying migrations.
It imports Base.metadata from the models package so Alembic can
detect all tables and autogenerate accurate migration scripts.

The DATABASE_URL is read from the environment variable (loaded from
.env via python-dotenv) rather than from alembic.ini directly,
keeping credentials out of the config file.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# ── Path setup ────────────────────────────────────────────────────────────────
# Add the project root to sys.path so Alembic can import models and config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Load .env before anything else ───────────────────────────────────────────
load_dotenv()

# ── Alembic config object ─────────────────────────────────────────────────────
config = context.config

# Set the database URL from environment variable — overrides alembic.ini value
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL", ""))

# ── Logging ───────────────────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import all models so Alembic can detect them ──────────────────────────────
from models.base import Base
from models.role import Role              # noqa: F401
from models.collaborator import Collaborator  # noqa: F401
from models.client import Client          # noqa: F401
from models.contract import Contract      # noqa: F401
from models.event import Event            # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode.

    Generates SQL scripts without connecting to the database.
    Useful for review before applying to production.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in online mode.

    Connects directly to the database and applies migrations immediately.
    Standard mode used during development and in the CI pipeline.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
