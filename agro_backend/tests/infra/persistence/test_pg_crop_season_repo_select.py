"""Static consistency guard for PgCropSeasonRepo.

``_row_to_view`` reads ``r.<col>`` for every CropSeasonView field, but those
columns only exist on the row if ``_SELECT_COLS`` selected them. A field read
but not selected raises ``NoSuchColumnError`` at runtime and takes down every
job built on crop_seasons (ginger daily, satellite, landsat, forecast). This
test fails fast at import time instead — it caught the missing ``k_source``.

No database needed: it parses the module source.
"""

from __future__ import annotations

import re
from pathlib import Path

import app.infra.persistence.pg_crop_season_repo as mod


def test_select_cols_covers_every_row_to_view_read() -> None:
    src = Path(mod.__file__).read_text(encoding="utf-8")

    sel_blob = re.search(r"_SELECT_COLS = \((.*?)\)\n", src, re.S)
    assert sel_blob, "could not locate _SELECT_COLS"
    selected = set(re.findall(r"[a-z_][a-z0-9_]+", sel_blob.group(1).replace('"', " ")))

    reads = set(re.findall(r"\br\.([a-z_][a-z0-9_]+)", src))

    missing = sorted(c for c in reads if c not in selected)
    assert not missing, f"_row_to_view reads columns not in _SELECT_COLS: {missing}"
