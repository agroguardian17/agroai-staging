"""Integration tests for
:class:`~app.infra.persistence.pg_cluster_repo.PgClusterRepo` (D12).

Exercises the spawn / join / recompute / move logic against real Postgres,
including the aggregate recompute (centroid mean, ``percentile_disc`` planting
week, ``baseline_active`` at ``min_plots``) and the delete-empty path that a
plot moving out of its last cluster must trigger.

Cluster rows are isolated by a run-unique ``tenant_id`` (``clusters.tenant_id``
has no FK), so ``load_active`` sees only this test's clusters and cleanup can
delete them by tenant. Seeded plots use ``PILOT_TENANT`` to satisfy the FK chain.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.cluster_repo import ClusterRepo
from app.domain.clustering import PlotForClustering
from app.infra.persistence.pg_cluster_repo import PgClusterRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)

_WEEK = date(2026, 6, 15)


def _seed_plots(eng: Engine, n: int) -> tuple[uuid.UUID, uuid.UUID, list[str]]:
    run = uuid.uuid4().hex[:8]
    farmer_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    plot_ids = [f"CLU_{run}_{i}" for i in range(n)]
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO farmers (
                    farmer_id, tenant_id, full_name, marathi_name, phone_primary,
                    whatsapp_number, language_preference, village, taluka, district,
                    state, subscription_tier, subscription_start, subscription_end,
                    payment_status
                ) VALUES (
                    :farmer, :tenant, 'Test Farmer', 'टेस्ट', '+910000000000',
                    '+910000000000', 'marathi', 'v', 't', 'd',
                    'Maharashtra', 'basic', '2025-06-01', '2026-06-01', 'paid'
                )
                """
            ),
            {"farmer": farmer_id, "tenant": PILOT_TENANT},
        )
        conn.execute(
            text(
                """
                INSERT INTO farms (
                    farm_id, tenant_id, farmer_id, total_area_acre,
                    gps_lat_center, gps_lng_center, soil_type,
                    water_source_primary, irrigation_type, electricity_source
                ) VALUES (
                    :farm, :tenant, :farmer, 2.0, 19.9, 75.7, 'black',
                    'well', 'drip', 'grid'
                )
                """
            ),
            {"farm": farm_id, "tenant": PILOT_TENANT, "farmer": farmer_id},
        )
        for i, pid in enumerate(plot_ids):
            conn.execute(
                text(
                    """
                    INSERT INTO plots (
                        plot_id, tenant_id, farm_id, plot_number, area_acre,
                        gps_lat, gps_lng, irrigation_valve_id
                    ) VALUES (
                        :plot, :tenant, :farm, :n, 1.0, 19.9, 75.7, :valve
                    )
                    """
                ),
                {
                    "plot": pid,
                    "tenant": PILOT_TENANT,
                    "farm": farm_id,
                    "n": i + 1,
                    "valve": f"V_{run}_{i}",
                },
            )
    return farmer_id, farm_id, plot_ids


@pytest.fixture
def env(sync_engine: Engine) -> Iterator[tuple[uuid.UUID, list[str]]]:
    """A run-unique cluster tenant + 10 seeded plots; cleaned up after."""
    cluster_tenant = uuid.uuid4()
    farmer_id, farm_id, plot_ids = _seed_plots(sync_engine, 10)
    yield cluster_tenant, plot_ids
    with sync_engine.begin() as conn:
        conn.execute(
            text("DELETE FROM plot_cluster WHERE plot_id = ANY(:pids)"),
            {"pids": plot_ids},
        )
        conn.execute(text("DELETE FROM clusters WHERE tenant_id = :t"), {"t": cluster_tenant})
        conn.execute(text("DELETE FROM plots WHERE plot_id = ANY(:pids)"), {"pids": plot_ids})
        conn.execute(text("DELETE FROM farms WHERE farm_id = :f"), {"f": farm_id})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": farmer_id})


def _inputs(lat: float = 19.860, lng: float = 75.400, week: date = _WEEK) -> PlotForClustering:
    return PlotForClustering(
        variety="IISR Mahima", planting_week=week, centroid_lat=lat, centroid_lng=lng
    )


async def _spawn(
    repo: PgClusterRepo, tenant: uuid.UUID, plot_id: str, inp: PlotForClustering
) -> str:
    return await repo.persist_assignment(
        tenant_id=tenant,
        plot_id=plot_id,
        plot=inp,
        chosen_cluster_id=None,
        distance_km=None,
        fit_score=0.0,
        informational_only=False,
    )


async def _join(
    repo: PgClusterRepo, tenant: uuid.UUID, plot_id: str, cid: str, inp: PlotForClustering
) -> str:
    return await repo.persist_assignment(
        tenant_id=tenant,
        plot_id=plot_id,
        plot=inp,
        chosen_cluster_id=cid,
        distance_km=0.2,
        fit_score=0.9,
        informational_only=False,
    )


async def test_pg_cluster_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(PgClusterRepo(sessionmaker), ClusterRepo)


async def test_spawn_creates_cluster_and_membership(
    sessionmaker: async_sessionmaker[AsyncSession],
    env: tuple[uuid.UUID, list[str]],
    sync_engine: Engine,
) -> None:
    tenant, plot_ids = env
    repo = PgClusterRepo(sessionmaker)
    cid = await _spawn(repo, tenant, plot_ids[0], _inputs())
    assert cid.startswith("CL-")

    with sync_engine.begin() as conn:
        row = conn.execute(
            text("SELECT plot_count, baseline_active FROM clusters WHERE cluster_id = :c"),
            {"c": cid},
        ).one()
        assert row.plot_count == 1
        assert row.baseline_active is False
        assert (
            conn.execute(
                text("SELECT count(*) FROM plot_cluster WHERE cluster_id = :c"), {"c": cid}
            ).scalar_one()
            == 1
        )
    assert await repo.cluster_id_for_plot(plot_ids[0]) == cid


async def test_join_recomputes_centroid_and_count(
    sessionmaker: async_sessionmaker[AsyncSession],
    env: tuple[uuid.UUID, list[str]],
    sync_engine: Engine,
) -> None:
    tenant, plot_ids = env
    repo = PgClusterRepo(sessionmaker)
    cid = await _spawn(repo, tenant, plot_ids[0], _inputs(lat=19.860, lng=75.400))
    await _join(repo, tenant, plot_ids[1], cid, _inputs(lat=19.870, lng=75.420))

    with sync_engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT plot_count, centroid_lat, centroid_lng FROM clusters WHERE cluster_id = :c"
            ),
            {"c": cid},
        ).one()
    assert row.plot_count == 2
    assert float(row.centroid_lat) == pytest.approx(19.865, abs=1e-4)  # mean of members
    assert float(row.centroid_lng) == pytest.approx(75.410, abs=1e-4)


async def test_baseline_activates_at_min_plots(
    sessionmaker: async_sessionmaker[AsyncSession],
    env: tuple[uuid.UUID, list[str]],
    sync_engine: Engine,
) -> None:
    tenant, plot_ids = env
    repo = PgClusterRepo(sessionmaker)
    cid = await _spawn(repo, tenant, plot_ids[0], _inputs())
    for pid in plot_ids[1:8]:  # 7 more -> 8 total == min_plots_per_cluster
        await _join(repo, tenant, pid, cid, _inputs())

    with sync_engine.begin() as conn:
        row = conn.execute(
            text("SELECT plot_count, baseline_active FROM clusters WHERE cluster_id = :c"),
            {"c": cid},
        ).one()
    assert row.plot_count == 8
    assert row.baseline_active is True


async def test_move_detaches_and_deletes_empty_source(
    sessionmaker: async_sessionmaker[AsyncSession],
    env: tuple[uuid.UUID, list[str]],
    sync_engine: Engine,
) -> None:
    tenant, plot_ids = env
    repo = PgClusterRepo(sessionmaker)
    # Plot 0 spawns cluster A (its sole member); plot 1 spawns cluster B.
    cid_a = await _spawn(repo, tenant, plot_ids[0], _inputs())
    cid_b = await _spawn(repo, tenant, plot_ids[1], _inputs())
    # Move plot 0 into B -> A is now empty and must be deleted.
    await _join(repo, tenant, plot_ids[0], cid_b, _inputs())

    assert await repo.cluster_id_for_plot(plot_ids[0]) == cid_b
    with sync_engine.begin() as conn:
        assert (
            conn.execute(
                text("SELECT count(*) FROM clusters WHERE cluster_id = :c"), {"c": cid_a}
            ).scalar_one()
            == 0
        )  # A deleted
        assert (
            conn.execute(
                text("SELECT plot_count FROM clusters WHERE cluster_id = :c"), {"c": cid_b}
            ).scalar_one()
            == 2
        )  # B now holds both


async def test_load_active_returns_candidates(
    sessionmaker: async_sessionmaker[AsyncSession],
    env: tuple[uuid.UUID, list[str]],
) -> None:
    tenant, plot_ids = env
    repo = PgClusterRepo(sessionmaker)
    cid = await _spawn(repo, tenant, plot_ids[0], _inputs())
    active = await repo.load_active(tenant)
    assert [c.cluster_id for c in active] == [cid]
    assert active[0].variety == "IISR Mahima"
    assert active[0].plot_count == 1


async def test_load_config_has_seeded_knobs(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = PgClusterRepo(sessionmaker)
    cfg = await repo.load_config()
    assert cfg.get("variety_gate") == "strict"
    assert cfg.get("min_plots_per_cluster") == "8"
