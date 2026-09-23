"""D12 advisory-QA enums (D12_QA_WORKFLOW §3.1, §3.2).

The controlled vocabularies the review write-path validates against, mirroring
the CHECK constraints on ``advisory_classification`` and ``non_compliance_reason``
(migration 0041). Kept in the domain so both the use-cases and any future review
API share one source of truth.
"""

from __future__ import annotations

from enum import StrEnum


class Classification(StrEnum):
    CONFIRMED_TRUE_POSITIVE = "confirmed_true_positive"
    FALSE_POSITIVE = "false_positive"
    UNRESOLVED = "unresolved"


class EvidenceSource(StrEnum):
    FARMER_REPORT = "farmer_report"
    AGRONOMIST_VISIT = "agronomist_visit"
    PHOTO = "photo"
    SENSOR = "sensor"
    NO_EVIDENCE = "no_evidence"


class ActionState(StrEnum):
    NOT_ACTED = "not_acted"
    PARTIALLY_ACTED = "partially_acted"


class NonComplianceReason(StrEnum):
    ALREADY_DONE = "already_done"
    COST_BARRIER = "cost_barrier"
    UNAVAILABLE_INPUT = "unavailable_input"
    DISAGREED = "disagreed"
    FORGOT = "forgot"
    OTHER = "other"


class CapturedVia(StrEnum):
    WHATSAPP_REPLY = "whatsapp_reply"
    AGRONOMIST_CALL = "agronomist_call"
    FARMER_APP = "farmer_app"
    FIELD_VISIT = "field_visit"


__all__ = [
    "ActionState",
    "CapturedVia",
    "Classification",
    "EvidenceSource",
    "NonComplianceReason",
]
