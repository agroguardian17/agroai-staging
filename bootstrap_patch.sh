#!/usr/bin/env bash
# AgroGuardian Round 8 hotfix v2 - robust regex-based patch for the
# _FakeAlertRepo missing-method issue.
#
# The v1 hotfix matched on an exact multi-line anchor string; that
# anchor didn't match your local file (whitespace / one-line differences).
# This version uses a regex that matches the class block regardless of
# the exact contents of create / last_triggered_at / resolve.


set -euo pipefail


echo "==> AgroGuardian Round 8 hotfix v2 starting"


if [ ! -d agro_backend ]; then
  echo "ERROR: run this from the directory that contains agro_backend/." >&2
  exit 1
fi


cd agro_backend


python3 <<'PYEOF'
import re
import sys
from pathlib import Path


target = Path("tests/application/test_ports_are_protocols.py")
if not target.is_file():
    print(f"ERROR: {target} not found", file=sys.stderr)
    sys.exit(2)


src = target.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Is list_for_plot already inside the _FakeAlertRepo class?
# ---------------------------------------------------------------------------
m = re.search(
    r"class\s+_FakeAlertRepo\b[^\n]*:\n(.*?)(?=\n\s*class\s+\w+|\Z)",
    src,
    re.DOTALL,
)
if m is None:
    print("ERROR: could not locate class _FakeAlertRepo in the file.", file=sys.stderr)
    sys.exit(3)


class_body = m.group(1)
if "async def list_for_plot" in class_body:
    print("[OK] _FakeAlertRepo already has list_for_plot - nothing to do.")
    sys.exit(0)


# ---------------------------------------------------------------------------
# Insert list_for_plot at the end of the class body (before the next
# top-level `class` or end-of-file). We trim trailing blank lines from
# class_body and append the new method with the same indentation
# pattern.
# ---------------------------------------------------------------------------
trimmed_body = class_body.rstrip("\n")
addition = (
    "\n"
    "\n"
    "    async def list_for_plot(self, plot_id: str, limit: int = 50) -> list:\n"
    "        return []\n"
)
new_block = "class _FakeAlertRepo" + m.group(0)[len("class _FakeAlertRepo") : m.start(1) - m.start(0)] + trimmed_body + addition


# Reconstruct: everything before the matched block + new_block + everything after.
new_src = src[: m.start()] + new_block + src[m.end() :]


# Sanity: the new file must still parse.
import ast


try:
    ast.parse(new_src)
except SyntaxError as exc:
    print(f"ERROR: patched file does not parse: {exc}", file=sys.stderr)
    sys.exit(4)


target.write_text(new_src, encoding="utf-8")
print("[PATCHED] Added list_for_plot to _FakeAlertRepo")
print(f"   File: {target}")
PYEOF


echo ""
echo "==> Hotfix v2 complete."
echo ""
echo "Verify:"
echo "  pytest tests/application/test_ports_are_protocols.py::test_fake_alert_repo_satisfies_protocol -v"
echo "  pytest tests -v   # expect 352 passed, 1 skipped"
