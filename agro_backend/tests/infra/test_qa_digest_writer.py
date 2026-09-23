"""D12 digest filesystem sink."""

from __future__ import annotations

from pathlib import Path

from app.application.build_qa_digest import DigestDoc
from app.infra.qa_digest_writer import write_digest_docs


def test_writes_docs_and_creates_dir(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "qa_digests"
    docs = [
        DigestDoc(filename="weekly_report_2026_06_15.md", content="# report\nहिंदी"),
        DigestDoc(filename="bias_digest_2026_06_15.md", content="# bias"),
    ]
    paths = write_digest_docs(str(out), docs)
    assert [p.name for p in paths] == [
        "weekly_report_2026_06_15.md",
        "bias_digest_2026_06_15.md",
    ]
    assert (out / "weekly_report_2026_06_15.md").read_text(encoding="utf-8") == "# report\nहिंदी"
    assert (out / "bias_digest_2026_06_15.md").read_text(encoding="utf-8") == "# bias"


def test_overwrites_existing_file(tmp_path: Path) -> None:
    write_digest_docs(str(tmp_path), [DigestDoc(filename="x.md", content="v1")])
    write_digest_docs(str(tmp_path), [DigestDoc(filename="x.md", content="v2")])
    assert (tmp_path / "x.md").read_text(encoding="utf-8") == "v2"
