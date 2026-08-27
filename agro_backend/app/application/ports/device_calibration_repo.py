"""Port for the per-device calibration lookup used by the raw-payload ingest.

Only the ingest pipeline consumes this port today: on receipt of a
``$schema=agro-guardian/telemetry/v2-raw`` payload the broker fetches the
matching row and applies the constants to produce a ``Reading``.

Small surface (`get_by_device`) — the CRUD path is a follow-up (an ops
tool or a Streamlit page). Keeping the port narrow now avoids retro-fitting
tests when the CRUD path lands.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.device_calibration import DeviceCalibration


@runtime_checkable
class DeviceCalibrationRepo(Protocol):
    """Look up a Sub Node's calibration constants by (tenant_id, device_id)."""

    async def get_by_device(
        self,
        tenant_id: str,
        device_id: str,
    ) -> DeviceCalibration | None:
        """Return the calibration row for ``device_id`` or ``None`` if absent.

        ``tenant_id`` is passed as ``str`` (not ``UUID``) so the port stays
        stdlib-only and pure — the Pg adapter converts to ``uuid.UUID``.
        """
        ...


__all__ = ["DeviceCalibrationRepo"]
