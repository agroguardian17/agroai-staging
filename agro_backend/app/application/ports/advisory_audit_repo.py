"""Port: immutable advisory-audit log (LEGAL_COMPLIANCE_CERTIFICATE §7.3, A4.2).

One append-only ``record`` per advisory capturing the immutable generation facts.
The concrete table forbids UPDATE/DELETE, so this port is insert-only by design.

Concrete implementation:
:class:`app.infra.persistence.pg_advisory_audit_repo.PgAdvisoryAuditRepo`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class AdvisoryAuditRow:
    suggestion_id: uuid.UUID
    rule_id: str | None
    rule_version: str | None
    model_version: str | None
    confidence: float | None
    gate_results: dict[str, Any] = field(default_factory=dict)
    inputs: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AdvisoryAuditRepo(Protocol):
    async def record(self, row: AdvisoryAuditRow) -> None:
        """Append one immutable audit row for a generated advisory."""
        ...


__all__ = ["AdvisoryAuditRepo", "AdvisoryAuditRow"]
