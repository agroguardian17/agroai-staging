"""ORM model registry.

Importing this package imports every model module, which registers all tables on
``Base.metadata``. The Alembic env intentionally keeps ``target_metadata = None``
(the schema is owned by hand-written migrations), but importing models here gives
the application + tests a single ``Base`` whose ``metadata.tables`` lists all 37
tables.
"""

from __future__ import annotations

from app.infra.persistence.base import Base

from . import (
    ai,
    alerts,
    billing,
    calibration,
    core,
    devices,
    events,
    farms,
    main_node,
    readings,
    system,
)

__all__ = [
    "Base",
    "ai",
    "alerts",
    "billing",
    "calibration",
    "core",
    "devices",
    "events",
    "farms",
    "main_node",
    "readings",
    "system",
]
