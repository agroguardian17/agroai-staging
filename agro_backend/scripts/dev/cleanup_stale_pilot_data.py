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
from dataclasses import dataclass

from sqlalchemy import Connection, create_engine, text

STALE_PLOT_IDS = ("PLOT_PILOT_003", "PLOT_PILOT_004")
STALE_DEVICE_IDS = ("AGR-SN-0002",)


@dataclass(frozen=True)
class CleanupStep:
    """One guarded delete in the stale-pilot cleanup plan."""

    label: str
    tables: tuple[str, ...]
    required_columns: dict[str, tuple[str, ...]]
    sql: str


# Order matters: children before parents.
CLEANUP_STEPS: list[CleanupStep] = [
    # 1. Anything that references these plots — remove first.
    CleanupStep(
        label="ai_suggestions for stale plots",
        tables=("ai_suggestions",),
        required_columns={"ai_suggestions": ("plot_id",)},
        sql="DELETE FROM ai_suggestions WHERE plot_id = ANY(:plots)",
    ),
    CleanupStep(
        label="notification_dispatch_log for stale-device alerts",
        tables=("notification_dispatch_log", "alerts_notifications"),
        required_columns={
            "notification_dispatch_log": ("alert_id",),
            "alerts_notifications": ("alert_id", "device_id"),
        },
        sql=(
            "DELETE FROM notification_dispatch_log "
            "WHERE alert_id IN ("
            "SELECT alert_id FROM alerts_notifications WHERE device_id = ANY(:devices)"
            ")"
        ),
    ),
    CleanupStep(
        label="notification_dlq for stale-device alerts",
        tables=("notification_dlq", "alerts_notifications"),
        required_columns={
            "notification_dlq": ("alert_id",),
            "alerts_notifications": ("alert_id", "device_id"),
        },
        sql=(
            "DELETE FROM notification_dlq "
            "WHERE alert_id IN ("
            "SELECT alert_id FROM alerts_notifications WHERE device_id = ANY(:devices)"
            ")"
        ),
    ),
    CleanupStep(
        label="alerts_notifications for stale devices",
        tables=("alerts_notifications",),
        required_columns={"alerts_notifications": ("device_id",)},
        sql="DELETE FROM alerts_notifications WHERE device_id = ANY(:devices)",
    ),
    CleanupStep(
        label="node_sensor_readings for stale plots",
        tables=("node_sensor_readings",),
        required_columns={"node_sensor_readings": ("plot_id",)},
        sql="DELETE FROM node_sensor_readings WHERE plot_id = ANY(:plots)",
    ),
    CleanupStep(
        label="crop_seasons for stale plots",
        tables=("crop_seasons",),
        required_columns={"crop_seasons": ("plot_id",)},
        sql="DELETE FROM crop_seasons WHERE plot_id = ANY(:plots)",
    ),
    # 2. Plots themselves.
    CleanupStep(
        label="plots (PLOT_PILOT_003, PLOT_PILOT_004)",
        tables=("plots",),
        required_columns={"plots": ("plot_id",)},
        sql="DELETE FROM plots WHERE plot_id = ANY(:plots)",
    ),
    # 3. Anything that references the stale devices before the device row.
    CleanupStep(
        label="node_sensor_readings for stale devices",
        tables=("node_sensor_readings",),
        required_columns={"node_sensor_readings": ("node_id",)},
        sql="DELETE FROM node_sensor_readings WHERE node_id = ANY(:devices)",
    ),
    CleanupStep(
        label="device_registry (AGR-SN-0002)",
        tables=("device_registry",),
        required_columns={"device_registry": ("device_id",)},
        sql="DELETE FROM device_registry WHERE device_id = ANY(:devices)",
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


def _column_exists(conn: Connection, table_name: str, column_name: str) -> bool:
    """Return whether a public table column exists without aborting the transaction."""
    return bool(
        conn.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = :table_name
                      AND column_name = :column_name
                )
                """
            ),
            {"table_name": table_name, "column_name": column_name},
        ).scalar()
    )


def _skip_reason(conn: Connection, step: CleanupStep) -> str | None:
    """Return why a cleanup step cannot run on this DB shape, or None."""
    for table_name in step.tables:
        if not _table_exists(conn, table_name):
            return f"table not present: {table_name}"

    for table_name, column_names in step.required_columns.items():
        for column_name in column_names:
            if not _column_exists(conn, table_name, column_name):
                return f"column not present: {table_name}.{column_name}"

    return None


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
            for step in CLEANUP_STEPS:
                skip_reason = _skip_reason(conn, step)
                if skip_reason is not None:
                    print(f"  skip  {step.label:<52} ({skip_reason})")
                    continue

                result = conn.execute(
                    text(step.sql),
                    {"plots": plots_param, "devices": devices_param},
                )
                n = result.rowcount if result.rowcount is not None else 0

                print(f"  {'preview' if args.dry_run else 'deleted'}  {step.label:<52} rows={n}")
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
