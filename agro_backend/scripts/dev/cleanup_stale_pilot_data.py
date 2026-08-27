"""Remove stale pilot rows left over from the pre-2-plot scope.

Context
-------
Between 2026-08-05 and 2026-08-26 the pilot was seeded with 4 plots and
2 Sub Nodes. On 2026-08-26 the scope was cut to 2 plots + 1 Sub Node
(see ``seed_pilot.py`` docstring). ``seed_pilot.py`` is idempotent but
not destructive, so any Postgres instance that ran the old seed still
carries rows for ``PLOT_PILOT_003``, ``PLOT_PILOT_004``, and
``AGR-SN-0002``. This script removes them, in an order that respects
foreign-key constraints, inside a single transaction.

Safety
------
* Uses ``IN`` filters on the exact identifiers only — nothing else is
  touched.
* Runs everything in one transaction; if any step fails the whole thing
  rolls back.
* Idempotent: safe to run repeatedly. If the rows are already gone,
  each ``DELETE`` reports 0 rows affected and the script exits 0.
* Read-only preview mode via ``--dry-run``: prints the row counts each
  ``DELETE`` would remove, then rolls back.

Run
---
::

    set -a; source .env; set +a
    export DATABASE_URL_SYNC="postgresql://agro:$POSTGRES_PASSWORD@localhost:5433/agro"
    python scripts/dev/cleanup_stale_pilot_data.py             # apply
    python scripts/dev/cleanup_stale_pilot_data.py --dry-run   # preview only
"""

from __future__ import annotations

import argparse
import os
import sys

from sqlalchemy import Connection, create_engine, text

STALE_PLOT_IDS = ("PLOT_PILOT_003", "PLOT_PILOT_004")
STALE_DEVICE_IDS = ("AGR-SN-0002",)

# (label, table, SQL) — order matters: children before parents.
CLEANUP_STEPS: list[tuple[str, str, str]] = [
    # 1. Anything that references these plots — remove first.
    (
        "ai_suggestions for stale plots",
        "ai_suggestions",
        "DELETE FROM ai_suggestions WHERE plot_id = ANY(:plots)",
    ),
    (
        "alerts_notifications for stale plots",
        "alerts_notifications",
        "DELETE FROM alerts_notifications WHERE plot_id = ANY(:plots)",
    ),
    (
        "node_sensor_readings for stale plots",
        "node_sensor_readings",
        "DELETE FROM node_sensor_readings WHERE plot_id = ANY(:plots)",
    ),
    (
        "crop_seasons for stale plots",
        "crop_seasons",
        "DELETE FROM crop_seasons WHERE plot_id = ANY(:plots)",
    ),
    # 2. Plots themselves.
    (
        "plots (PLOT_PILOT_003, PLOT_PILOT_004)",
        "plots",
        "DELETE FROM plots WHERE plot_id = ANY(:plots)",
    ),
    # 3. Anything that references the stale devices before the device row.
    (
        "node_sensor_readings for stale devices",
        "node_sensor_readings",
        "DELETE FROM node_sensor_readings WHERE node_id = ANY(:devices)",
    ),
    (
        "device_registry (AGR-SN-0002)",
        "device_registry",
        "DELETE FROM device_registry WHERE device_id = ANY(:devices)",
    ),
]


def _table_exists(conn: Connection, table_name: str) -> bool:
    """Return whether a public table exists without aborting the transaction."""
    return bool(
        conn.execute(
            text("SELECT to_regclass(:qualified_table_name) IS NOT NULL"),
            {"qualified_table_name": f"public.{table_name}"},
        ).scalar()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted and roll back.",
    )
    args = parser.parse_args()

    sync_url = os.environ.get("DATABASE_URL_SYNC")
    if not sync_url:
        print(
            "ERROR: DATABASE_URL_SYNC must be set. Example:\n"
            "    set -a; source .env; set +a\n"
            '    export DATABASE_URL_SYNC="postgresql://agro:$POSTGRES_PASSWORD@localhost:5433/agro"',
            file=sys.stderr,
        )
        return 1

    plots_param = list(STALE_PLOT_IDS)
    devices_param = list(STALE_DEVICE_IDS)

    eng = create_engine(sync_url, future=True)
    print()
    print("Cleanup targets:")
    print(f"  plots   : {', '.join(STALE_PLOT_IDS)}")
    print(f"  devices : {', '.join(STALE_DEVICE_IDS)}")
    print(f"  mode    : {'DRY-RUN (rollback)' if args.dry_run else 'APPLY (commit)'}")
    print()

    total_removed = 0
    with eng.connect() as conn:
        transaction = conn.begin()
        try:
            for label, table_name, sql in CLEANUP_STEPS:
                if not _table_exists(conn, table_name):
                    print(f"  skip  {label:<52} (table not present)")
                    continue

                result = conn.execute(
                    text(sql),
                    {"plots": plots_param, "devices": devices_param},
                )
                n = result.rowcount if result.rowcount is not None else 0

                print(f"  {'preview' if args.dry_run else 'deleted'}  {label:<52} rows={n}")
                total_removed += n

            if args.dry_run:
                transaction.rollback()
                print()
                print(f"Dry-run complete — {total_removed} row(s) would have been removed.")
            else:
                transaction.commit()
        except Exception:
            transaction.rollback()
            raise

    if not args.dry_run:
        print()
        print(f"Cleanup complete — {total_removed} row(s) removed.")
        print("Re-run scripts/dev/seed_pilot.py if you want to reseed the 2-plot state.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
