#!/usr/bin/env python3
"""Fold agronomist sign-offs from a filled review tracker back into the KB JSON.

Reads a ``review_tracker.csv`` that reviewers have filled (the four sign-off
columns ``review_outcome`` / ``reviewer`` / ``review_date`` /
``review_comment_mr``) and updates the matching rules in the Domain JSON:

  review_outcome = accepted  -> status := AGRONOMIST_REVIEWED, and a ``review``
                                block {tier, reviewer, date, outcome, comment_mr}
                                is written (mirrors the existing convention, e.g.
                                D05-CH-001).
  review_outcome = revise    -> the ``review`` block is written with that outcome
     or rejected                for the record; status is left unchanged so the
                                rule stays out of the reviewed set.

``status`` / ``review`` are authoring metadata only — json_to_sql.py does not
emit them and the drift/golden gates do not read them — so a sign-off is a pure
JSON change with no SQL, migration or gate impact. Regenerate the SQL afterwards
only for tidiness.

Default is a dry run; pass --apply to write. Stdlib only:
    python build/kb_apply_reviews.py --dir knowledge_base --csv review/review_tracker.csv --apply
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
from pathlib import Path
from typing import Any

DOMAIN_FILES = ["Domain1_Rules_Ginger_v2.json"] + [
    f"Domain{i}_Rules_Ginger.json" for i in range(2, 15)
]

REVIEWED = "AGRONOMIST_REVIEWED"
_VALID_OUTCOMES = {"accepted", "revise", "rejected"}
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load(kb_dir: Path) -> dict[str, dict[str, Any]]:
    """Map each Domain file name to its parsed document."""
    return {
        fn: json.loads((kb_dir / fn).read_text(encoding="utf-8")) for fn in DOMAIN_FILES
    }


def _index(docs: dict[str, dict[str, Any]]) -> dict[str, tuple[str, dict[str, Any]]]:
    idx: dict[str, tuple[str, dict[str, Any]]] = {}
    for fn, doc in docs.items():
        for rule in doc["rules"]:
            idx[rule["rule_id"]] = (fn, rule)
    return idx


def _read_signoffs(csv_path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """Filled rows (those with an outcome) and a list of validation errors."""
    filled: list[dict[str, str]] = []
    errors: list[str] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            outcome = (row.get("review_outcome") or "").strip().lower()
            if not outcome:
                continue
            rid = (row.get("rule_id") or "").strip()
            if outcome not in _VALID_OUTCOMES:
                errors.append(
                    f"row {i} ({rid}): outcome '{outcome}' not in {sorted(_VALID_OUTCOMES)}"
                )
                continue
            if not (row.get("reviewer") or "").strip():
                errors.append(f"row {i} ({rid}): reviewer is required for a sign-off")
                continue
            date = (row.get("review_date") or "").strip()
            if not _DATE_RE.match(date):
                errors.append(
                    f"row {i} ({rid}): review_date '{date}' must be YYYY-MM-DD"
                )
                continue
            filled.append(
                {
                    "rule_id": rid,
                    "outcome": outcome,
                    "reviewer": row["reviewer"].strip(),
                    "date": date,
                    "comment_mr": (row.get("review_comment_mr") or "").strip(),
                }
            )
    return filled, errors


def _apply_one(rule: dict[str, Any], sign: dict[str, str]) -> str:
    """Mutate a rule with one sign-off; return a one-line description."""
    rule["review"] = {
        "tier": "T1",
        "reviewer": sign["reviewer"],
        "date": sign["date"],
        "outcome": sign["outcome"],
        "comment_mr": sign["comment_mr"],
    }
    if sign["outcome"] == "accepted":
        was = rule.get("status", "")
        rule["status"] = REVIEWED
        return f"{sign['rule_id']}: {was} -> {REVIEWED} (reviewer {sign['reviewer']})"
    return (
        f"{sign['rule_id']}: review recorded as '{sign['outcome']}' (status unchanged)"
    )


def _dump(doc: dict[str, Any], path: Path) -> None:
    path.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", default="knowledge_base", help="KB JSON directory")
    ap.add_argument(
        "--csv", default="review/review_tracker.csv", help="filled review tracker"
    )
    ap.add_argument(
        "--apply", action="store_true", help="write changes (default: dry run)"
    )
    args = ap.parse_args()

    kb_dir = Path(args.dir)
    docs = _load(kb_dir)
    idx = _index(docs)
    signoffs, errors = _read_signoffs(Path(args.csv))

    unknown = [s["rule_id"] for s in signoffs if s["rule_id"] not in idx]
    for rid in unknown:
        errors.append(f"unknown rule_id in CSV: {rid}")
    if errors:
        print("VALIDATION FAILED — no changes written:")
        for e in errors:
            print(f"  - {e}")
        return 1

    if not signoffs:
        print(
            "No filled sign-offs found (review_outcome is blank on every row). Nothing to do."
        )
        return 0

    changed_files: set[str] = set()
    accepted = 0
    for sign in signoffs:
        fn, rule = idx[sign["rule_id"]]
        # Guard against a future date typo.
        if sign["date"] > datetime.date.today().isoformat():
            print(
                f"VALIDATION FAILED: {sign['rule_id']} review_date {sign['date']} is in the future"
            )
            return 1
        print("  " + _apply_one(rule, sign))
        changed_files.add(fn)
        if sign["outcome"] == "accepted":
            accepted += 1

    print(
        f"\n{len(signoffs)} sign-off(s): {accepted} accepted -> {REVIEWED}, "
        f"{len(signoffs) - accepted} recorded; {len(changed_files)} file(s) affected."
    )
    if not args.apply:
        print(
            "Dry run — pass --apply to write. Then regenerate the SQL (json_to_sql.py)."
        )
        return 0
    for fn in sorted(changed_files):
        _dump(docs[fn], kb_dir / fn)
    print(
        f"Wrote {len(changed_files)} file(s). Regenerate the SQL next (json_to_sql.py)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
