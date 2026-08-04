"""Tests for app.application.compose_advisory.execute.


Pure unit tests with stub repos + the LogOnlyChatModel-shaped stub.
No real DB, no real LLM call.
"""


from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

from app.application.compose_advisory import (
    ComposeAdvisoryDeps,
    ComposeAdvisoryResult,
    execute,
)
from app.application.ports.ai_suggestion_repo import AiSuggestion
from app.application.ports.alert_repo import AlertFull
from app.application.ports.chat_model import ChatRequest, ChatResponse
from app.application.ports.crop_season_repo import CropSeasonView
from app.domain.alert import AlertType, Severity
from app.domain.plot import DataTier, Plot, PlotStatus
from app.domain.sensor import Reading, TransmissionType

NOW = datetime.datetime(2026, 6, 20, 12, 0, tzinfo=datetime.UTC)
TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
FARMER = uuid.UUID("22222222-2222-2222-2222-222222222222")
FARM = uuid.UUID("33333333-3333-3333-3333-333333333333")
SEASON = uuid.UUID("44444444-4444-4444-4444-444444444444")




# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------
def _alert(**over: object) -> AlertFull:
    base: dict[str, object] = {
        "alert_id": 7,
        "tenant_id": TENANT,
        "farm_id": FARM,
        "farmer_id": FARMER,
        "device_id": "AGR-001",
        "alert_type": AlertType.LOW_BATTERY,
        "severity": Severity.WARNING,
        "alert_message_marathi": "बॅटरी कमी",
        "alert_value": Decimal("3.10"),
        "alert_threshold": Decimal("3.30"),
        "triggered_at": NOW,
        "resolved": False,
        "resolved_at": None,
    }
    base.update(over)
    return AlertFull(**base)  # type: ignore[arg-type]




def _plot(node_id: str = "AGR-001") -> Plot:
    return Plot(
        plot_id="PLOT_AUR_001",
        tenant_id=TENANT,
        farm_id=FARM,
        plot_number=1,
        area_acre=Decimal("1.0"),
        gps_lat=19.9,
        gps_lng=75.7,
        node_id=node_id,
        data_tier=DataTier.SUB_NODE,
        plot_status=PlotStatus.ACTIVE,
        irrigation_valve_id="V_1",
    )




def _season() -> CropSeasonView:
    return CropSeasonView(
        season_id=SEASON,
        tenant_id=TENANT,
        farm_id=FARM,
        plot_id="PLOT_AUR_001",
        crop_name_english="Cotton",
        crop_name_marathi="कापूस",
        crop_category="cash_crop",
        crop_variety="Bt-Pinky",
        sowing_date=datetime.date(2026, 6, 1),
        expected_harvest_date=datetime.date(2026, 12, 1),
        current_growth_stage="vegetative",
        crop_age_days_today=20,
    )




def _reading() -> Reading:
    return Reading(
        tenant_id=TENANT,
        farmer_id=FARMER,
        farm_id=FARM,
        plot_id="PLOT_AUR_001",
        node_id="AGR-001",
        recorded_at=NOW,
        received_at_master=NOW,
        transmission_type=TransmissionType.LORA,
        soil_moisture_avg_pct=Decimal("28.5"),
        battery_voltage_v=Decimal("3.10"),
    )




# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------
class _StubAlertRepo:
    def __init__(self, alert: AlertFull | None) -> None:
        self._alert = alert


    async def create(self, c):
        return 1


    async def last_triggered_at(self, p, a):
        return None


    async def resolve(self, a, n=None):
        pass


    async def list_for_plot(self, p, limit=50):
        return []


    async def find_by_id(self, alert_id: int) -> AlertFull | None:
        return self._alert




class _StubPlotRepo:
    def __init__(self, plots: list[Plot]) -> None:
        self.plots = plots


    async def find(self, plot_id):
        return next((p for p in self.plots if p.plot_id == plot_id), None)


    async def for_farmer(self, farmer_id):
        return self.plots


    async def for_tenant(self, tenant_id):
        return self.plots


    async def update_data_tier(self, p, t):
        pass




class _StubCropSeasonRepo:
    def __init__(self, season: CropSeasonView | None) -> None:
        self._season = season


    async def find_active_for_plot(self, plot_id: str):
        return self._season if (self._season and self._season.plot_id == plot_id) else None




class _StubReadingRepo:
    def __init__(self, readings: list[Reading]) -> None:
        self._readings = readings


    async def save(self, r):
        return 1


    async def latest_for_plot(self, plot_id: str, limit: int):
        return self._readings[:limit]


    async def recent_for_node(self, *args, **kw):
        return []


    async def history_for_stuck_check(self, *args, **kw):
        return []


    async def history_for_mad_check(self, *args, **kw):
        return []




class _StubAiSuggestionRepo:
    def __init__(self) -> None:
        self.created: list[AiSuggestion] = []


    async def create(self, s: AiSuggestion) -> uuid.UUID:
        self.created.append(s)
        return s.suggestion_id


    async def find_by_id(self, suggestion_id):
        return None




class _CapturingChatModel:
    def __init__(self, response_text: str = "बॅटरी बदला. ओलावा कमी आहे. पाणी द्या.") -> None:
        self.response_text = response_text
        self.calls: list[ChatRequest] = []


    async def complete(self, request: ChatRequest) -> ChatResponse:
        self.calls.append(request)
        return ChatResponse(
            text=self.response_text,
            model=request.model,
            input_tokens=120,
            output_tokens=40,
            latency_ms=850,
            finish_reason="stop",
        )




_DEPS_UNSET = object()




def _deps(
    *,
    alert=_DEPS_UNSET,
    plots=_DEPS_UNSET,
    season=_DEPS_UNSET,
    readings=_DEPS_UNSET,
):
    """Sentinel-based defaults: tests can pass ``None`` / ``[]`` to mean
    "exercise the skip path"; only an unset argument falls back to the
    default fixture. The previous ``X or default`` and
    ``X if X is not None else default`` forms both collapsed those two
    cases - this distinguishes them.
    """
    chat = _CapturingChatModel()
    suggestion_repo = _StubAiSuggestionRepo()
    deps = ComposeAdvisoryDeps(
        alert_repo=_StubAlertRepo(_alert() if alert is _DEPS_UNSET else alert),
        plot_repo=_StubPlotRepo([_plot()] if plots is _DEPS_UNSET else plots),
        crop_season_repo=_StubCropSeasonRepo(_season() if season is _DEPS_UNSET else season),
        reading_repo=_StubReadingRepo([_reading()] if readings is _DEPS_UNSET else readings),
        ai_suggestion_repo=suggestion_repo,
        chat_model=chat,
    )
    return deps, chat, suggestion_repo




# ===========================================================================
# Happy path
# ===========================================================================
async def test_compose_persists_suggestion_with_claude_response() -> None:
    deps, chat, repo = _deps()
    out = await execute(alert_id=7, deps=deps, now=NOW)
    assert isinstance(out, ComposeAdvisoryResult)
    assert out.skip_reason is None
    assert out.suggestion is not None
    s = out.suggestion
    assert s.suggestion_type == "alert"
    assert "बॅटरी" in s.full_message_marathi
    assert s.season_id == SEASON
    assert s.crop_stage == "vegetative"
    assert s.crop_age_days == 20
    assert s.tokens_used == 160  # 120 in + 40 out
    assert s.generation_time_ms == 850
    assert len(repo.created) == 1
    # Claude was called once with a system + user prompt.
    assert len(chat.calls) == 1
    req = chat.calls[0]
    assert "AgroGuardian" in req.system
    assert "कापूस" in req.user  # crop_name_marathi in user prompt




async def test_user_prompt_includes_alert_value_and_threshold() -> None:
    deps, chat, _ = _deps()
    await execute(alert_id=7, deps=deps, now=NOW)
    user_prompt = chat.calls[0].user
    assert "3.10" in user_prompt
    assert "3.30" in user_prompt




async def test_user_prompt_includes_latest_reading_when_available() -> None:
    deps, chat, _ = _deps()
    await execute(alert_id=7, deps=deps, now=NOW)
    user_prompt = chat.calls[0].user
    assert "28.5" in user_prompt  # soil_moisture_avg_pct from _reading()




async def test_compose_handles_missing_latest_reading() -> None:
    deps, chat, _ = _deps(readings=[])
    out = await execute(alert_id=7, deps=deps, now=NOW)
    assert out.suggestion is not None
    # User prompt should still include alert + crop info even without
    # a recent reading.
    assert "कापूस" in chat.calls[0].user




# ===========================================================================
# Skip paths
# ===========================================================================
async def test_compose_skips_when_alert_not_found() -> None:
    deps, chat, repo = _deps(alert=None)
    # Override alert_repo to return None.
    deps_no_alert = ComposeAdvisoryDeps(
        alert_repo=_StubAlertRepo(None),
        plot_repo=deps.plot_repo,
        crop_season_repo=deps.crop_season_repo,
        reading_repo=deps.reading_repo,
        ai_suggestion_repo=deps.ai_suggestion_repo,
        chat_model=deps.chat_model,
    )
    out = await execute(alert_id=999, deps=deps_no_alert, now=NOW)
    assert out.suggestion is None
    assert out.skip_reason == "alert_not_found"
    assert chat.calls == []
    assert repo.created == []




async def test_compose_skips_when_plot_cannot_be_resolved() -> None:
    # Empty plot list -> resolver returns None.
    deps, chat, _repo = _deps(plots=[])
    out = await execute(alert_id=7, deps=deps, now=NOW)
    assert out.suggestion is None
    assert out.skip_reason == "plot_not_found"
    assert chat.calls == []




async def test_compose_skips_when_no_active_season() -> None:
    deps, chat, repo = _deps(season=None)
    out = await execute(alert_id=7, deps=deps, now=NOW)
    assert out.suggestion is None
    assert out.skip_reason == "no_active_season"
    assert chat.calls == []  # Claude not even called.
    assert repo.created == []




async def test_compose_skips_when_alert_device_id_is_null() -> None:
    deps, chat, _ = _deps(alert=_alert(device_id=None))
    out = await execute(alert_id=7, deps=deps, now=NOW)
    assert out.skip_reason == "plot_not_found"
    assert chat.calls == []




# ===========================================================================
# Misc
# ===========================================================================
async def test_compose_uses_configured_model_name() -> None:
    deps, chat, _ = _deps()
    # Override the model in deps.
    deps2 = ComposeAdvisoryDeps(
        alert_repo=deps.alert_repo,
        plot_repo=deps.plot_repo,
        crop_season_repo=deps.crop_season_repo,
        reading_repo=deps.reading_repo,
        ai_suggestion_repo=deps.ai_suggestion_repo,
        chat_model=deps.chat_model,
        chat_model_name="claude-haiku-4-5",
    )
    await execute(alert_id=7, deps=deps2, now=NOW)
    assert chat.calls[0].model == "claude-haiku-4-5"
