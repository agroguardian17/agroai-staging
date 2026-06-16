"""Alembic-managed migration scripts.

Phase 1 of the roadmap creates the canonical migrations:
  0001_init_21_tables.sql        -- 21 source tables + tenants
  0002_v3_additional_tables.sql  -- 14 v3 additional tables
  0003_extensions.sql            -- uuid-ossp, postgis, vector, pgcrypto
  0004_plots_satellite_only.sql  -- plots.data_tier + trigger
  0005_partition_timeseries.sql  -- monthly range partitioning
  0006_aggregates.sql            -- materialized views
  0007_audit_log.sql             -- audit_trigger_fn + per-table triggers
  0008_rls_policies.sql          -- row-level security
  0009_event_outbox.sql          -- transactional outbox
"""
