#!/usr/bin/env python3
"""Generate an agronomist review packet for the un-reviewed Ginger KB rules.

The KB has 483 rules but only a fraction carry ``status: AGRONOMIST_REVIEWED``.
This turns "read 439 raw JSON objects" into a prioritised worksheet the panel
can actually work through:

- ``review_tracker.csv`` — one row per un-reviewed rule with the fields a
  reviewer needs, plus blank sign-off columns (``review_outcome``,
  ``reviewer``, ``review_date``, ``review_comment_mr``). Open it in a
  spreadsheet, sort/filter, fill the four columns, then feed it back through
  ``kb_apply_reviews.py`` to fold the sign-offs into the JSON.
- ``review_packet.md`` — the same rules grouped by priority and domain with the
  full English + Marathi text, for reading the content itself.

Priority tiers (highest-risk first):
  P1  executable (has a trigger) AND severity blocking/red — fires now, high
      severity, on un-validated logic.
  P2  executable, severity yellow/info — fires now, lower severity.
  P3  non-executable — advisory/policy/computational, surfaced by context.

Read-only on the KB. Stdlib only, runs from anywhere:
    python build/kb_review_packet.py --dir knowledge_base --out-dir review
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

DOMAIN_FILES = ["Domain1_Rules_Ginger_v2.json"] + [
    f"Domain{i}_Rules_Ginger.json" for i in range(2, 15)
]

REVIEWED = "AGRONOMIST_REVIEWED"
_SEV_RANK = {"blocking": 0, "red": 1, "yellow": 2, "info": 3}

CSV_COLUMNS = [
    "priority",
    "rule_id",
    "domain",
    "category",
    "executable",
    "immutable",
    "severity",
    "status",
    "trigger_en",
    "trigger_expr",
    "action_en",
    "agronomic_basis",
    "yield_impact",
    "confidence",
    "source_tier",
    "recoverability",
    "source_class",
    "references",
    # Sign-off columns the reviewer fills; consumed by kb_apply_reviews.py.
    "review_outcome",  # accepted | revise | rejected
    "reviewer",
    "review_date",  # YYYY-MM-DD
    "review_comment_mr",
]


def _tier(rule: dict[str, Any]) -> str:
    executable = bool(rule.get("trigger", {}).get("expr"))
    severity = rule.get("severity", "info")
    if executable and severity in ("blocking", "red"):
        return "P1"
    if executable:
        return "P2"
    return "P3"


def _row(rule: dict[str, Any], domain: int) -> dict[str, Any]:
    trig = rule.get("trigger", {})
    rz = rule.get("reasoning", {})
    return {
        "priority": _tier(rule),
        "rule_id": rule["rule_id"],
        "domain": f"D{domain:02d}",
        "category": rule.get("category", ""),
        "executable": "yes" if trig.get("expr") else "no",
        "immutable": "yes" if rule.get("immutable") else "no",
        "severity": rule.get("severity", ""),
        "status": rule.get("status", ""),
        "trigger_en": trig.get("english", ""),
        "trigger_expr": trig.get("expr", ""),
        "action_en": rule.get("action", {}).get("english", ""),
        "agronomic_basis": rz.get("agronomic_basis", ""),
        "yield_impact": rz.get("yield_impact", ""),
        "confidence": rz.get("confidence_score", ""),
        "source_tier": rz.get("source_tier", ""),
        "recoverability": rule.get("recoverability", ""),
        "source_class": rule.get("source_class", ""),
        "references": " | ".join(rz.get("references", []) or []),
        "review_outcome": "",
        "reviewer": "",
        "review_date": "",
        "review_comment_mr": "",
    }


def collect(kb_dir: Path) -> list[dict[str, Any]]:
    """Every un-reviewed rule as a flat row, prioritised."""
    rows: list[dict[str, Any]] = []
    for fname in DOMAIN_FILES:
        doc = json.loads((kb_dir / fname).read_text(encoding="utf-8"))
        domain = doc["metadata"]["domain"]
        for rule in doc["rules"]:
            if rule.get("status") == REVIEWED:
                continue
            rows.append(_row(rule, domain))
    rows.sort(
        key=lambda r: (
            r["priority"],
            _SEV_RANK.get(r["severity"], 9),
            r["domain"],
            r["rule_id"],
        )
    )
    return rows


def write_csv(rows: list[dict[str, Any]], out: Path) -> None:
    with out.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _rule_by_id(kb_dir: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for fname in DOMAIN_FILES:
        doc = json.loads((kb_dir / fname).read_text(encoding="utf-8"))
        for rule in doc["rules"]:
            out[rule["rule_id"]] = rule
    return out


def write_markdown(rows: list[dict[str, Any]], kb_dir: Path, out: Path) -> None:
    rules = _rule_by_id(kb_dir)
    tiers = {
        "P1": "P1 — executable & high-severity (fires now, review first)",
        "P2": "P2 — executable, lower severity",
        "P3": "P3 — advisory / policy / computational (surfaced by context)",
    }
    lines: list[str] = [
        "# Ginger KB — Agronomist Review Packet",
        "",
        f"{len(rows)} rules awaiting `AGRONOMIST_REVIEWED`, ordered by review priority. "
        "Record sign-offs in `review_tracker.csv` (the machine-readable half of this "
        "packet) and apply them with `kb_apply_reviews.py`.",
        "",
    ]
    by_tier: dict[str, list[dict[str, Any]]] = {"P1": [], "P2": [], "P3": []}
    for r in rows:
        by_tier[r["priority"]].append(r)
    for tier, heading in tiers.items():
        tier_rows = by_tier[tier]
        if not tier_rows:
            continue
        lines.append(f"## {heading} — {len(tier_rows)} rules")
        lines.append("")
        current_domain = None
        for r in tier_rows:
            if r["domain"] != current_domain:
                current_domain = r["domain"]
                lines.append(f"### {current_domain}")
                lines.append("")
            rule = rules[r["rule_id"]]
            trig = rule.get("trigger", {})
            rz = rule.get("reasoning", {})
            act = rule.get("action", {})
            flags = []
            if r["executable"] == "yes":
                flags.append("executable")
            if r["immutable"] == "yes":
                flags.append("immutable")
            flag_str = f" · _{', '.join(flags)}_" if flags else ""
            lines.append(
                f"**{r['rule_id']}** ({r['category']}, {r['severity']}, "
                f"conf {r['confidence']}, tier {r['source_tier']}){flag_str}"
            )
            lines.append("")
            if trig.get("expr"):
                lines.append(
                    f"- **Trigger:** {trig.get('english', '')}  \n  `{trig['expr']}`"
                )
            else:
                lines.append(f"- **When:** {trig.get('english', '')}")
            lines.append(f"- **Action (EN):** {act.get('english', '')}")
            if act.get("marathi"):
                lines.append(f"- **कृती (MR):** {act['marathi']}")
            lines.append(f"- **Basis:** {rz.get('agronomic_basis', '')}")
            if rz.get("yield_impact"):
                lines.append(f"- **Yield impact:** {rz['yield_impact']}")
            refs = rz.get("references", []) or []
            if refs:
                lines.append(f"- **References:** {'; '.join(refs)}")
            lines.append("")
    out.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="knowledge_base", help="KB JSON directory")
    ap.add_argument("--out-dir", default="review", help="output directory")
    args = ap.parse_args()

    kb_dir = Path(args.dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = collect(kb_dir)
    write_csv(rows, out_dir / "review_tracker.csv")
    write_markdown(rows, kb_dir, out_dir / "review_packet.md")

    tiers = {t: sum(1 for r in rows if r["priority"] == t) for t in ("P1", "P2", "P3")}
    print(f"Un-reviewed rules: {len(rows)}")
    print(f"  P1 (executable, high-severity): {tiers['P1']}")
    print(f"  P2 (executable, lower):         {tiers['P2']}")
    print(f"  P3 (advisory/policy):           {tiers['P3']}")
    print(f"Wrote {out_dir / 'review_tracker.csv'} and {out_dir / 'review_packet.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
