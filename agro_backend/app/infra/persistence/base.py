"""SQLAlchemy 2.0 declarative base.

All ORM models inherit from :class:`Base`. The schema itself is owned by the
hand-written Alembic migrations (``target_metadata = None`` in alembic/env.py);
these models mirror that schema for the application/repository layer. Keep the
two in sync -- see ``docs/SCHEMA_DECISIONS.md``.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for every AgroGuardian ORM model."""
