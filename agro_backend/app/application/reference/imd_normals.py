"""IMD 1991-2020 rainfall normals — the source of truth for rainfall deviation.

Loads ``imd_district_normals_1991_2020.csv`` (agronomy-team deliverable) into
``STATION_RAINFALL_NORMAL``, keyed by a short station slug, which the farm-brain
mapper reads to compute season-to-date rainfall deviation vs the plot's station.

Key = the parenthetical in ``station_name`` when present, else the name slugged,
so "Aurangabad (Chikalthana)" -> ``chikalthana`` (the anchor the interim
``_ZONE_TO_STATION`` map points at). Each value keeps the full metadata block
(source, station name, period, method, scope, verification_status) - per the
README these must never be stripped. Chikalthana is CONFIRMED; the other 10
stations are PROVISIONAL (monthly distribution proportioned) until IMD Pune
per-station monthlies are fetched.

Stdlib ``csv`` only (application layer, no framework, no DB). If the file is
missing/malformed it falls back to the confirmed Chikalthana anchor so pilot
rainfall deviation still works rather than failing open.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

_CSV_PATH = Path(__file__).with_name("imd_district_normals_1991_2020.csv")

_MONTHS = (
    "jan_mm",
    "feb_mm",
    "mar_mm",
    "apr_mm",
    "may_mm",
    "jun_mm",
    "jul_mm",
    "aug_mm",
    "sep_mm",
    "oct_mm",
    "nov_mm",
    "dec_mm",
)

# Confirmed anchor (AG-V2.0 §4); the failsafe if the CSV cannot be read.
_FALLBACK: dict[str, dict[str, Any]] = {
    "chikalthana": {
        "monthly_mm": [2.6, 2.2, 11.4, 6.0, 17.4, 155.6, 178.0, 171.5, 172.4, 68.2, 17.5, 8.9],
        "annual_mm": 811.7,
        "source_institution": "IMD",
        "station_name": "Aurangabad (Chikalthana)",
        "normal_period": "1991-2020",
        "geographical_scope": "station",
    },
}


def station_key(station_name: str) -> str:
    """Short slug for a station: the parenthetical if present, else the name.

    "Aurangabad (Chikalthana)" -> "chikalthana"; "Jalna" -> "jalna".
    """
    match = re.search(r"\(([^)]+)\)", station_name)
    base = match.group(1) if match else station_name
    return re.sub(r"[^a-z0-9]+", "_", base.strip().lower()).strip("_")


def load_normals(path: Path = _CSV_PATH) -> dict[str, dict[str, Any]]:
    """Parse the CSV into {station_key: {monthly_mm, annual_mm, ...metadata}}."""
    out: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            name = (row.get("station_name") or "").strip()
            if not name:
                continue
            out[station_key(name)] = {
                "monthly_mm": [float(row[m]) for m in _MONTHS],
                "annual_mm": float(row["annual_mm"]),
                "source_institution": (row.get("source_institution") or "").strip(),
                "station_name": name,
                "district": (row.get("district") or "").strip(),
                "normal_period": (row.get("normal_period") or "").strip(),
                "measurement_method": (row.get("measurement_method") or "").strip(),
                "geographical_scope": (row.get("geographical_scope") or "").strip(),
                "verification_status": (row.get("verification_status") or "").strip(),
            }
    return out


try:
    STATION_RAINFALL_NORMAL = load_normals()
    if "chikalthana" not in STATION_RAINFALL_NORMAL:  # anchor missing == treat as failure
        raise ValueError("IMD normals missing the Chikalthana anchor")
except (OSError, ValueError, KeyError):  # pragma: no cover - defensive fallback
    STATION_RAINFALL_NORMAL = dict(_FALLBACK)


__all__ = ["STATION_RAINFALL_NORMAL", "load_normals", "station_key"]
