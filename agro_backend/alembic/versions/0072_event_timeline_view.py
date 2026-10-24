"""0072 event_timeline — a read-only union view of every pipeline event (R3.2).

The Round-3 Event Timeline needs "see every event in one place": ingest traces,
device/KB alerts, advisories composed, notifications delivered, job ticks,
diagnostics results, and anomaly findings — in one chronological, filterable
stream. Rather than add an `event_log` table (and a write on every hot path),
this is a ``UNION ALL`` **view** over the durable rows those paths already
write. Pure read, no write overhead, no new ingest coupling; the dashboard
bounds every query by time + limit so the view never does a full scan.

Each branch projects the same shape: ts, event_kind, event_type, level, entity,
summary, source_table, source_id (for drill-in). All non-timestamp columns are
cast to text so the UNION's column types line up.

Revision ID: 0072
Revises: 0071
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0072"
down_revision: str | None = "0071"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE OR REPLACE VIEW event_timeline AS
    -- ingest messages (R3.1 traces)
    SELECT t.created_at AS ts,
           'ingest'::text AS event_kind,
           COALESCE(t.drop_reason, 'ingested')::text AS event_type,
           t.overall::text AS level,
           COALESCE(t.plot_id, t.node_id)::text AS entity,
           ('node ' || COALESCE(t.node_id, '?'))::text AS summary,
           'pipeline_trace'::text AS source_table,
           t.trace_id::text AS source_id
    FROM pipeline_trace t
  UNION ALL
    -- device / KB alerts
    SELECT a.triggered_at,
           'alert'::text,
           a.alert_type::text,
           a.severity::text,
           a.device_id::text,
           left(a.alert_message_marathi, 140)::text,
           'alerts_notifications'::text,
           a.alert_id::text
    FROM alerts_notifications a
  UNION ALL
    -- advisories composed
    SELECT s.generated_at,
           'advisory'::text,
           s.suggestion_type::text,
           (CASE WHEN s.whatsapp_sent THEN 'sent' ELSE 'composed' END)::text,
           s.plot_id::text,
           COALESCE(s.ai_model_version, '')::text,
           'ai_suggestions'::text,
           s.suggestion_id::text
    FROM ai_suggestions s
  UNION ALL
    -- notification deliveries
    SELECT n.dispatched_at,
           'notification'::text,
           n.channel::text,
           n.status::text,
           ('alert ' || n.alert_id)::text,
           COALESCE(n.error_message, n.provider_message_id, '')::text,
           'notification_dispatch_log'::text,
           n.id::text
    FROM notification_dispatch_log n
  UNION ALL
    -- scheduler / job ticks
    SELECT j.started_at,
           'job'::text,
           j.job_name::text,
           j.status::text,
           NULL::text,
           COALESCE(j.error_message, '')::text,
           'job_run'::text,
           j.id::text
    FROM job_run j
  UNION ALL
    -- nightly diagnostics results
    SELECT d.created_at,
           'diagnostic'::text,
           d.check_id::text,
           d.status::text,
           d.category::text,
           COALESCE(d.observed, '')::text,
           'diagnostics_result'::text,
           d.id::text
    FROM diagnostics_result d
  UNION ALL
    -- anomaly findings (R3.4)
    SELECT f.created_at,
           'anomaly'::text,
           f.anomaly_type::text,
           f.severity::text,
           f.entity_id::text,
           COALESCE(f.observed, '')::text,
           'anomaly_finding'::text,
           f.id::text
    FROM anomaly_finding f;
"""

DOWNGRADE_SQL = r"""
DROP VIEW IF EXISTS event_timeline;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
