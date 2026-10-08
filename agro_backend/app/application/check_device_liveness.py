"""Use case: raise a DEVICE_OFFLINE alert when a node goes silent.

The gap this closes: the backend stored ``sub_node_online`` / ``sub_node_silence_ms``
from every Main Node heartbeat but never acted on them, so a dead Sub Node (or a
down Main Node) was never surfaced. This sweep reads each node's latest heartbeat,
classifies liveness (``app.domain.device_liveness``), and — subject to a per-plot
cooldown so it fires once per silence episode, not every tick — creates an alert
through the same path the device-health rules use and publishes ``alert.created``
so the advisory/delivery pipeline treats it like any other alert.

PURE w.r.t. imports: stdlib + ports + domain only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.application.ports.alert_repo import AlertRepo
from app.application.ports.event_bus import EVENT_ALERT_CREATED, EventBus
from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.main_node_reading_repo import MainNodeReadingRepo
from app.application.ports.plot_repo import PlotRepo
from app.domain.alert import AlertCandidate, AlertType
from app.domain.device_liveness import LivenessVerdict, assess_liveness


@dataclass(frozen=True, slots=True)
class DeviceLivenessDeps:
    heartbeat_repo: MainNodeReadingRepo
    alert_repo: AlertRepo
    farmer_repo: FarmerRepo
    plot_repo: PlotRepo
    event_bus: EventBus
    warn_minutes: int
    critical_minutes: int
    cooldown_minutes: int


def _message(verdict: LivenessVerdict) -> str:
    mins = verdict.silent_minutes
    if verdict.reason == "main_node_stale":
        return (
            f"तुमचे मुख्य यंत्र (गेटवे) सुमारे {mins} मिनिटांपासून संपर्कात नाही. कृपया वीज व इंटरनेट जोडणी तपासा."
        )
    return f"तुमचा जमिनीतील सेन्सर सुमारे {mins} मिनिटांपासून संपर्कात नाही. कृपया यंत्र व त्याची बॅटरी तपासा."


async def check_device_liveness(deps: DeviceLivenessDeps, *, now: datetime) -> int:
    """Scan latest heartbeats; raise DEVICE_OFFLINE alerts. Returns count raised."""
    raised = 0
    for hb in await deps.heartbeat_repo.latest_per_node():
        verdict = assess_liveness(
            recorded_at=hb.recorded_at,
            sub_node_online=hb.sub_node_online,
            sub_node_silence_ms=hb.sub_node_silence_ms,
            now=now,
            warn_minutes=deps.warn_minutes,
            critical_minutes=deps.critical_minutes,
        )
        if not verdict.offline:
            continue

        farmer_id = await deps.farmer_repo.owner_of_farm(hb.farm_id)
        if farmer_id is None:
            continue  # farm has no owner on record — nothing to attribute the alert to

        # Attribute the alert to the farm's monitored (node-bearing) plot, and
        # use it for the per-(plot, alert_type) cooldown.
        plots = await deps.plot_repo.for_farmer(farmer_id)
        monitored = next(
            (p for p in plots if p.farm_id == hb.farm_id and p.node_id is not None), None
        )
        if monitored is None:
            continue  # no node-bearing plot on this farm to attribute to

        last_at = await deps.alert_repo.last_triggered_at(
            monitored.plot_id, AlertType.DEVICE_OFFLINE
        )
        if last_at is not None and (now - last_at).total_seconds() / 60.0 < deps.cooldown_minutes:
            continue

        candidate = AlertCandidate(
            alert_type=AlertType.DEVICE_OFFLINE,
            severity=verdict.severity,
            alert_message_marathi=_message(verdict),
            tenant_id=hb.tenant_id,
            farm_id=hb.farm_id,
            farmer_id=farmer_id,
            triggered_at=now,
            device_id=monitored.node_id,
            alert_value=Decimal(verdict.silent_minutes),
            alert_threshold=Decimal(deps.warn_minutes),
        )
        alert_id = await deps.alert_repo.create(candidate)
        await deps.event_bus.publish(
            EVENT_ALERT_CREATED,
            {
                "alert_id": alert_id,
                "alert_type": AlertType.DEVICE_OFFLINE.value,
                "severity": verdict.severity.value,
                "source": "device_watchdog",
                "plot_id": monitored.plot_id,
                "farmer_id": str(farmer_id),
            },
        )
        raised += 1
    return raised


__all__ = ["DeviceLivenessDeps", "check_device_liveness"]
