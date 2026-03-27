"""
ORM model re-exports for the models package.

Importing from this module gives access to all ORM classes and the
shared Base in a single line. This is also the import pattern used
by Alembic's env.py to detect all tables for autogenerate migrations.

Usage:
    from models import Base, Collaborator, Client, Contract, Event
"""

from models.base import Base
from models.client import Client
from models.contract import Contract
from models.event import Event

__all__ = ["Base", "Client", "Contract", "Event"]
