"""Unit tests for the qa_digest scheduler's best-effort FS write (fix A2).

The DB is the durable sink; the filesystem drop must never fail the job when the
dir isn't writable (the PermissionError that broke the Sunday job in prod).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.application.build_qa_digest import DigestDoc
from app.jobs import qa_digest_scheduler as mod


def _docs() -> list[DigestDoc]:
    return [
        DigestDoc(filename="weekly_report_2026_10_12.md", content="# weekly"),
        DigestDoc(filename="bias_digest_2026_10_12.md", content="# bias"),
    ]


def test_best_effort_write_happy_path(tmp_path: Path) -> None:
    paths = mod._best_effort_write(str(tmp_path / "qa"), _docs())
    assert len(paths) == 2
    assert all(Path(p).exists() for p in paths)


def test_best_effort_write_swallows_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(out_dir: str, docs: list[DigestDoc]) -> list[Path]:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(mod, "write_digest_docs", boom)
    # Must return [] and NOT raise (this is the A2 regression).
    assert mod._best_effort_write("/root/not-writable", _docs()) == []
