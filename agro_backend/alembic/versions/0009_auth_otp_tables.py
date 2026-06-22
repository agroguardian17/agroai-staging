"""0009 OTP challenges + auth sessions.


Adds two tables that the Round 8 auth flow needs:


* ``otp_challenges`` - one row per OTP request. Stores a SALTED HASH of the
  6-digit code (never the code itself), an expiry, and an attempt counter
  so /auth/verify_otp can rate-limit brute-force guesses.
* ``auth_sessions`` - one row per active refresh token, keyed by a SHA-256
  hash of the random refresh secret. Setting ``revoked_at`` invalidates
  the token without rotating signing keys. Doubles as a session list for
  the "your devices" feature in Phase 4.


Indexes:
* (phone, expires_at DESC) on otp_challenges for the "find latest active
  challenge for this phone" lookup that send_otp's rate-limit and
  verify_otp's match both perform.
* UNIQUE(refresh_token_hash) on auth_sessions so a lookup by token is
  index-only and rotation is just one DELETE + INSERT.


The tables don't carry RLS policies in Phase 2 because they're system-
level (the auth service, not farmers, owns them). Phase 4 may add tenant
scoping if we land multi-tenant control planes.


Revision ID: 0009
Revises: 0008
Create Date: Phase 3, Round 8
"""


from __future__ import annotations


from collections.abc import Sequence


from alembic import op


revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None




UPGRADE_SQL = r"""
-- ---------------------------------------------------------------------------
-- otp_challenges
-- ---------------------------------------------------------------------------
CREATE TABLE otp_challenges (
    challenge_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id),
    phone            TEXT NOT NULL,
    code_hash        TEXT NOT NULL,
    transport        TEXT NOT NULL CHECK (transport IN ('whatsapp','sms','log_only')),
    expires_at       TIMESTAMPTZ NOT NULL,
    consumed_at      TIMESTAMPTZ,
    attempt_count    INT NOT NULL DEFAULT 0,
    max_attempts     INT NOT NULL DEFAULT 5,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    ip_address       INET,
    user_agent       TEXT
);


CREATE INDEX otp_challenges_phone_expiry_idx
    ON otp_challenges (phone, expires_at DESC);


CREATE INDEX otp_challenges_phone_unconsumed_idx
    ON otp_challenges (phone, expires_at DESC)
    WHERE consumed_at IS NULL;


-- ---------------------------------------------------------------------------
-- auth_sessions
-- ---------------------------------------------------------------------------
CREATE TABLE auth_sessions (
    session_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID NOT NULL REFERENCES tenants(id),
    farmer_id            UUID NOT NULL REFERENCES farmers(farmer_id),
    refresh_token_hash   TEXT NOT NULL UNIQUE,
    expires_at           TIMESTAMPTZ NOT NULL,
    revoked_at           TIMESTAMPTZ,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_agent           TEXT,
    ip_address           INET
);


CREATE INDEX auth_sessions_farmer_active_idx
    ON auth_sessions (farmer_id, expires_at DESC)
    WHERE revoked_at IS NULL;
"""




DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS auth_sessions;
DROP TABLE IF EXISTS otp_challenges;
"""




def upgrade() -> None:
    op.execute(UPGRADE_SQL)




def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
