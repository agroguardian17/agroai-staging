#!/usr/bin/env python3
"""Fold agronomist sign-offs from a completed review tracker into the KB JSON.

Reads a review tracker (``.xlsx`` from the agronomy team, or a ``.csv``) whose
sign-off columns are filled (``review_outcome`` / ``reviewer`` / ``review_date``
/ ``review_comment_mr``) and updates the matching rules in the Domain JSON.

Outcome taxonomy (case-insensitive) and its effect on ``status``:

  COMPLIANT, CONDITIONAL          -> status := AGRONOMIST_REVIEWED (an agronomist
                                     assessed the rule); CONDITIONAL keeps its
                                     condition in the review note for audit +
                                     Season-1 elevation.
  NON_COMPLIANT                   -> review recorded, status UNCHANGED (these are
                                     rewritten separately, see AGRONOMY_COMPLIANCE
                                     §2.2 / the NON_COMPLIANT rewrite migration).
  LEGAL_REVIEW_REQUIRED,          -> review recorded, status UNCHANGED (routed to
  LEGAL_FOOD_SAFETY_REVIEW_...       the legal track).
  accepted / revise / rejected    -> legacy taxonomy, still honoured.

Every processed row writes a ``review`` block {tier, reviewer, date, outcome,
comment_mr} (mirrors the D05-CH-001 convention). ``status`` / ``review`` are
authoring metadata only - json_to_sql.py does not emit them and the drift/golden
gates do not read them - so a sign-off is a pure JSON change with no SQL,
migration or gate impact. Regenerate the SQL afterwards only for tidiness.

Default is a dry run; pass --apply to write. Stdlib only:
    python build/kb_apply_reviews.py --dir knowledge_base --tracker <file.xlsx|.csv> --apply
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

DOMAIN_FILES = ["Domain1_Rules_Ginger_v2.json"] + [
    f"Domain{i}_Rules_Ginger.json" for i in range(2, 15)
]

REVIEWED = "AGRONOMIST_REVIEWED"
# Outcomes that mean an agronomist assessed the rule -> flip status to REVIEWED.
_REVIEWED_OUTCOMES = {"compliant", "conditional", "accepted"}
# Outcomes recorded for the trail but leaving status untouched.
_RECORD_ONLY = {
    "non_compliant",
    "legal_review_required",
    "legal_food_safety_review_required",
    "rejected",
    "revise",
}
_VALID_OUTCOMES = _REVIEWED_OUTCOMES | _RECORD_ONLY
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_EXCEL_EPOCH = datetime.date(1899, 12, 30)  # Excel's day 0 (1900 leap-year bug)
_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


# --- tracker reading (xlsx or csv) -----------------------------------------


def _col_to_idx(ref: str) -> int:
    """Excel cell ref -> 0-based column index ('S19' -> 18)."""
    letters = re.match(r"[A-Z]+", ref)
    n = 0
    for ch in letters.group(0) if letters else "":
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def _read_xlsx(path: Path) -> list[dict[str, str]]:
    """Rows of the first sheet as dicts, keyed by the header row.

    Column-reference-aware so sparse (empty) cells never shift later columns.
    """
    zf = zipfile.ZipFile(path)
    shared: list[str] = []
    if "xl/sharedStrings.xml" in zf.namelist():
        for si in ET.fromstring(zf.read("xl/sharedStrings.xml")).findall(f"{_NS}si"):
            shared.append("".join((t.text or "") for t in si.iter(f"{_NS}t")))
    root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
    grid: list[list[str]] = []
    for row in root.iter(f"{_NS}row"):
        cells: dict[int, str] = {}
        for c in row.findall(f"{_NS}c"):
            idx = _col_to_idx(c.get("r", "A1"))
            kind = c.get("t")
            v = c.find(f"{_NS}v")
            inline = c.find(f"{_NS}is")
            if kind == "s" and v is not None:
                cells[idx] = shared[int(v.text or "0")]
            elif kind == "inlineStr" and inline is not None:
                cells[idx] = "".join((t.text or "") for t in inline.iter(f"{_NS}t"))
            elif v is not None:
                cells[idx] = v.text or ""
            else:
                cells[idx] = ""
        width = (max(cells) + 1) if cells else 0
        grid.append([cells.get(i, "") for i in range(width)])
    if not grid:
        return []
    header = grid[0]
    return [dict(zip(header, r, strict=False)) for r in grid[1:]]


def _read_rows(path: Path) -> list[dict[str, str]]:
    if path.suffix.lower() == ".xlsx":
        return _read_xlsx(path)
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _normalize_date(raw: str) -> str | None:
    """Return an ISO date from an ISO string or an Excel serial, else None."""
    raw = raw.strip()
    if _DATE_RE.match(raw):
        return raw
    if raw.isdigit():
        return (_EXCEL_EPOCH + datetime.timedelta(days=int(raw))).isoformat()
    return None


# --- sign-off extraction + application --------------------------------------


def _read_signoffs(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    filled: list[dict[str, str]] = []
    errors: list[str] = []
    for i, row in enumerate(_read_rows(path), start=2):
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
        date = _normalize_date(row.get("review_date") or "")
        if date is None:
            errors.append(
                f"row {i} ({rid}): review_date '{row.get('review_date')}' unparseable"
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
    rule["review"] = {
        "tier": "T1",
        "reviewer": sign["reviewer"],
        "date": sign["date"],
        "outcome": sign["outcome"],
        "comment_mr": sign["comment_mr"],
    }
    if sign["outcome"] in _REVIEWED_OUTCOMES:
        was = rule.get("status", "")
        rule["status"] = REVIEWED
        return f"{sign['rule_id']}: {was} -> {REVIEWED} ({sign['outcome']}, {sign['reviewer']})"
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
        "--tracker",
        default="review/review_tracker.csv",
        help="completed review tracker (.xlsx or .csv)",
    )
    ap.add_argument(
        "--apply", action="store_true", help="write changes (default: dry run)"
    )
    args = ap.parse_args()

    kb_dir = Path(args.dir)
    docs = _load(kb_dir)
    idx = _index(docs)
    signoffs, errors = _read_signoffs(Path(args.tracker))

    for rid in [s["rule_id"] for s in signoffs if s["rule_id"] not in idx]:
        errors.append(f"unknown rule_id in tracker: {rid}")
    if errors:
        print("VALIDATION FAILED — no changes written:")
        for e in errors[:50]:
            print(f"  - {e}")
        return 1
    if not signoffs:
        print("No filled sign-offs found. Nothing to do.")
        return 0

    changed_files: set[str] = set()
    counts: dict[str, int] = {}
    reviewed = 0
    for sign in signoffs:
        if sign["date"] > datetime.date.today().isoformat():
            print(
                f"VALIDATION FAILED: {sign['rule_id']} review_date {sign['date']} is in the future"
            )
            return 1
        fn, rule = idx[sign["rule_id"]]
        _apply_one(rule, sign)
        changed_files.add(fn)
        counts[sign["outcome"]] = counts.get(sign["outcome"], 0) + 1
        if sign["outcome"] in _REVIEWED_OUTCOMES:
            reviewed += 1

    print(
        f"{len(signoffs)} sign-off(s): {reviewed} -> {REVIEWED}; by outcome: {counts}"
    )
    print(f"{len(changed_files)} file(s) affected.")
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


def _load(kb_dir: Path) -> dict[str, dict[str, Any]]:
    return {
        fn: json.loads((kb_dir / fn).read_text(encoding="utf-8")) for fn in DOMAIN_FILES
    }


def _index(docs: dict[str, dict[str, Any]]) -> dict[str, tuple[str, dict[str, Any]]]:
    idx: dict[str, tuple[str, dict[str, Any]]] = {}
    for fn, doc in docs.items():
        for rule in doc["rules"]:
            idx[rule["rule_id"]] = (fn, rule)
    return idx


if __name__ == "__main__":
    raise SystemExit(main())
