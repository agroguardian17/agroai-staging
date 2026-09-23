"""D12 weekly-digest generator: window, rendering, and the standing rules."""

from __future__ import annotations

from datetime import date, datetime

from app.application.build_qa_digest import build_weekly_digest
from app.application.ports.qa_digest_repo import (
    BiasObservationSummary,
    RuleCount,
    WeeklyQaData,
)
from app.lib.time import IST

# Sunday 2026-06-21 18:00 IST -> review week Monday is 2026-06-15.
_NOW = datetime(2026, 6, 21, 18, 0, tzinfo=IST)


class _FakeRepo:
    def __init__(self, data: WeeklyQaData) -> None:
        self.data = data
        self.called_with: tuple[date, date, int] | None = None

    async def gather(
        self, week_start: date, week_end: date, *, top_fp_rules: int = 10
    ) -> WeeklyQaData:
        self.called_with = (week_start, week_end, top_fp_rules)
        return self.data


def _data(**over: object) -> WeeklyQaData:
    base = dict(
        week_start=date(2026, 6, 15),
        week_end=date(2026, 6, 22),
        classification_counts={"confirmed_true_positive": 6, "false_positive": 2, "unresolved": 2},
        total_advisories=20,
        classified_count=10,
        false_positive_rules=[RuleCount("D05-RF-001", 2)],
        non_compliance_counts={"cost_barrier": 3, "forgot": 1},
        bias_observations=[
            BiasObservationSummary(
                bias_type="over_issuing",
                scope_domain="D05",
                scope_rule_id="D05-RF-001",
                observation_mr="खूप जास्त सूचना",
                suggested_change_mr="थ्रेशोल्ड वाढवा",
                observed_by="agronomist_a",
                kb_author_read=False,
            )
        ],
        unread_bias_total=4,
        photo_backlog=12,
    )
    base.update(over)
    return WeeklyQaData(**base)  # type: ignore[arg-type]


async def test_window_is_ist_monday_and_filenames_use_week_start() -> None:
    repo = _FakeRepo(_data())
    digest = await build_weekly_digest(repo=repo, now=_NOW, top_fp_rules=5)
    assert repo.called_with == (date(2026, 6, 15), date(2026, 6, 22), 5)
    assert digest.weekly_report.filename == "weekly_report_2026_06_15.md"
    assert digest.bias_digest.filename == "bias_digest_2026_06_15.md"


async def test_weekly_report_shows_rates_with_raw_basis() -> None:
    digest = await build_weekly_digest(repo=_FakeRepo(_data()), now=_NOW)
    body = digest.weekly_report.content
    # False-positive rate 2 of 10 = 20%; coverage 10 of 20 = 50%.
    assert "20% (2 of 10)" in body
    assert "50% (10 of 20)" in body
    assert "| Confirmed true positive | 6 |" in body
    assert "D05-RF-001" in body
    assert "cost_barrier" in body
    assert "12" in body  # photo backlog


async def test_zero_denominator_is_na_not_fabricated() -> None:
    data = _data(
        classification_counts={},
        classified_count=0,
        total_advisories=0,
        false_positive_rules=[],
        non_compliance_counts={},
    )
    body = (await build_weekly_digest(repo=_FakeRepo(data), now=_NOW)).weekly_report.content
    assert "n/a (0 of 0)" in body
    assert "0% (0 of 0)" not in body  # never fabricate a rate from nothing
    assert "_No false positives recorded this week._" in body
    assert "_No non-compliance captured this week._" in body


async def test_bias_digest_preserves_marathi_and_flags_unread() -> None:
    body = (await build_weekly_digest(repo=_FakeRepo(_data()), now=_NOW)).bias_digest.content
    assert "खूप जास्त सूचना" in body  # farmer/agronomist voice preserved (rule #3)
    assert "थ्रेशोल्ड वाढवा" in body
    assert "UNREAD" in body
    assert "awaiting KB author action: 4" in body


async def test_bias_digest_handles_empty_week() -> None:
    body = (
        await build_weekly_digest(repo=_FakeRepo(_data(bias_observations=[])), now=_NOW)
    ).bias_digest.content
    assert "_No bias observations recorded this week._" in body
