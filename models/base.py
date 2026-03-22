"""
Base declarative class for all SQLAlchemy ORM models.

All model classes in this project inherit from Base, which provides
the SQLAlchemy declarative mapping system. This module intentionally
contains nothing else — no engine, no session, no imports of other models.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models.

    Inheriting from this class registers a model with SQLAlchemy's
    metadata, enabling Alembic to detect and autogenerate migrations.
    """
    pass
