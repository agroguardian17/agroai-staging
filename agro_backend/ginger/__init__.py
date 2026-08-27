"""AgroGuardian Ginger Advisory Engine — teammate's rule engine (v1.0).

The 7 engine files under ``ginger/engine/`` use *flat* imports throughout —
``from precedence import Precedence``, not ``from .precedence import Precedence``.
That is how the teammate authored them; we do not rewrite their imports because
they are also used verbatim by their own regression suite in ``new-docs/``.

To satisfy those flat imports, this package inserts its ``engine/`` directory
onto ``sys.path`` at import time. Consumers should:

    import ginger  # noqa: F401 - activates the sys.path shim
    from runner import Runner
    from persistence import PersistentRunner
    from runtime_loader import PostgresSource, build_runner

Do NOT import via ``ginger.engine.<mod>`` — that path creates a duplicate module
object under a different sys.modules key, and their internal flat imports would
see a different instance than yours. Always go through flat names.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ENGINE_DIR = str((Path(__file__).parent / "engine").resolve())
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)


__all__: list[str] = []
