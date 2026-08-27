"""Verify the ginger engine's flat imports resolve through our sys.path shim.

The teammate's engine at ``agro_backend/ginger/engine/`` uses flat imports
(``from precedence import Precedence``). Our ``ginger/__init__.py``
inserts ``engine/`` onto sys.path at import time to make those work.

If this test fails, either the shim is broken or someone renamed a module in
their engine. Both are worth surfacing loudly.
"""

from __future__ import annotations


def test_flat_imports_resolve() -> None:
    # Side-effect: puts agro_backend/ginger/engine/ on sys.path.
    # Now the teammate's flat names resolve.
    from expert_override import OverrideStore
    from notification_policy import Notifier
    from persistence import STATE_VERSION, PersistentRunner
    from precedence import Precedence, Relation
    from runner import Runner
    from runtime_loader import (
        JsonSource,
        PostgresSource,
        SqliteSource,
        build_runner,
    )
    from trigger_dsl import parse

    import ginger  # noqa: F401

    # Basic shape sanity — the classes exist and are callable, not just importable.
    assert callable(Runner)
    assert callable(PersistentRunner)
    assert callable(build_runner)
    assert callable(parse)
    assert callable(Notifier)
    assert callable(OverrideStore)
    assert callable(Precedence)
    assert isinstance(STATE_VERSION, int)
    # PostgresSource + SqliteSource + JsonSource each expose ``load()``.
    for cls in (PostgresSource, SqliteSource, JsonSource):
        assert hasattr(cls, "load")
    # Relation exists as a dataclass or namedtuple; construct-shape check.
    assert callable(Relation)
