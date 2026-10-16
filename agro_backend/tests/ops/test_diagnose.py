"""Unit test for the `make diagnose` report formatter (pure, no DB/network)."""

from __future__ import annotations

from app.domain.diagnostics import CheckResult
from app.ops import diagnose


def test_format_orders_fail_first_and_summarizes() -> None:
    results = [
        CheckResult("a_ok", "freshness", "ok", observed="fresh"),
        CheckResult("b_fail", "invariant", "fail", observed="2", expected="0"),
        CheckResult("c_skip", "dependency", "skip", detail="unset"),
        CheckResult("d_warn", "freshness", "warn", observed="old", expected="<= 6h"),
    ]
    out = diagnose._format(results)
    lines = out.splitlines()

    assert lines[0].startswith("❌") and "b_fail" in lines[0]
    assert "expected 0" in lines[0]  # expected is shown for failures
    assert lines[1].startswith("⚠️")  # warn ranks after fail
    assert "1 ok · 1 warn · 1 fail · 1 skip" in out
