"""Use case: turn a farmer's WhatsApp reply into a ``farmer_actions`` row.

Attributes the reply to the farmer's most recent sent advisory and captures the
lightly-parsed intent: a quantity (litres) and a yes/no on whether they followed
the advice. Kept deliberately conservative — the raw text is always preserved in
``farmer_note`` so nothing is lost to a parsing miss.

PURE w.r.t. imports: stdlib + ports only. No infra.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import datetime

from app.application.ports.farmer_action_repo import FarmerActionInput, FarmerActionRepo

# Affirmatives / negatives in Marathi (Devanagari + roman) and English.
_YES = {"हो", "होय", "हा", "केले", "दिले", "yes", "y", "ho", "hoy", "kele", "done", "ok"}
_NO = {"नाही", "नको", "no", "n", "nahi", "nako", "not"}
# Match ASCII digits only, after normalising Devanagari digits to ASCII —
# float() cannot parse Devanagari, and farmers may type either script.
_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
_NUM = re.compile(r"[0-9]+(?:\.[0-9]+)?")


def _tokens(text: str) -> set[str]:
    return {t.strip(".,!?;:").lower() for t in text.split()}


def parse_quantity(text: str) -> float | None:
    """First number in the reply (litres for a watering action)."""
    m = _NUM.search(text.translate(_DEVANAGARI_DIGITS))
    return float(m.group()) if m else None


def parse_followed(text: str) -> bool | None:
    """True/False if the reply clearly affirms/denies, else None."""
    toks = _tokens(text)
    yes = bool(toks & _YES)
    no = bool(toks & _NO)
    if yes and not no:
        return True
    if no and not yes:
        return False
    return None


@dataclass(frozen=True, slots=True)
class RecordActionDeps:
    farmer_action_repo: FarmerActionRepo
    within_days: int = 3


async def execute(
    *, farmer_id: uuid.UUID, reply_text: str | None, deps: RecordActionDeps, now: datetime
) -> int | None:
    """Record a farmer_action from a reply. None when there's nothing to attribute."""
    ctx = await deps.farmer_action_repo.latest_advisory_for_farmer(
        farmer_id, within_days=deps.within_days
    )
    if ctx is None:
        return None  # no recent advisory to attribute the reply to

    text = reply_text or ""
    litres = parse_quantity(text)
    followed = parse_followed(text)
    # A watering advisory (or a numeric reply) => a watering action; else 'other'.
    action_type = "watering" if (ctx.is_watering or litres is not None) else "other"

    return await deps.farmer_action_repo.record(
        FarmerActionInput(
            tenant_id=ctx.tenant_id,
            farmer_id=ctx.farmer_id,
            farm_id=ctx.farm_id,
            season_id=ctx.season_id,
            plot_id=ctx.plot_id,
            ai_suggestion_id=ctx.suggestion_id,
            action_date=now.date(),
            action_type=action_type,
            ai_suggested=True,
            farmer_followed_ai=followed,
            water_liters=litres if action_type == "watering" else None,
            farmer_note=(text[:2000] or None),
        )
    )


__all__ = [
    "RecordActionDeps",
    "execute",
    "parse_followed",
    "parse_quantity",
]
