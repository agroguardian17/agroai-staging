"""Adapters that bridge the ginger engine to our infrastructure.

The teammate's engine lives at ``agro_backend/ginger/`` and is designed to be
storage-agnostic. This package holds our Postgres-backed implementations of
their storage interfaces so they persist to the same database as everything
else in the pilot.
"""
