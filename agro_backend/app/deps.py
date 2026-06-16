"""Application-wide FastAPI dependencies.

Phase 0 ships only a typed ``get_app_settings`` so other modules don't import
``app.config.get_settings`` directly inside route handlers. The full set of
dependencies (``get_session``, ``get_current_user``, ``require_role``) lands
in Phase 3 alongside auth - the import surface stays the same.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings


def _settings_dep() -> Settings:
    return get_settings()


SettingsDep = Annotated[Settings, Depends(_settings_dep)]


__all__ = ["SettingsDep"]
