"""Use case: compose a Marathi advisory for an alert and persist it.

Trigger: an ``alert.created`` event with ``{alert_id, ...}``.

Steps:

1. Fetch the alert (``AlertRepo.find_by_id``).
2. Fetch the active CropSeason for the plot. If none -> skip (we
   can't persist ``ai_suggestions`` without ``season_id``; log + bail).
3. Fetch the latest sensor reading (one-row lookback) for context.
4. Build the Claude prompt (system + user). The system prompt fixes
   the persona, language, and length; the user prompt carries the
   alert + context.
5. Call ``ChatModel.complete()``.
6. Persist the response as one row in ``ai_suggestions``
   (``suggestion_type='alert'``).
7. Return the persisted ``AiSuggestion`` or None when skipped.

PURE w.r.t. imports: stdlib + ports + domain only. No infra.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.application.ports.ai_suggestion_repo import AiSuggestion, AiSuggestionRepo
from app.application.ports.alert_repo import AlertFull, AlertRepo
from app.application.ports.chat_model import ChatModel, ChatRequest
from app.application.ports.crop_season_repo import CropSeasonRepo, CropSeasonView
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.reading_repo import ReadingRepo
from app.domain.plot import Plot
from app.domain.sensor import Reading


@dataclass(frozen=True, slots=True)
class ComposeAdvisoryDeps:
    alert_repo: AlertRepo
    plot_repo: PlotRepo
    crop_season_repo: CropSeasonRepo
    reading_repo: ReadingRepo
    ai_suggestion_repo: AiSuggestionRepo
    chat_model: ChatModel
    chat_model_name: str = "claude-sonnet-4-5"
    max_tokens: int = 600


@dataclass(frozen=True, slots=True)
class ComposeAdvisoryResult:
    suggestion: AiSuggestion | None
    skip_reason: str | None = None


# ---------------------------------------------------------------------------
# Prompt templates - intentionally co-located with the use case.
# Future rounds may externalise these into a YAML registry.
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_MARATHI = (
    "तुम्ही 'AgroGuardian' चे शेतीतज्ञ आहात. महाराष्ट्रातील औरंगाबाद "
    "जिल्ह्यातील शेतकऱ्यांना सल्ला देता. केवळ मराठीत उत्तर द्या. "
    "तुमचे उत्तर ३-४ छोट्या ओळींचे असावे - WhatsApp वर वाचता येईल असे. "
    "वैद्यकीय / कायदेशीर सल्ला देऊ नका. आर्थिक मदतीचे आश्वासन देऊ नका. "
    "फक्त सेन्सर डेटा + पीकाच्या टप्प्यावर आधारित कृषी सूचना द्या."
)


def _user_prompt(
    alert: AlertFull,
    season: CropSeasonView,
    latest_reading: Reading | None,
    plot: Plot,
) -> str:
    """Build the user-facing prompt with all the context the model needs."""
    lines: list[str] = []
    lines.append(f"पीक: {season.crop_name_marathi} ({season.crop_variety})")
    if season.current_growth_stage:
        lines.append(f"पीकाचा टप्पा: {season.current_growth_stage}")
    if season.crop_age_days_today is not None:
        lines.append(f"पीकाचे वय: {season.crop_age_days_today} दिवस")
    lines.append(f"शेतपटी क्षेत्र: {plot.area_acre} एकर")
    lines.append("")
    lines.append(f"अलर्ट प्रकार: {alert.alert_type.value}")
    lines.append(f"तीव्रता: {alert.severity.value}")
    lines.append(f"नियम मेसेज: {alert.alert_message_marathi}")
    if alert.alert_value is not None:
        lines.append(f"मापन मूल्य: {alert.alert_value}")
    if alert.alert_threshold is not None:
        lines.append(f"उंबरठा: {alert.alert_threshold}")
    if latest_reading is not None:
        if latest_reading.soil_moisture_avg_pct is not None:
            lines.append(f"मातीतील ओलावा (नवीन): {latest_reading.soil_moisture_avg_pct}%")
        if latest_reading.soil_ph is not None:
            lines.append(f"मातीचा pH: {latest_reading.soil_ph}")
        if latest_reading.battery_voltage_v is not None:
            lines.append(f"बॅटरी व्होल्टेज: {latest_reading.battery_voltage_v}V")
    lines.append("")
    lines.append(
        "वरील माहितीच्या आधारे ३-४ ओळींची मराठी सल्ला तयार करा. शेतकऱ्याला आज काय करायला हवे ते सांगा."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------


async def execute(
    *,
    alert_id: int,
    deps: ComposeAdvisoryDeps,
    now: datetime,
) -> ComposeAdvisoryResult:
    """Run the full advisory pipeline for one alert."""
    alert = await deps.alert_repo.find_by_id(alert_id)
    if alert is None:
        return ComposeAdvisoryResult(suggestion=None, skip_reason="alert_not_found")

    # device_id -> plot. We trust the device->plot association via
    # device_registry; for the pilot we look up the plot directly
    # through the alert's device_id by joining inside plot_repo or
    # falling back to the alerts row's farm_id when device is null.
    plot = await _resolve_plot(alert, deps)
    if plot is None:
        return ComposeAdvisoryResult(suggestion=None, skip_reason="plot_not_found")

    season = await deps.crop_season_repo.find_active_for_plot(plot.plot_id)
    if season is None:
        # We can't persist ai_suggestions without a season_id (NOT NULL).
        # This is a post-harvest gap; advisory generation pauses until
        # the next sowing.
        return ComposeAdvisoryResult(suggestion=None, skip_reason="no_active_season")

    latest_readings = await deps.reading_repo.latest_for_plot(plot.plot_id, limit=1)
    latest_reading = latest_readings[0] if latest_readings else None

    request = ChatRequest(
        system=SYSTEM_PROMPT_MARATHI,
        user=_user_prompt(alert, season, latest_reading, plot),
        model=deps.chat_model_name,
        max_tokens=deps.max_tokens,
    )
    response = await deps.chat_model.complete(request)

    suggestion = AiSuggestion(
        suggestion_id=uuid.uuid4(),
        tenant_id=alert.tenant_id,
        farmer_id=alert.farmer_id,
        farm_id=alert.farm_id,
        plot_id=plot.plot_id,
        season_id=season.season_id,
        generated_at=now,
        suggestion_type="alert",
        full_message_marathi=response.text,
        ai_model_version=response.model,
        tokens_used=response.input_tokens + response.output_tokens,
        generation_time_ms=response.latency_ms,
        crop_age_days=season.crop_age_days_today,
        crop_stage=season.current_growth_stage,
    )
    persisted_id = await deps.ai_suggestion_repo.create(suggestion)
    # Round-trip the server-assigned id (no-op when our uuid wins, but
    # the repo retains the right to override).
    persisted = AiSuggestion(
        suggestion_id=persisted_id,
        tenant_id=suggestion.tenant_id,
        farmer_id=suggestion.farmer_id,
        farm_id=suggestion.farm_id,
        plot_id=suggestion.plot_id,
        season_id=suggestion.season_id,
        generated_at=suggestion.generated_at,
        suggestion_type=suggestion.suggestion_type,
        full_message_marathi=suggestion.full_message_marathi,
        ai_model_version=suggestion.ai_model_version,
        tokens_used=suggestion.tokens_used,
        generation_time_ms=suggestion.generation_time_ms,
        crop_age_days=suggestion.crop_age_days,
        crop_stage=suggestion.crop_stage,
    )
    return ComposeAdvisoryResult(suggestion=persisted)


async def _resolve_plot(alert: AlertFull, deps: ComposeAdvisoryDeps) -> Plot | None:
    """Look up the Plot for an alert.

    Strategy: the alert carries ``device_id`` (the Sub Node serial).
    Round 6's PlotRepo.find takes a plot_id, not a device_id, so we
    iterate the farm's plots and pick the one whose node matches.
    For the pilot's 1-farm-4-plots scope this is fine; a future
    PlotRepo.find_by_device method would optimise this.
    """
    if alert.device_id is None:
        return None
    # Get all plots for this farmer (small set in pilot), find the match.
    plots = await deps.plot_repo.for_farmer(alert.farmer_id)
    for plot in plots:
        if plot.node_id == alert.device_id:
            return plot
    return None


__all__ = ["ComposeAdvisoryDeps", "ComposeAdvisoryResult", "execute"]
