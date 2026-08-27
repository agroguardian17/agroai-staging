# Multi-stage Dockerfile for AgroGuardian backend.
# Builds for both linux/amd64 (Lightsail $20 plan today) and linux/arm64 (Graviton tomorrow).
# Use:
#   docker buildx build --platform linux/amd64,linux/arm64 -t agro-backend:dev .

ARG PYTHON_VERSION=3.12.7

# ---------- Stage 1: builder ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Build dependencies for native wheels (rasterio/cryptography/asyncpg etc).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        libgdal-dev \
        gdal-bin \
        libgeos-dev \
        libproj-dev \
        libffi-dev \
        libssl-dev \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install production dependencies into an isolated prefix so the runtime stage stays slim.
COPY pyproject.toml ./
RUN pip install --upgrade pip wheel \
    && pip install --prefix=/install "."

# ---------- Stage 2: runtime ----------
FROM python:${PYTHON_VERSION}-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV=production

# Runtime libs only (no build toolchain).
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgdal32 \
        libgeos-c1v5 \
        libproj25 \
        libssl3 \
        ca-certificates \
        curl \
        tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1000 agro \
    && useradd --system --uid 1000 --gid agro --home-dir /app --shell /usr/sbin/nologin agro

# Copy installed packages from builder.
COPY --from=builder /install /usr/local

WORKDIR /app
COPY --chown=agro:agro app ./app
COPY --chown=agro:agro ginger ./ginger
COPY --chown=agro:agro alembic ./alembic
COPY --chown=agro:agro alembic.ini ./
COPY --chown=agro:agro rules ./rules
# Keep the idempotent pilot seeder available in the staging image.
COPY --chown=agro:agro scripts/dev/seed_pilot.py ./scripts/dev/seed_pilot.py
# Keep the exact pilot-scope cleanup available for VPSes seeded before the
# 2026-08-26 two-plot pilot cutover.
COPY --chown=agro:agro scripts/dev/cleanup_stale_pilot_data.py ./scripts/dev/cleanup_stale_pilot_data.py
COPY --chown=agro:agro pyproject.toml ./

USER agro

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--proxy-headers", \
     "--forwarded-allow-ips", "*"]
