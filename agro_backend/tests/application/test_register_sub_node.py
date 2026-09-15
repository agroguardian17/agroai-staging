"""Tests for the Round 9 Sub-Node registration use case."""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any, cast

import pytest

from app.application.register_sub_node import (
    FarmOwnerNotFoundError,
    PlotNotFoundError,
    RegisterSubNodeCommand,
    RegisterSubNodeDeps,
    execute,
)
from app.domain.plot import DataTier, Plot, PlotStatus

TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
FARM = uuid.UUID("33333333-3333-3333-3333-333333333333")
FARMER = uuid.UUID("22222222-2222-2222-2222-222222222222")
INSTALL_ID = uuid.UUID("99999999-9999-9999-9999-999999999999")


def _plot() -> Plot:
    return Plot(
        plot_id="PLOT_PILOT_001",
        tenant_id=TENANT,
        farm_id=FARM,
        plot_number=1,
        area_acre=Decimal("2.5"),
        gps_lat=19.87,
        gps_lng=75.34,
        irrigation_valve_id="V1",
        data_tier=DataTier.SATELLITE_ONLY,
        plot_status=PlotStatus.ACTIVE,
    )


class _FakePlotRepo:
    def __init__(self, plot: Plot | None) -> None:
        self._plot = plot
        self.assigned: list[tuple[str, str]] = []

    async def find(self, plot_id: str) -> Plot | None:
        return self._plot

    async def assign_sub_node(self, plot_id: str, node_id: str) -> None:
        self.assigned.append((plot_id, node_id))


class _FakeFarmerRepo:
    def __init__(self, owner: uuid.UUID | None) -> None:
        self._owner = owner

    async def owner_of_farm(self, farm_id: uuid.UUID) -> uuid.UUID | None:
        return self._owner


class _FakeInstallRepo:
    def __init__(self) -> None:
        self.recorded: list[Any] = []

    async def record(self, install: Any) -> uuid.UUID:
        self.recorded.append(install)
        return INSTALL_ID


def _cmd() -> RegisterSubNodeCommand:
    return RegisterSubNodeCommand(
        plot_id="PLOT_PILOT_001",
        node_id="AGR-SN-0001",
        technician_id="TECH-1",
        technician_name="Ravi",
        technician_phone="+919000000000",
        visit_date=datetime.date(2026, 9, 15),
    )


def _deps(plot_repo: Any, farmer_repo: Any, install_repo: Any) -> RegisterSubNodeDeps:
    return RegisterSubNodeDeps(
        plot_repo=cast(Any, plot_repo),
        farmer_repo=cast(Any, farmer_repo),
        install_repo=cast(Any, install_repo),
    )


async def test_registers_node_and_records_install() -> None:
    plot_repo = _FakePlotRepo(_plot())
    install_repo = _FakeInstallRepo()
    out = await execute(cmd=_cmd(), deps=_deps(plot_repo, _FakeFarmerRepo(FARMER), install_repo))

    assert out.plot_id == "PLOT_PILOT_001"
    assert out.node_id == "AGR-SN-0001"
    assert out.installation_id == INSTALL_ID
    assert out.data_tier == "sub_node"
    # node assigned to the plot (trigger will flip data_tier)
    assert plot_repo.assigned == [("PLOT_PILOT_001", "AGR-SN-0001")]
    # install row carries the resolved owner + tenant/farm from the plot
    rec = install_repo.recorded[0]
    assert rec.farmer_id == FARMER and rec.tenant_id == TENANT and rec.farm_id == FARM
    assert rec.devices_installed_json == [{"device_id": "AGR-SN-0001", "role": "sub_node"}]


async def test_unknown_plot_raises() -> None:
    with pytest.raises(PlotNotFoundError):
        await execute(
            cmd=_cmd(), deps=_deps(_FakePlotRepo(None), _FakeFarmerRepo(FARMER), _FakeInstallRepo())
        )


async def test_farm_without_owner_raises_and_does_not_assign() -> None:
    plot_repo = _FakePlotRepo(_plot())
    install_repo = _FakeInstallRepo()
    with pytest.raises(FarmOwnerNotFoundError):
        await execute(cmd=_cmd(), deps=_deps(plot_repo, _FakeFarmerRepo(None), install_repo))
    assert plot_repo.assigned == []
    assert install_repo.recorded == []
