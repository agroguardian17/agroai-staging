"""0023 crop_scouting - per-visit field observations (Phase 2.3).

Time-series scouting log the KB's D05 (pest) / D06 (disease) and growth rules
read: pest & disease incidence %, plant/rhizome/stem condition tests, growth
markers, and monitoring actions. One row per scouting visit per plot; the
farm-brain reads the latest row for the plot.

KB-consumed columns are named identically to their kb_farm_brain_fields name so
build_farm_brain copies them by name; enum columns carry a CHECK matching the KB
enum exactly. ``pest_scouting_date`` is DERIVED in the mapper from the latest
row's ``scouting_date`` (not a stored column).

Post-harvest/storage metrics, field history, and D14 task-state fields that also
appeared in the observation bucket are intentionally NOT here - they belong to
later harvest/economics/history units. Reversible, no backfill.

Revision ID: 0023
Revises: 0022
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS crop_scouting (
    scouting_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    tenant_id            UUID        NOT NULL REFERENCES tenants(id),
    farm_id              UUID        NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    plot_id              TEXT        NOT NULL REFERENCES plots(plot_id) ON DELETE CASCADE,
    season_id            UUID        REFERENCES crop_seasons(season_id) ON DELETE SET NULL,

    scouting_date        DATE        NOT NULL,
    scouted_by           TEXT,
    growth_stage_observed TEXT,

    -- KB-consumed observations: names MATCH kb_farm_brain_fields
    emergence_started                BOOLEAN,
    establishment_pct                NUMERIC,
    tillers_per_plant                NUMERIC,
    flowering_observed               BOOLEAN,
    central_shoot_dead               BOOLEAN,
    seed_sprouts_visible             BOOLEAN,
    shoot_borer_incidence_pct        NUMERIC,
    leaf_roller_incidence_pct        NUMERIC,
    rhizome_fly_incidence_pct        NUMERIC,
    white_grub_suspected             BOOLEAN,
    nematode_suspected               BOOLEAN,
    leaf_caterpillar_observed        BOOLEAN,
    light_trap_installed             BOOLEAN,
    light_trap_count_nightly         INTEGER,
    straight_line_holes_in_whorl     BOOLEAN,
    stem_hole_with_webbing           BOOLEAN,
    exposed_rhizomes_observed        BOOLEAN,
    rot_incidence_pct                NUMERIC,
    wilt_incidence_pct               NUMERIC,
    leaf_spot_incidence_pct          NUMERIC,
    wilt_while_green                 BOOLEAN,
    leaf_spot_rings_visible          BOOLEAN,
    ooze_test_result                 TEXT CHECK (ooze_test_result IN ('not_done', 'milky_thread', 'no_thread')),
    rhizome_texture                  TEXT CHECK (rhizome_texture IN ('firm', 'mushy_wet', 'dry_rot')),
    rhizome_smell                    TEXT CHECK (rhizome_smell IN ('normal', 'sour_foul', 'faint')),
    stem_cut_colour                  TEXT CHECK (stem_cut_colour IN ('brown_black', 'greyish_yellow', 'brown_vascular', 'normal')),
    stem_ooze_type                   TEXT CHECK (stem_ooze_type IN ('none', 'watery_foul', 'milky_yellowish')),
    soft_rhizome_found               BOOLEAN,
    plant_pulls_easily               BOOLEAN,
    shoot_pulls_out_easily           BOOLEAN,
    leaf_yellowing_pattern           TEXT CHECK (leaf_yellowing_pattern IN ('uniform_old', 'interveinal_new', 'interveinal_old', 'small_new_leaves', 'margin_scorch', 'with_soft_stem', 'sudden_green_wilt', 'none')),
    skin_scrape_result               TEXT CHECK (skin_scrape_result IN ('not_done', 'peels_easily', 'firmly_attached')),
    sample_dig_120_done              BOOLEAN,
    sample_dig_180_done              BOOLEAN,
    standing_water_hours_observed    NUMERIC,
    harvest_injury_observed          BOOLEAN,
    moisture_pct_final               NUMERIC,

    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS crop_scouting_plot_recent
    ON crop_scouting (plot_id, scouting_date DESC);
"""

DOWNGRADE_SQL = r"""
DROP INDEX IF EXISTS crop_scouting_plot_recent;
DROP TABLE IF EXISTS crop_scouting;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
