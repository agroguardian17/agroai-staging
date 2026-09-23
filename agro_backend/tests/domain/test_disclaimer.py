"""Mandatory advisory disclaimer (LEGAL_COMPLIANCE_CERTIFICATE §7.2)."""

from __future__ import annotations

from app.domain.disclaimer import DISCLAIMER_MR, append_disclaimer


def test_disclaimer_verbatim_key_phrases() -> None:
    # Guard the verbatim text against accidental edits (it is legally load-bearing).
    assert "CIB&RC-प्रमाणित लेबल-सूचना" in DISCLAIMER_MR
    assert "VIRAAI हा सल्ला विशिष्ट उत्पन्नाची किंवा परिणामाची हमी देत नाही." in DISCLAIMER_MR
    assert "PPE वापरावेत." in DISCLAIMER_MR


def test_append_adds_disclaimer() -> None:
    out = append_disclaimer("पाणी द्या.")
    assert out.startswith("पाणी द्या.")
    assert DISCLAIMER_MR in out


def test_append_is_idempotent() -> None:
    once = append_disclaimer("पाणी द्या.")
    twice = append_disclaimer(once)
    assert once == twice
    assert twice.count(DISCLAIMER_MR) == 1


def test_append_to_empty_returns_disclaimer_only() -> None:
    assert append_disclaimer("") == DISCLAIMER_MR
    assert append_disclaimer("   ") == DISCLAIMER_MR
