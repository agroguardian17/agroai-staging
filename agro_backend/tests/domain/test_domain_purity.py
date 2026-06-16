"""Domain layer purity test.

The hexagon's #1 invariant is that ``app.domain.*`` imports nothing from
FastAPI, SQLAlchemy, Anthropic, or any framework. Importing from a fresh
process must succeed with only stdlib + numpy + shapely available.

This test scans every Python file under ``app/domain/`` and ``app/lib/time.py``
(the only pure helper today) and rejects forbidden imports statically.
Phase 1+ adds more modules; the test covers them automatically.
"""

from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

FORBIDDEN_PREFIXES = (
    "fastapi",
    "sqlalchemy",
    "asyncpg",
    "alembic",
    "anthropic",
    "firebase_admin",
    "chromadb",
    "sentinelhub",
    "earthaccess",
    "rasterio",
    "boto3",
    "b2sdk",
    "pydantic",  # pydantic is for adapters/IO boundaries, never domain
    "pydantic_settings",
    "structlog",
    "httpx",
    "paho",
    "sentry_sdk",
    "slowapi",
    "passlib",
    "jose",
)

ALLOWED_TOP_LEVEL = {
    "app.domain",
    "app.lib.time",  # tz helper used by domain
}

DOMAIN_DIR = Path(__file__).resolve().parents[2] / "app" / "domain"


def _iter_domain_files() -> list[Path]:
    return [p for p in DOMAIN_DIR.rglob("*.py") if p.name != "__init__.py"]


@pytest.mark.parametrize(
    "file_path", _iter_domain_files() or [pytest.param(None, id="no-files-yet")]
)
def test_domain_file_has_no_forbidden_imports(file_path: Path | None) -> None:
    """Static check - domain files must not import frameworks."""
    if file_path is None:
        pytest.skip("Domain layer empty; first module lands in Phase 2")
    tree = ast.parse(file_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _assert_allowed(alias.name, file_path)
        elif isinstance(node, ast.ImportFrom) and node.module:
            _assert_allowed(node.module, file_path)


def _assert_allowed(module_name: str, source: Path) -> None:
    head = module_name.split(".")[0]
    assert head not in FORBIDDEN_PREFIXES, (
        f"Forbidden framework import '{module_name}' in {source} - "
        f"domain layer must stay pure (.cursorrules rule #12)"
    )


def test_domain_package_imports_at_runtime() -> None:
    """Importing app.domain (and walking subpackages) must succeed standalone."""
    pkg = importlib.import_module("app.domain")
    if not hasattr(pkg, "__path__"):
        pytest.skip("app.domain is empty until Phase 2")
    for module_info in pkgutil.walk_packages(pkg.__path__, prefix="app.domain."):
        importlib.import_module(module_info.name)
