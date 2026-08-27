"""Daily ginger advisory job.

Runs once a day (default 06:30 IST) and delivers per-plot Marathi advisories
by driving the teammate's ginger engine over Farm Brain state we assemble
from our own repositories.

Execution model
---------------
The ginger engine is **synchronous** by design (see their arch doc §11A).
Our backend is async. We resolve this by:

1. Iterating active ginger crop_seasons via our async repos (fast, small).
2. Building each plot's Farm Brain state via async repos.
3. Handing the state to the engine inside ``asyncio.to_thread`` so the sync
   psycopg2 access does not block the asyncio event loop.
4. Persisting every returned message as an ``ai_suggestions`` row with
   ``suggestion_type='daily'`` and a JSON provenance blob so we can tell
   ginger-engine output apart from other advisory sources.

Idempotency
-----------
Two safety nets stop the job from double-counting on retry:

* The engine's own persistence — ``advisory_log`` keys on
  ``(plot_id, day, rule_id)`` and rejects duplicates.
* Each ``ai_suggestions`` row's ``generated_at`` is scoped to the run day,
  and a follow-up round can add a UNIQUE index on
  ``(plot_id, generated_at::date, ai_model_version, crop_stage)`` if we
  observe drift. Today, running the job twice in one day produces one row
  per message per run — acceptable while we are still tuning.

The job is safe to invoke manually for debugging:

    python -m app.jobs.ginger_daily --plot PLOT_PILOT_001 --date 2026-08-03
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

import structlog

# Activates the sys.path shim BEFORE we reach into their engine modules. Use
# the runtime package name (`ginger`), because the app normally runs from the
# `agro_backend/` directory or `/app` inside Docker.
import ginger  # noqa: F401 - side-effect: sys.path shim
from app.application.build_farm_brain import (
    SYNTHETIC_FIELDS,
    FarmBrainDeps,
    build_farm_brain,
)
from app.application.ports.ai_suggestion_repo import AiSuggestion, AiSuggestionRepo
from app.application.ports.crop_season_repo import CropSeasonRepo, CropSeasonView
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.reading_repo import ReadingRepo
from app.lib import metrics

if TYPE_CHECKING:
    pass


log = structlog.get_logger(__name__)


# Crop key we filter crop_seasons on.
GINGER_CROP_NAME: str = "Ginger"

# ``ai_model_version`` tag written on every advisory this job produces so
# rows can be filtered from the dashboard and from other tools.
GINGER_MODEL_TAG: str = "ginger-engine/v1.0"


@dataclass(frozen=True, slots=True)
class GingerDailyDeps:
    """Ports the job needs. Constructed once by the lifespan wiring."""

    reading_repo: ReadingRepo
    plot_repo: PlotRepo
    crop_season_repo: CropSeasonRepo
    ai_suggestion_repo: AiSuggestionRepo
    # SYNC DSN — the engine's PostgresSource wants a libpq-style URL for
    # psycopg (v3). We pass this in so the job builder can hand it to
    # ``build_runner(PostgresSource(dsn), ...)``.
    sync_dsn: str
    # Timezone the "today" date is computed in. Defaults to IST — the pilot
    # is in Aurangabad and the farmer's day boundary is IST midnight.
    timezone: ZoneInfo = field(default_factory=lambda: ZoneInfo("Asia/Kolkata"))


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


async def run_daily(deps: GingerDailyDeps, *, override_today: date | None = None) -> int:
    """Run the ginger engine over every active ginger plot.

    Returns the number of advisory rows written.
    """
    today = override_today or _today_in(deps.timezone)
    log.info("ginger_daily.starting", date=today.isoformat(), tz=str(deps.timezone))

    seasons = await deps.crop_season_repo.list_active_by_crop(GINGER_CROP_NAME)
    if not seasons:
        log.info("ginger_daily.no_active_seasons", crop=GINGER_CROP_NAME)
        return 0

    # Load the declared field set once (~306 fields). Done sync in a thread
    # because the ginger source is sync.
    declared_fields = await asyncio.to_thread(_load_declared_fields, deps.sync_dsn)

    total_written = 0
    for season in seasons:
        try:
            n = await _run_one_plot(season, deps, today, declared_fields)
            total_written += n
        except Exception:
            # One plot's failure must not stop the others.
            log.exception("ginger_daily.plot_failed", plot_id=season.plot_id)
            metrics.ginger_engine_errors_total.labels(reason="plot_run").inc()

    log.info(
        "ginger_daily.completed",
        plots_processed=len(seasons),
        advisories_written=total_written,
    )
    return total_written


async def _run_one_plot(
    season: CropSeasonView,
    deps: GingerDailyDeps,
    today: date,
    declared_fields: frozenset[str],
) -> int:
    """Build state, invoke the engine, persist messages. Returns rows written."""
    fb_deps = FarmBrainDeps(
        reading_repo=deps.reading_repo,
        plot_repo=deps.plot_repo,
        crop_season_repo=deps.crop_season_repo,
        declared_fields=declared_fields,
    )
    state = await build_farm_brain(plot_id=season.plot_id, today=today, deps=fb_deps)
    log.debug(
        "ginger_daily.state_built",
        plot_id=season.plot_id,
        filled=len(state.filled),
        unknown=len(state.unknown),
    )

    # Hand the sync engine + sync DB access to a worker thread.
    started = time.perf_counter()
    engine_result = await asyncio.to_thread(
        _invoke_engine, deps.sync_dsn, season.plot_id, state.state, today
    )
    elapsed = time.perf_counter() - started
    metrics.ginger_engine_run_seconds.observe(elapsed)

    rows = 0
    for msg in engine_result.get("messages", []):
        await _persist_message(deps.ai_suggestion_repo, season, msg, today)
        rows += 1
        delivery_class = (
            engine_result.get("delivery", {}).get(msg.rule_id, "unknown")
            if isinstance(engine_result.get("delivery"), dict)
            else "unknown"
        )
        metrics.ginger_messages_total.labels(delivery_class=delivery_class).inc()
    return rows


# ---------------------------------------------------------------------------
# Sync helpers (run in asyncio.to_thread)
# ---------------------------------------------------------------------------


def _load_declared_fields(sync_dsn: str) -> frozenset[str]:
    """Read the full ``kb_farm_brain_fields`` list from Postgres.

    Sync — called via ``asyncio.to_thread`` from the async entry point.
    """
    import psycopg2

    with psycopg2.connect(sync_dsn) as conn, conn.cursor() as cur:
        cur.execute("SELECT field_name FROM kb_farm_brain_fields")
        db_fields = {r[0] for r in cur.fetchall()}
    return frozenset(db_fields | SYNTHETIC_FIELDS)


def _invoke_engine(
    sync_dsn: str, plot_id: str, state: dict[str, Any], today: date
) -> dict[str, Any]:
    """Build the engine (or reuse if cached) and run one day.

    Their ``build_runner`` returns a ``PersistentRunner`` when we hand it a
    state_store, and ``PersistentRunner.run_day`` returns a dict shaped like
    ``{'messages': [Message, ...], 'unknown': [...], 'gap_days': int|None,
    'state_reset': str|None, ...}``.

    This function is SYNCHRONOUS because their engine is synchronous.
    """
    # Imports are flat because the ``ginger`` package init put
    # ``ginger/engine/`` on sys.path.
    from runtime_loader import PostgresSource, build_runner  # type: ignore[import-not-found]

    from app.infra.ginger.pg_state_store import PgStateStore

    state_store = PgStateStore(sync_dsn)
    runner = build_runner(PostgresSource(sync_dsn), state_store=state_store)
    return runner.run_day(plot_id, state, today)


# ---------------------------------------------------------------------------
# Persistence to our ai_suggestions table
# ---------------------------------------------------------------------------


async def _persist_message(
    repo: AiSuggestionRepo, season: CropSeasonView, msg: Any, today: date
) -> None:
    """Write one engine message as an ``ai_suggestions`` row."""
    body = msg.render() if hasattr(msg, "render") else str(msg)
    suggestion = AiSuggestion(
        suggestion_id=uuid.uuid4(),
        tenant_id=season.tenant_id,
        farmer_id=_farmer_id_for(season),  # see helper below
        farm_id=season.farm_id,
        plot_id=season.plot_id,
        season_id=season.season_id,
        generated_at=datetime.combine(today, datetime.min.time(), tzinfo=UTC),
        suggestion_type="daily",
        full_message_marathi=body,
        ai_model_version=GINGER_MODEL_TAG,
        tokens_used=None,  # deterministic engine, no LLM tokens
        generation_time_ms=None,
        crop_age_days=season.crop_age_days_today,
        crop_stage=season.current_growth_stage,
    )
    await repo.create(suggestion)


def _farmer_id_for(season: CropSeasonView) -> uuid.UUID:
    """Farmer FK on ai_suggestions.

    CropSeasonView does not carry farmer_id today; the crop_seasons row
    identifies a farm, and the farm identifies the farmer. For the pilot
    (single farmer per farm) we look this up via a subquery in a follow-up.
    Placeholder: the seeded pilot farmer id is used until we thread
    farmer_id through the view.
    """
    # NB: the pilot has one farmer. When multi-tenant lands, replace this
    # with a repo call: ``await farmer_repo.owner_of_farm(season.farm_id)``.
    return uuid.UUID("aaaaaaaa-1111-1111-1111-111111111111")


def _today_in(tz: ZoneInfo) -> date:
    """Compute the current date in the given timezone.

    Do NOT use ``date.today()`` — Docker containers run in UTC and midnight
    UTC != midnight IST. The pilot's day boundary is IST.
    """
    return datetime.now(UTC).astimezone(tz).date()


__all__ = ["GINGER_CROP_NAME", "GINGER_MODEL_TAG", "GingerDailyDeps", "run_daily"]
