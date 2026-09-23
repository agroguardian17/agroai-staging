"""Filesystem sink for the D12 weekly digests.

v1 emits the two Markdown documents to a directory (``QA_DIGEST_DIR``); email
routing (D12-OI-04) is a later Ops step. The directory is created on demand and
existing files for the same week are overwritten (the digest is regenerable).
"""

from __future__ import annotations

from pathlib import Path

from app.application.build_qa_digest import DigestDoc


def write_digest_docs(out_dir: str, docs: list[DigestDoc]) -> list[Path]:
    """Write each doc under ``out_dir``; return the paths written."""
    base = Path(out_dir)
    base.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for doc in docs:
        path = base / doc.filename
        path.write_text(doc.content, encoding="utf-8")
        written.append(path)
    return written


__all__ = ["write_digest_docs"]
