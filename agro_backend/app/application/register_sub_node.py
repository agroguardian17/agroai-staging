"""Use case: register a Sub Node on a plot (Round 9 technician-install flow).

Transitions a plot from ``satellite_only`` to ``sub_node`` by assigning a
device, and logs the technician visit. Invoked by the technician/admin path (a
future staff-authenticated endpoint or an ops script) — the logic lives here so
that entry point stays thin.

PURE w.r.t. imports: stdlib + ports + domain + application only. No infra.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date

from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.technician_install_repo import (
    TechnicianInstall,
    TechnicianInstallRepo,
)


class RegisterSubNodeError(Exception):
    """Base class for registration problems."""


class PlotNotFoundError(RegisterSubNodeError):
    """No plot with the given id."""


class FarmOwnerNotFoundError(RegisterSubNodeError):
    """The plot's farm has no resolvable owner."""


@dataclass(frozen=True, slots=True)
class RegisterSubNodeCommand:
    plot_id: str
    node_id: str
    technician_id: str
    technician_name: str
    technician_phone: str
    visit_date: date
    nodes_installed_count: int = 1
    notes: str | None = None
    # Must match the technician_installations.visit_type CHECK.
    visit_type: str = "installation"


@dataclass(frozen=True, slots=True)
class RegisterSubNodeDeps:
    plot_repo: PlotRepo
    farmer_repo: FarmerRepo
    install_repo: TechnicianInstallRepo


@dataclass(frozen=True, slots=True)
class RegisterSubNodeResult:
    plot_id: str
    node_id: str
    installation_id: uuid.UUID
    data_tier: str = "sub_node"


async def execute(
    *, cmd: RegisterSubNodeCommand, deps: RegisterSubNodeDeps
) -> RegisterSubNodeResult:
    plot = await deps.plot_repo.find(cmd.plot_id)
    if plot is None:
        raise PlotNotFoundError(cmd.plot_id)

    farmer_id = await deps.farmer_repo.owner_of_farm(plot.farm_id)
    if farmer_id is None:
        raise FarmOwnerNotFoundError(str(plot.farm_id))

    # Assign the device (trigger flips data_tier to sub_node; the node_id FK
    # enforces the device exists — a bad id raises for the caller to surface).
    await deps.plot_repo.assign_sub_node(cmd.plot_id, cmd.node_id)

    installation_id = await deps.install_repo.record(
        TechnicianInstall(
            tenant_id=plot.tenant_id,
            farm_id=plot.farm_id,
            farmer_id=farmer_id,
            technician_id=cmd.technician_id,
            technician_name=cmd.technician_name,
            technician_phone=cmd.technician_phone,
            visit_type=cmd.visit_type,
            visit_date=cmd.visit_date,
            nodes_installed_count=cmd.nodes_installed_count,
            devices_installed_json=[{"device_id": cmd.node_id, "role": "sub_node"}],
            notes=cmd.notes,
        )
    )
    return RegisterSubNodeResult(
        plot_id=cmd.plot_id, node_id=cmd.node_id, installation_id=installation_id
    )


__all__ = [
    "FarmOwnerNotFoundError",
    "PlotNotFoundError",
    "RegisterSubNodeCommand",
    "RegisterSubNodeDeps",
    "RegisterSubNodeError",
    "RegisterSubNodeResult",
    "execute",
]
