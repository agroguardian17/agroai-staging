"""Guard that the Advisory Journey's columns exist on ai_suggestions (R3.3).

The Advisory Journey page (dashboard page 25) reads the whole advisory lifecycle
from one `ai_suggestions` row — trigger (rule_id), compose metadata, the Marathi
message, and the migration-0016 `delivery_*` state machine. If any of those
columns were renamed/dropped the page would break at runtime; this DB-gated test
selects the exact projection against the migrated schema so CI catches it first.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]

_JOURNEY_PROJECTION = (
    "suggestion_id, generated_at, plot_id, suggestion_type, rule_id, "
    "crop_age_days, crop_stage, soil_moisture_at_time, ndvi_at_time, "
    "ai_model_version, prompt_template_version, tokens_used, generation_time_ms, llm_cost_inr, "
    "full_message_marathi, delivery_status, delivery_attempts, delivery_claimed_at, "
    "delivery_next_retry_at, delivery_last_error, delivery_provider_message_id, "
    "whatsapp_sent, whatsapp_sent_at"
)


async def test_advisory_journey_projection_is_valid(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with sessionmaker() as s:
        # A dropped/renamed column raises here; shape-only, so an empty table is fine.
        await s.execute(text(f"SELECT {_JOURNEY_PROJECTION} FROM ai_suggestions LIMIT 1"))
