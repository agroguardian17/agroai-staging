"""Postgres adapter for :class:`SatelliteReadingRepo`.

Writes into ``satellite_data`` (migration 0001 + the Domain 14 panel added in
0019). Upsert is idempotent on the ``satellite_data_plot_scene_idem`` unique
constraint ``(plot_id, image_date, satellite_source)``.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.satellite_reading_repo import SatelliteScene

# Columns written per scene (besides the tenant/farm/plot ids + source + date).
_VALUE_COLUMNS: tuple[str, ...] = (
    "ndvi_value",
    "ndvi_std",
    "ndre_value",
    "ndmi_value",
    "evi_value",
    "savi_value",
    "nbr_value",
    "cloud_cover_pct",
    "valid_pixel_pct",
    "sar_vv_db",
    "sar_vh_db",
    "sar_rvi",
    "sar_coherence",
    "lst_c",
    "cwsi",
    "pipeline_version",
)


def _f(v: Decimal | None) -> float | None:
    return None if v is None else float(v)


def _d(v: Any) -> Decimal | None:
    return None if v is None else Decimal(str(v))


def _scene_params(scene: SatelliteScene) -> dict[str, Any]:
    return {
        "ndvi_value": _f(scene.ndvi_mean),
        "ndvi_std": _f(scene.ndvi_std),
        "ndre_value": _f(scene.ndre_mean),
        "ndmi_value": _f(scene.ndmi_mean),
        "evi_value": _f(scene.evi_mean),
        "savi_value": _f(scene.savi_mean),
        "nbr_value": _f(scene.nbr_value),
        "cloud_cover_pct": _f(scene.cloud_cover_pct),
        "valid_pixel_pct": _f(scene.valid_pixel_pct),
        "sar_vv_db": _f(scene.sar_vv_db),
        "sar_vh_db": _f(scene.sar_vh_db),
        "sar_rvi": _f(scene.sar_rvi),
        "sar_coherence": _f(scene.sar_coherence),
        "lst_c": _f(scene.lst_c),
        "cwsi": _f(scene.cwsi),
        "pipeline_version": scene.pipeline_version,
    }


def _row_to_scene(row: Any) -> SatelliteScene:
    return SatelliteScene(
        image_date=row.image_date,
        satellite_source=row.satellite_source,
        ndvi_mean=_d(row.ndvi_value),
        ndvi_std=_d(row.ndvi_std),
        ndre_mean=_d(row.ndre_value),
        ndmi_mean=_d(row.ndmi_value),
        evi_mean=_d(row.evi_value),
        savi_mean=_d(row.savi_value),
        nbr_value=_d(row.nbr_value),
        cloud_cover_pct=_d(row.cloud_cover_pct),
        valid_pixel_pct=_d(row.valid_pixel_pct),
        sar_vv_db=_d(row.sar_vv_db),
        sar_vh_db=_d(row.sar_vh_db),
        sar_rvi=_d(row.sar_rvi),
        sar_coherence=_d(row.sar_coherence),
        lst_c=_d(row.lst_c),
        cwsi=_d(row.cwsi),
        pipeline_version=row.pipeline_version,
    )


_INSERT_COLS = (
    "tenant_id",
    "farm_id",
    "plot_id",
    "satellite_source",
    "image_date",
    *_VALUE_COLUMNS,
)
_SET_CLAUSE = ", ".join(f"{c} = EXCLUDED.{c}" for c in _VALUE_COLUMNS)


def _insert_sql() -> str:
    cols = ", ".join(_INSERT_COLS)
    placeholders = ", ".join(f":{c}" for c in _INSERT_COLS)
    return (
        f"INSERT INTO satellite_data ({cols}) VALUES ({placeholders}) "
        "ON CONFLICT (plot_id, image_date, satellite_source) DO UPDATE SET "
        f"{_SET_CLAUSE}"
    )


_SELECT_SQL = (
    "SELECT image_date, satellite_source, ndvi_value, ndvi_std, ndre_value, ndmi_value, "
    "evi_value, savi_value, nbr_value, cloud_cover_pct, valid_pixel_pct, sar_vv_db, sar_vh_db, "
    "sar_rvi, sar_coherence, lst_c, cwsi, pipeline_version FROM satellite_data "
    "WHERE plot_id = :plot_id AND satellite_source = :source "
    "ORDER BY image_date DESC LIMIT :limit"
)


class PgSatelliteReadingRepo:
    """Concrete :class:`SatelliteReadingRepo` against Postgres."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def save(
        self,
        *,
        tenant_id: uuid.UUID,
        farm_id: uuid.UUID,
        plot_id: str,
        scene: SatelliteScene,
    ) -> None:
        params = {
            "tenant_id": tenant_id,
            "farm_id": farm_id,
            "plot_id": plot_id,
            "satellite_source": scene.satellite_source,
            "image_date": scene.image_date,
            **_scene_params(scene),
        }
        async with self._sm() as session:
            await session.execute(text(_insert_sql()), params)
            await session.commit()

    async def recent(self, plot_id: str, satellite_source: str, limit: int) -> list[SatelliteScene]:
        async with self._sm() as session:
            res = await session.execute(
                text(_SELECT_SQL),
                {"plot_id": plot_id, "source": satellite_source, "limit": limit},
            )
            return [_row_to_scene(r) for r in res.all()]


__all__ = ["PgSatelliteReadingRepo"]
