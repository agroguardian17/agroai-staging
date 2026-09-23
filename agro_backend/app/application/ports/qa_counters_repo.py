"""Port: D12 per-plot QA counters for the farm brain (D12_QA_WORKFLOW §3).

The cumulative counts the mapper fills into the Domain 12 farm-brain fields —
``true_alarm_count`` / ``false_alarm_count`` (from ``advisory_classification``)
and ``photo_uploaded_count`` / ``photo_labelled_count`` (from ``farmer_photos`` /
``photo_label``). All per plot, read in one round trip.

``non_compliance_reason`` is deliberately not sourced here: that farm-brain field
is the farmer's own answer to D12-AL-001 (a WhatsApp-reply channel not yet
built), a different source and vocabulary from the agronomist review table.

Concrete implementation:
:class:`app.infra.persistence.pg_qa_counters_repo.PgQaCountersRepo`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class QaCounters:
    true_alarm_count: int
    false_alarm_count: int
    photo_uploaded_count: int
    photo_labelled_count: int


@runtime_checkable
class QaCountersRepo(Protocol):
    async def counts_for_plot(self, plot_id: str) -> QaCounters:
        """The plot's cumulative QA counters (zeros when nothing recorded yet)."""
        ...


__all__ = ["QaCounters", "QaCountersRepo"]
