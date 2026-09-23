"""D12 weekly-digest generator (D12_QA_WORKFLOW §5.4).

Builds the two Markdown documents the Sunday-18:00-IST cron emits from the four
QA tables — ``weekly_report_{date}.md`` for the agronomist and
``bias_digest_{date}.md`` for the KB author. Pure given the gathered read model;
the scheduler gathers, builds, then writes the files.

Standing agronomy rules honoured here: every rate shows its raw numerator and
denominator (rule #1), a zero denominator surfaces as ``n/a`` rather than a
fabricated 0 % (rule #2), and each farmer/agronomist observation is carried in
its original Marathi (rule #3).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.ports.qa_digest_repo import QaDigestRepo, WeeklyQaData
from app.lib.time import IST, now_ist


@dataclass(frozen=True, slots=True)
class DigestDoc:
    filename: str
    content: str


@dataclass(frozen=True, slots=True)
class WeeklyDigest:
    weekly_report: DigestDoc
    bias_digest: DigestDoc
    data: WeeklyQaData


def _review_window(now: datetime) -> tuple[datetime, datetime]:
    """The [Monday 00:00, next-Monday 00:00) IST window containing ``now``."""
    ist = now.astimezone(IST)
    monday = (ist - timedelta(days=ist.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return monday, monday + timedelta(days=7)


def _rate(numerator: int, denominator: int) -> str:
    """A percentage with its raw basis, or ``n/a`` when nothing was measured."""
    if denominator == 0:
        return "n/a (0 of 0)"
    return f"{numerator / denominator * 100:.0f}% ({numerator} of {denominator})"


def _render_weekly_report(data: WeeklyQaData) -> str:
    total_classified = sum(data.classification_counts.values())
    tp = data.classification_counts.get("confirmed_true_positive", 0)
    fp = data.classification_counts.get("false_positive", 0)
    unresolved = data.classification_counts.get("unresolved", 0)

    lines: list[str] = [
        f"# Weekly advisory-QA report — week of {data.week_start.isoformat()}",
        "",
        f"Review window (IST): {data.week_start.isoformat()} to "
        f"{(data.week_end - timedelta(days=1)).isoformat()}",
        "",
        "## Classification",
        "",
        "| Verdict | Count |",
        "| --- | ---: |",
        f"| Confirmed true positive | {tp} |",
        f"| False positive | {fp} |",
        f"| Unresolved | {unresolved} |",
        f"| **Total classified** | **{total_classified}** |",
        "",
        "## Key rates (D12 §7)",
        "",
        f"- **False-positive rate** (D12-EVAL-002): {_rate(fp, total_classified)} "
        "— target ≤ 15% Season 1",
        f"- **Classification coverage** (D12-EVAL-003): "
        f"{_rate(data.classified_count, data.total_advisories)} — target ≥ 70% Season 1",
        "",
        "> Action-compliance rate (D12-EVAL-001) needs the farmer-action linkage and "
        "is not computed in the v1 digest.",
        "",
        "## Top false-positive rules",
        "",
    ]
    if data.false_positive_rules:
        lines += ["| Rule | False positives |", "| --- | ---: |"]
        lines += [f"| {r.rule_id} | {r.count} |" for r in data.false_positive_rules]
    else:
        lines.append("_No false positives recorded this week._")
    lines += ["", "## Non-compliance reasons", ""]
    if data.non_compliance_counts:
        lines += ["| Reason | Count |", "| --- | ---: |"]
        lines += [
            f"| {reason} | {count} |"
            for reason, count in sorted(
                data.non_compliance_counts.items(), key=lambda kv: (-kv[1], kv[0])
            )
        ]
    else:
        lines.append("_No non-compliance captured this week._")
    lines += [
        "",
        "## Backlogs",
        "",
        f"- Photo labelling backlog (>7 days unlabelled): {data.photo_backlog} — target ≤ 20",
        f"- Bias observations awaiting KB author: {data.unread_bias_total}",
        "",
    ]
    return "\n".join(lines)


def _render_bias_digest(data: WeeklyQaData) -> str:
    lines: list[str] = [
        f"# Bias digest for the KB author — week of {data.week_start.isoformat()}",
        "",
        f"Bias observations recorded this week: {len(data.bias_observations)}",
        f"Total awaiting KB author action: {data.unread_bias_total}",
        "",
    ]
    if not data.bias_observations:
        lines.append("_No bias observations recorded this week._")
        return "\n".join(lines)

    for i, b in enumerate(data.bias_observations, start=1):
        scope_bits = [s for s in (b.scope_domain, b.scope_rule_id) if s]
        scope = ", ".join(scope_bits) if scope_bits else "unscoped"
        status = "read" if b.kb_author_read else "UNREAD"
        lines += [
            f"## {i}. {b.bias_type} — {scope} [{status}]",
            "",
            f"- Observed by: {b.observed_by}",
            f"- Observation (mr): {b.observation_mr}",
        ]
        if b.suggested_change_mr:
            lines.append(f"- Suggested change (mr): {b.suggested_change_mr}")
        lines.append("")
    return "\n".join(lines)


async def build_weekly_digest(
    *,
    repo: QaDigestRepo,
    now: datetime | None = None,
    top_fp_rules: int = 10,
) -> WeeklyDigest:
    """Gather the review window and render the agronomist + KB-author documents."""
    week_start_dt, week_end_dt = _review_window(now or now_ist())
    week_start, week_end = week_start_dt.date(), week_end_dt.date()

    data = await repo.gather(week_start, week_end, top_fp_rules=top_fp_rules)
    stamp = week_start.strftime("%Y_%m_%d")

    return WeeklyDigest(
        weekly_report=DigestDoc(
            filename=f"weekly_report_{stamp}.md", content=_render_weekly_report(data)
        ),
        bias_digest=DigestDoc(
            filename=f"bias_digest_{stamp}.md", content=_render_bias_digest(data)
        ),
        data=data,
    )


__all__ = ["DigestDoc", "WeeklyDigest", "build_weekly_digest"]
