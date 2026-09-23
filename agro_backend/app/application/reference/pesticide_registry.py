"""Ginger pesticide registry — the source of truth for PHI + the blocklist gate.

Loads ``ginger_pesticide_registry.csv`` (agronomy-team deliverable, VNMKV-aligned)
into the two structures the farm-brain mapper reads:

* ``PHI_DAYS_BY_GROUP`` — pesticide group (lower-cased) -> pre-harvest interval
  in days. Registered chemicals carry their label PHI; biologicals carry 0.
  Blocklisted molecules are excluded (they have no valid PHI).
* ``CROP_INPUT_BLOCKLIST`` — group (lower-cased) -> {reason, source_ref} for
  every molecule banned / not registered on ginger. A recorded spray on this
  list forces ``phi_blocklist_hit`` and refuses a PHI number (see D05-CH-008).

A PHI cell may be a single value, a range, or annotated (``"15-21"``,
``"30-40"``, ``"30+ (pre-plant only)"``); we take the largest integer so the
default errs long (more restrictive = food-safe). A group not in the registry
falls through to the mapper's conservative default, so this never loosens a PHI.

Reading a bundled static reference file with stdlib ``csv`` keeps the mapper in
the application layer (no framework, no DB). If the file is missing or malformed
the module falls back to a minimal safe set so the blocklist gate still fires on
the historically-known bans rather than failing open.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

_CSV_PATH = Path(__file__).with_name("ginger_pesticide_registry.csv")

# Failsafe if the CSV cannot be read: the molecules that were hard-coded before
# the registry landed. Better to keep blocking these than to fail open.
_FALLBACK_BLOCKLIST: dict[str, dict[str, str]] = {
    "chlorpyriphos": {
        "reason": "Not registered on ginger; blocked by D05-CH-001.",
        "source_ref": "CIB&RC label / FSSAI MRL",
    },
}


def parse_phi_days(raw: str | None) -> int | None:
    """Largest integer in a PHI cell, or None when the cell has no number.

    ``"15-21" -> 21``, ``"30-40" -> 40``, ``"30+ (pre-plant only)" -> 30``,
    ``"0" -> 0``, ``"" / None -> None``.
    """
    if not raw:
        return None
    nums = [int(n) for n in re.findall(r"\d+", raw)]
    return max(nums) if nums else None


def load_registry(
    path: Path = _CSV_PATH,
) -> tuple[dict[str, int], dict[str, dict[str, str]]]:
    """Return (PHI_DAYS_BY_GROUP, CROP_INPUT_BLOCKLIST) parsed from the CSV.

    Group keys are lower-cased for case-insensitive matching. A row with a
    non-empty ``blocklist_reason_if_any`` is a blocklist entry (no PHI); every
    other row contributes its parsed PHI (biologicals = 0).
    """
    phi_by_group: dict[str, int] = {}
    blocklist: dict[str, dict[str, str]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            group = (row.get("group") or "").strip().lower()
            if not group:
                continue
            reason = (row.get("blocklist_reason_if_any") or "").strip()
            if reason:
                blocklist[group] = {
                    "reason": reason,
                    "source_ref": (row.get("source_ref") or "").strip(),
                }
                continue
            phi = parse_phi_days(row.get("phi_days"))
            if phi is not None:
                phi_by_group[group] = phi
    return phi_by_group, blocklist


try:
    PHI_DAYS_BY_GROUP, CROP_INPUT_BLOCKLIST = load_registry()
    if not CROP_INPUT_BLOCKLIST:  # empty parse == treat as failure, don't fail open
        raise ValueError("registry produced an empty blocklist")
except (OSError, ValueError, KeyError):  # pragma: no cover - defensive fallback
    PHI_DAYS_BY_GROUP = {}
    CROP_INPUT_BLOCKLIST = dict(_FALLBACK_BLOCKLIST)


__all__ = ["CROP_INPUT_BLOCKLIST", "PHI_DAYS_BY_GROUP", "load_registry", "parse_phi_days"]
