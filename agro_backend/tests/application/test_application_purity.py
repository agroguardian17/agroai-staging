"""Application layer purity test.


Mirrors ``tests/domain/test_domain_purity.py`` for the application layer.


Per the hexagon (.cursorrules #13): ``app.application.*`` imports domain +
ports + stdlib + typing. It NEVER imports ``app.infra.*`` or any framework
(fastapi, sqlalchemy, anthropic, ...). If a use case "needs" SQL it needs
a port instead.


This test statically AST-scans every Python file under ``app/application/``
and rejects forbidden imports. Adapter implementations live in
``app/infra/`` and the domain in ``app/domain/`` - both are explicitly
allowed prefixes; everything else from the forbidden list is rejected.
"""


from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

# Same forbidden set as the domain purity test, kept in sync intentionally.
# The application layer can import the same things the domain can - i.e.
# stdlib + numpy + shapely - plus the typing module (Protocols), plus
# ``app.domain`` and ``app.application`` itself.
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
    "pydantic",
    "pydantic_settings",
    "structlog",
    "httpx",
    "paho",
    "sentry_sdk",
    "slowapi",
    "passlib",
    "jose",
)


# Specifically forbidden: app.infra.* (the entire adapter layer).
FORBIDDEN_APP_PREFIX = "app.infra"


APPLICATION_DIR = Path(__file__).resolve().parents[2] / "app" / "application"




def _iter_application_files() -> list[Path]:
    return [p for p in APPLICATION_DIR.rglob("*.py") if p.name != "__init__.py"]




@pytest.mark.parametrize(
    "file_path", _iter_application_files() or [pytest.param(None, id="no-files-yet")]
)
def test_application_file_has_no_forbidden_imports(file_path: Path | None) -> None:
    """Static check - application files must not import frameworks or infra."""
    if file_path is None:
        pytest.skip("Application layer empty; first port lands in this round")
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
        f"application layer must stay framework-free (.cursorrules rule #13)"
    )
    assert not module_name.startswith(FORBIDDEN_APP_PREFIX), (
        f"Forbidden infra import '{module_name}' in {source} - "
        f"application layer must call adapters via Protocols, "
        f"never import from app.infra.* (.cursorrules rule #13)"
    )




def test_application_package_imports_at_runtime() -> None:
    """Importing the whole package walk-must succeed standalone."""
    pkg = importlib.import_module("app.application")
    if not hasattr(pkg, "__path__"):
        pytest.skip("app.application is a leaf module")
    for module_info in pkgutil.walk_packages(pkg.__path__, prefix="app.application."):
        importlib.import_module(module_info.name)
