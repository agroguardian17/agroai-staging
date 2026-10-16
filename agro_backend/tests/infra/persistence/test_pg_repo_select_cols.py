"""Static guard across every Pg*Repo: _row_to_* reads only selected columns.

Generalises the single-repo guard that caught the ``k_source`` outage to every
persistence module using the ``_SELECT_COLS = (...)`` + ``r.<col>`` pattern. A
column read by ``_row_to_view`` but missing from ``_SELECT_COLS`` raises
``NoSuchColumnError`` at runtime and takes down every job built on that repo —
this fails fast at collection time instead. No database needed: it parses source.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import app.infra.persistence as _persistence

_PERSIST_DIR = Path(_persistence.__file__).parent
_SELECT_RE = re.compile(r"_SELECT_COLS\s*=\s*\((.*?)\)\n", re.S)


def _modules_with_select() -> list[Path]:
    return [
        p
        for p in sorted(_PERSIST_DIR.glob("pg_*.py"))
        if _SELECT_RE.search(p.read_text(encoding="utf-8"))
    ]


def _missing_columns(path: Path) -> list[str]:
    src = path.read_text(encoding="utf-8")
    match = _SELECT_RE.search(src)
    assert match, f"{path.name}: _SELECT_COLS not found"
    selected = set(re.findall(r"[a-z_][a-z0-9_]+", match.group(1).replace('"', " ")))
    reads = set(re.findall(r"\br\.([a-z_][a-z0-9_]+)", src))
    return sorted(col for col in reads if col not in selected)


@pytest.mark.parametrize("path", _modules_with_select(), ids=lambda p: p.name)
def test_select_cols_covers_every_row_read(path: Path) -> None:
    missing = _missing_columns(path)
    assert not missing, (
        f"{path.name}: _row_to_* reads columns not in _SELECT_COLS: {missing}. "
        "Add them to _SELECT_COLS (this is the k_source-class guard)."
    )
