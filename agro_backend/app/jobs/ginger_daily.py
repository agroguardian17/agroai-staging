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
from typing import TYPE_CHECKING, Any, cast
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
from app.application.ports.advisory_metrics_repo import AdvisoryMetricsRepo
from app.application.ports.ai_suggestion_repo import AiSuggestion, AiSuggestionRepo
from app.application.ports.cluster_repo import ClusterRepo
from app.application.ports.crop_scouting_repo import CropScoutingRepo
from app.application.ports.crop_season_repo import CropSeasonRepo, CropSeasonView
from app.application.ports.farm_repo import FarmRepo
from app.application.ports.farmer_consent_repo import FarmerConsentRepo
from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.farmer_schemes_repo import FarmerSchemesRepo
from app.application.ports.lab_soil_test_repo import LabSoilTestRepo
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.qa_counters_repo import QaCountersRepo
from app.application.ports.reading_repo import ReadingRepo
from app.application.ports.satellite_reading_repo import SatelliteReadingRepo
from app.application.ports.season_economics_repo import SeasonEconomicsRepo
from app.application.ports.season_operations_repo import SeasonOperationsRepo
from app.application.ports.weather_forecast_repo import WeatherForecastRepo
from app.application.ports.weather_station_reading_repo import WeatherStationReadingRepo
from app.application.ports.yield_model_repo import YieldModelRepo
from app.lib import metrics

if TYPE_CHECKING:
    pass


log = structlog.get_logger(__name__)


# Crop key we filter crop_seasons on.
GINGER_CROP_NAME: str = "Ginger"

# ``ai_model_version`` tag written on every advisory this job produces so
# rows can be filtered from the dashboard and from other tools.
GINGER_MODEL_TAG: str = "ginger-engine/v1.0"
# The KB ruleset version an advisory is generated under (advisory audit, §7.3).
# Bump when the deployed KB reload changes the ruleset.
GINGER_KB_VERSION: str = "ginger-kb/v1.0"


@dataclass(frozen=True, slots=True)
class GingerDailyDeps:
    """Ports the job needs. Constructed once by the lifespan wiring."""

    reading_repo: ReadingRepo
    plot_repo: PlotRepo
    crop_season_repo: CropSeasonRepo
    ai_suggestion_repo: AiSuggestionRepo
    farmer_repo: FarmerRepo
    # SYNC DSN — the engine's PostgresSource wants a libpq-style URL for
    # psycopg (v3). We pass this in so the job builder can hand it to
    # ``build_runner(PostgresSource(dsn), ...)``.
    sync_dsn: str
    # Optional weather source for the farm-brain (air temp + humidity + VPD).
    weather_station_reading_repo: WeatherStationReadingRepo | None = None
    # Optional satellite source for the farm-brain (Domain 14 indices).
    satellite_reading_repo: SatelliteReadingRepo | None = None
    # Optional farm source for the farm-brain (soil, water, irrigation facts).
    farm_repo: FarmRepo | None = None
    # Optional weather-forecast source (Open-Meteo window) for D07 rain fields.
    weather_forecast_repo: WeatherForecastRepo | None = None
    # Optional soil-lab source for the farm-brain (KB nutrient chemistry).
    lab_soil_test_repo: LabSoilTestRepo | None = None
    # Optional crop-scouting source (KB pest/disease observations).
    crop_scouting_repo: CropScoutingRepo | None = None
    # Optional per-season economics / operations + per-farmer schemes.
    season_economics_repo: SeasonEconomicsRepo | None = None
    season_operations_repo: SeasonOperationsRepo | None = None
    farmer_schemes_repo: FarmerSchemesRepo | None = None
    farmer_consent_repo: FarmerConsentRepo | None = None
    # Optional advisory-performance source (D12 compliance counters).
    advisory_metrics_repo: AdvisoryMetricsRepo | None = None
    # Optional Domain 11 yield-model source (U-value register + prediction log).
    yield_model_repo: YieldModelRepo | None = None
    # Optional D12 peer-cluster source (fills the farm-brain ``cluster_id``).
    cluster_repo: ClusterRepo | None = None
    # Optional D12 QA-counter source (true/false-alarm + photo counts).
    qa_counters_repo: QaCountersRepo | None = None
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
        weather_station_reading_repo=deps.weather_station_reading_repo,
        satellite_reading_repo=deps.satellite_reading_repo,
        farm_repo=deps.farm_repo,
        farmer_repo=deps.farmer_repo,
        weather_forecast_repo=deps.weather_forecast_repo,
        lab_soil_test_repo=deps.lab_soil_test_repo,
        crop_scouting_repo=deps.crop_scouting_repo,
        season_economics_repo=deps.season_economics_repo,
        season_operations_repo=deps.season_operations_repo,
        farmer_schemes_repo=deps.farmer_schemes_repo,
        farmer_consent_repo=deps.farmer_consent_repo,
        advisory_metrics_repo=deps.advisory_metrics_repo,
        yield_model_repo=deps.yield_model_repo,
        cluster_repo=deps.cluster_repo,
        qa_counters_repo=deps.qa_counters_repo,
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

    # Resolve the farm's owner once per plot (was a hardcoded pilot UUID).
    farmer_id = await deps.farmer_repo.owner_of_farm(season.farm_id)
    if farmer_id is None:
        log.warning("ginger_daily.no_owner", plot_id=season.plot_id, farm_id=str(season.farm_id))
        return 0

    rows = 0
    for msg in engine_result.get("messages", []):
        await _persist_message(deps.ai_suggestion_repo, season, farmer_id, msg, today)
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
    import psycopg2  # type: ignore[import-untyped]

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
    return cast(dict[str, Any], runner.run_day(plot_id, state, today))


# ---------------------------------------------------------------------------
# Persistence to our ai_suggestions table
# ---------------------------------------------------------------------------


async def _persist_message(
    repo: AiSuggestionRepo,
    season: CropSeasonView,
    farmer_id: uuid.UUID,
    msg: Any,
    today: date,
) -> None:
    """Write one engine message as an ``ai_suggestions`` row."""
    body = msg.render() if hasattr(msg, "render") else str(msg)
    suggestion = AiSuggestion(
        suggestion_id=uuid.uuid4(),
        tenant_id=season.tenant_id,
        farmer_id=farmer_id,
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
        rule_id=getattr(msg, "rule_id", None),  # links the advisory to its KB rule (D12 QA)
        confidence=getattr(msg, "confidence", None),  # audit trail §7.3
        rule_version=GINGER_KB_VERSION,
    )
    await repo.create(suggestion)


def _today_in(tz: ZoneInfo) -> date:
    """Compute the current date in the given timezone.

    Do NOT use ``date.today()`` — Docker containers run in UTC and midnight
    UTC != midnight IST. The pilot's day boundary is IST.
    """
    return datetime.now(UTC).astimezone(tz).date()


__all__ = [
    "GINGER_CROP_NAME",
    "GINGER_KB_VERSION",
    "GINGER_MODEL_TAG",
    "GingerDailyDeps",
    "run_daily",
]
