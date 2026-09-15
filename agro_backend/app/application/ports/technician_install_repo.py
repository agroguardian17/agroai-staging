"""Port: technician-installation records (``technician_installations``).

Round 9. When a technician provisions a Sub Node on a plot, we log the visit
(who, when, what was installed) for the ops trail.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class TechnicianInstall:
    tenant_id: uuid.UUID
    farm_id: uuid.UUID
    farmer_id: uuid.UUID
    technician_id: str
    technician_name: str
    technician_phone: str
    visit_type: str  # 'install' | 'service' | 'repair' | 'inspection'
    visit_date: datetime.date
    nodes_installed_count: int | None = None
    devices_installed_json: Any | None = None
    notes: str | None = None


@runtime_checkable
class TechnicianInstallRepo(Protocol):
    async def record(self, install: TechnicianInstall) -> uuid.UUID:
        """Insert one installation row; return the installation_id."""
        ...


__all__ = ["TechnicianInstall", "TechnicianInstallRepo"]
