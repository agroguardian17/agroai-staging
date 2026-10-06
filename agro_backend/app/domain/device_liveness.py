"""Device-liveness assessment — pure domain logic for the silence watchdog.

Decides, from a Main Node's latest heartbeat, whether a DEVICE_OFFLINE alert is
warranted. Two independent silence conditions:

* **Main Node stale** — the heartbeat itself is old (the gateway stopped
  publishing; a heartbeat lands every ~5 min, so a gap means the Main Node or
  its link is down).
* **Sub Node silent** — the Main Node is alive but reports the buried Sub Node
  as offline (``sub_node_online=False``) or silent for ``sub_node_silence_ms``
  (the firmware flags this past ``SUB_NODE_SILENCE_THRESHOLD_MS`` = 15 min).

PURE module — stdlib + domain only (enforced by the domain-purity gate).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.alert import Severity


@dataclass(frozen=True, slots=True)
class LivenessVerdict:
    offline: bool
    severity: Severity
    silent_minutes: int
    # 'online' | 'main_node_stale' | 'sub_node_silent'
    reason: str


def assess_liveness(
    *,
    recorded_at: datetime,
    sub_node_online: bool,
    sub_node_silence_ms: int,
    now: datetime,
    warn_minutes: int,
    critical_minutes: int,
) -> LivenessVerdict:
    """Classify one heartbeat. Offline when either silence condition exceeds
    ``warn_minutes``; CRITICAL once the dominant silence reaches ``critical_minutes``.
    """
    heartbeat_age_min = max(0.0, (now - recorded_at).total_seconds() / 60.0)
    sub_silence_min = max(0.0, sub_node_silence_ms / 60_000.0)

    main_stale = heartbeat_age_min >= warn_minutes
    sub_silent = (not sub_node_online) or sub_silence_min >= warn_minutes
    if not main_stale and not sub_silent:
        return LivenessVerdict(False, Severity.INFO, 0, "online")

    # The stale heartbeat age bounds how long the Sub Node could have been
    # silent too (we only have heartbeats to go on), so take the larger figure.
    main_minutes = heartbeat_age_min if main_stale else 0.0
    if main_minutes >= sub_silence_min:
        silent_minutes = int(main_minutes)
        reason = "main_node_stale"
    else:
        silent_minutes = int(max(sub_silence_min, main_minutes))
        reason = "sub_node_silent"

    severity = Severity.CRITICAL if silent_minutes >= critical_minutes else Severity.WARNING
    return LivenessVerdict(True, severity, silent_minutes, reason)


__all__ = ["LivenessVerdict", "assess_liveness"]
