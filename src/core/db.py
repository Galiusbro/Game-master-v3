"""
Declarative base for everything stored in PostgreSQL.

The event log and the account tables live in the same database and are
created together, so they share one metadata object.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for the operational tables: the event store and accounts."""
