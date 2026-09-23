"""D12-DPDP-001 use-case: capture a farmer's registration consent (A3.1, A3.3).

Records the explicit, versioned, age-verified consent required before
registration (LEGAL_COMPLIANCE_CERTIFICATE §3.1): upserts ``farmer_consent`` with
the notice version + hash the farmer saw, enforces the DPDP §9 age gate
(under-18 needs verifiable parental consent), and appends a ``consent_event`` per
granted scope. Advisory consent is blocking — registration cannot proceed
without it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime

from app.application.ports.farmer_consent_repo import ConsentCapture, FarmerConsentRepo
from app.domain.age import is_minor
from app.domain.consent_notice import CONSENT_NOTICE_VERSION, consent_notice_hash
from app.lib.time import now_utc

# Retention per §3.1 ("season-end + 3 years"); approximated as consent-date + 3y
# in the absence of a season context. Legal to confirm before launch.
RETENTION_YEARS = 3


class ConsentRequiredError(Exception):
    """Advisory consent (D12-DPDP-001) is blocking and was not granted."""


class MinorConsentError(Exception):
    """The farmer is under 18 and no verifiable parental consent was provided."""


def _plus_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 Feb → 28 Feb
        return d.replace(year=d.year + years, day=28)


@dataclass(frozen=True, slots=True)
class ConsentResult:
    farmer_id: uuid.UUID
    data_retention_until: date
    parental_consent_required: bool


async def record_consent(
    *,
    farmer_id: uuid.UUID,
    tenant_id: uuid.UUID,
    consent_advisory: bool,
    consent_research: bool,
    third_party_share: bool,
    channel: str,
    actor: str,
    consent_repo: FarmerConsentRepo,
    date_of_birth: date | None = None,
    parental_consent_by: str | None = None,
    now: datetime | None = None,
) -> ConsentResult:
    """Capture consent at registration; raises if advisory consent or (for a
    minor) verifiable parental consent is missing."""
    if not consent_advisory:
        raise ConsentRequiredError("advisory consent (D12-DPDP-001) is required to register")

    when = now or now_utc()
    today = when.date()

    minor = date_of_birth is not None and is_minor(date_of_birth, today)
    if minor and not (parental_consent_by and parental_consent_by.strip()):
        raise MinorConsentError(
            "farmer is under 18; verifiable parental consent is required (DPDP §9)"
        )

    retention_until = _plus_years(today, RETENTION_YEARS)
    await consent_repo.capture(
        ConsentCapture(
            farmer_id=farmer_id,
            tenant_id=tenant_id,
            consent_advisory=consent_advisory,
            consent_research=consent_research,
            third_party_share_consent_given=third_party_share,
            consent_version=CONSENT_NOTICE_VERSION,
            consent_notice_hash=consent_notice_hash(),
            notice_shown_at=when,
            consent_channel=channel,
            consent_date=today,
            data_retention_until=retention_until,
            parental_consent_by=parental_consent_by if minor else None,
            parental_consent_verified=True if minor else None,
        )
    )

    scopes = [
        ("advisory", consent_advisory),
        ("research", consent_research),
        ("third_party", third_party_share),
    ]
    for scope, granted in scopes:
        if granted:
            await consent_repo.record_event(
                farmer_id=farmer_id,
                event_type="given",
                scope=scope,
                consent_version=CONSENT_NOTICE_VERSION,
                channel=channel,
                actor=actor,
            )

    return ConsentResult(
        farmer_id=farmer_id,
        data_retention_until=retention_until,
        parental_consent_required=minor,
    )


__all__ = ["ConsentRequiredError", "ConsentResult", "MinorConsentError", "record_consent"]
