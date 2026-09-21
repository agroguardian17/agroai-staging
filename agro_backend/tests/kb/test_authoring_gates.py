"""KB authoring-surface quality gates (drift + trigger golden tests).

The ginger knowledge base is authored in ``new-docs/AgroGuardian_Ginger_Engine_v1.0_9931``:
JSON rules, a Python authoring surface (``triggers_wave*.py`` + the engine's
``IMMUTABLE`` / ``PRECEDENCE`` / ``DELIVERY`` structures), and a compiled SQL
build that migration 0010/0018 load into the ``kb_*`` tables.

These gates are the tripwire against *silent desync* between those surfaces:

* **drift check** (``test_runtime_loader.py``) — every trigger expression,
  delivery class, precedence relation and immutable id must match between the
  authoring ``.py`` and the JSON knowledge base. A rule added to the JSON but
  not the code (or vice versa) fails here.
* **trigger golden tests** (``run_d14_trigger_tests.py``) — all 235 rules
  across waves 1-5 must parse, declare their fields, and pass their golden
  tests (587 total).

Both are DB-free: they run against the JSON files and the authoring ``.py``
via the engine's ``JsonSource`` (never ``PostgresSource``), so they need no
Postgres. They are invoked as subprocesses because the authoring package uses
flat imports and is designed to run from its ``knowledge_base`` directory with
``engine/``, ``authoring/`` and ``tests/`` on ``PYTHONPATH``.

If the authoring package is not checked out, the tests skip rather than fail.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PKG = _REPO_ROOT / "new-docs" / "AgroGuardian_Ginger_Engine_v1.0_9931"
_KB_DIR = _PKG / "knowledge_base"

# (runner script under tests/, human label)
_GATES = [
    ("test_runtime_loader.py", "build .py vs KB JSON drift check"),
    ("run_d14_trigger_tests.py", "trigger DSL parse + golden tests (waves 1-5)"),
]

pytestmark = pytest.mark.skipif(
    not _KB_DIR.is_dir(),
    reason="ginger authoring package (new-docs/) not present in this checkout",
)


@pytest.mark.parametrize(("script", "label"), _GATES, ids=[g[0] for g in _GATES])
def test_kb_authoring_gate(script: str, label: str) -> None:
    """Run one authoring-surface gate; fail loudly with its output if it exits non-zero."""
    # Strip pytest-cov's subprocess-coverage handshake vars (COV_CORE_*) and any
    # COVERAGE_* settings before spawning. Otherwise the child auto-starts coverage
    # from the authoring package (cwd, no branch=true) and writes a statement-mode
    # data file that the branch-mode parent cannot combine ("Can't combine statement
    # coverage data with branch data"). The authoring build is not in source=["app"],
    # so there is nothing worth measuring here anyway.
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith("COV_CORE_") and not k.startswith("COVERAGE_")
    }
    env["PYTHONPATH"] = os.pathsep.join(
        [str(_PKG / "engine"), str(_PKG / "authoring"), str(_PKG / "tests")]
    )
    proc = subprocess.run(
        [sys.executable, str(_PKG / "tests" / script)],
        cwd=str(_KB_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        pytest.fail(
            f"KB authoring gate failed: {label} ({script})\n"
            f"--- stdout ---\n{proc.stdout[-4000:]}\n"
            f"--- stderr ---\n{proc.stderr[-2000:]}"
        )
