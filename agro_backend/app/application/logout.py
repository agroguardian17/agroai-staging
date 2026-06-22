"""Use case: revoke a refresh token (a.k.a. log out one device).


The other mode - "log out everywhere" - is exposed through
:meth:`AuthSessionRepo.revoke_all_for_farmer` from the HTTP layer when
the user posts /auth/logout?everywhere=true.
"""


from __future__ import annotations


from dataclasses import dataclass


from app.application.ports.auth_session_repo import AuthSessionRepo
from app.domain.auth import hash_refresh_token




@dataclass(frozen=True, slots=True)
class LogoutDeps:
    session_repo: AuthSessionRepo




async def logout_one(*, refresh_secret: str, deps: LogoutDeps) -> bool:
    """Revoke the session matching ``refresh_secret``.


    Returns True if a session was revoked, False if nothing matched
    (we don't surface this to the client; logout is idempotent).
    """
    token_hash = hash_refresh_token(refresh_secret)
    session = await deps.session_repo.find_by_token_hash(token_hash)
    if session is None:
        return False
    await deps.session_repo.revoke(session.session_id)
    return True




async def logout_everywhere(*, farmer_id: object, deps: LogoutDeps) -> int:
    """Revoke ALL active sessions for a farmer. Returns the count revoked."""
    # ``farmer_id`` is ``uuid.UUID`` at the call sites; typing it as
    # ``object`` here avoids importing uuid into a 30-line module.
    return await deps.session_repo.revoke_all_for_farmer(farmer_id)  # type: ignore[arg-type]




__all__ = ["LogoutDeps", "logout_everywhere", "logout_one"]
