"""Postgres adapter for
:class:`~app.application.ports.technician_install_repo.TechnicianInstallRepo`.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.technician_install_repo import TechnicianInstall


class PgTechnicianInstallRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def record(self, install: TechnicianInstall) -> uuid.UUID:
        stmt = text(
            """
            INSERT INTO technician_installations (
                tenant_id, farm_id, farmer_id,
                technician_id, technician_name, technician_phone,
                visit_type, visit_date,
                nodes_installed_count, devices_installed_json, notes
            ) VALUES (
                :tenant_id, :farm_id, :farmer_id,
                :technician_id, :technician_name, :technician_phone,
                :visit_type, :visit_date,
                :nodes_installed_count, CAST(:devices_json AS jsonb), :notes
            )
            RETURNING installation_id
            """
        )
        params: dict[str, Any] = {
            "tenant_id": install.tenant_id,
            "farm_id": install.farm_id,
            "farmer_id": install.farmer_id,
            "technician_id": install.technician_id,
            "technician_name": install.technician_name,
            "technician_phone": install.technician_phone,
            "visit_type": install.visit_type,
            "visit_date": install.visit_date,
            "nodes_installed_count": install.nodes_installed_count,
            "devices_json": (
                None
                if install.devices_installed_json is None
                else json.dumps(install.devices_installed_json)
            ),
            "notes": install.notes,
        }
        async with self._sm() as session:
            res = await session.execute(stmt, params)
            row = res.first()
            await session.commit()
        if row is None:
            raise RuntimeError("technician_installations INSERT did not RETURN a row")
        return cast(uuid.UUID, cast(Any, row).installation_id)


__all__ = ["PgTechnicianInstallRepo"]
