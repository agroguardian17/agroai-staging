# AgroGuardian Makefile.
#
# Works on Linux/macOS natively, and on Windows via:
#   - Git Bash (recommended)  -- `make` is on PATH if you `choco install make`
#   - WSL                     -- transparent
#   - Native PowerShell       -- use `pwsh -File scripts/dev/render-caddyfile.ps1` directly
#
# Everything runs from `agro_backend/`.

PYTHON ?= python
COMPOSE_DEV = docker compose -f docker-compose.dev.yml
COMPOSE_PROD = docker compose -f docker-compose.prod.yml
CADDY_TEMPLATE = deploy/caddy/Caddyfile
CADDY_PROD = deploy/caddy/Caddyfile.prod

.PHONY: help install lint format typecheck test test-cov \
        up up-deps down logs build build-multiarch \
        migrate migrate-down migrate-new \
        caddyfile-prod clean

help:
	@echo "AgroGuardian backend - common targets:"
	@echo ""
	@echo "  install            Create venv + install dev deps"
	@echo "  lint               ruff check + ruff format --check"
	@echo "  format             ruff format (auto-fix)"
	@echo "  typecheck          mypy app/"
	@echo "  test               pytest -q"
	@echo "  test-cov           pytest with coverage gate"
	@echo ""
	@echo "  up                 docker compose up -d (dev stack)"
	@echo "  up-deps            postgres + mosquitto + chroma only"
	@echo "  down               docker compose down"
	@echo "  logs               tail app logs"
	@echo "  build              build the dev image"
	@echo "  build-multiarch    buildx build amd64+arm64 (CI)"
	@echo ""
	@echo "  migrate            alembic upgrade head"
	@echo "  migrate-down       alembic downgrade base"
	@echo "  migrate-new m=name alembic revision -m \"name\""
	@echo ""
	@echo "  caddyfile-prod IP=<ip>     Render Caddyfile for sslip.io"
	@echo "  caddyfile-prod DOMAIN=<d>  Render Caddyfile for real domain"

install:
	$(PYTHON) -m venv .venv
	.venv/bin/pip install --upgrade pip wheel
	.venv/bin/pip install -e ".[dev]"

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check . --fix

typecheck:
	mypy app/

test:
	pytest -q

test-cov:
	pytest -q --cov=app --cov-report=term-missing --cov-fail-under=80

up:
	$(COMPOSE_DEV) up -d --build

up-deps:
	$(COMPOSE_DEV) up -d postgres mosquitto chroma

down:
	$(COMPOSE_DEV) down

logs:
	$(COMPOSE_DEV) logs -f app

build:
	$(COMPOSE_DEV) build app

build-multiarch:
	docker buildx build --platform linux/amd64,linux/arm64 -t agro-backend:multi .

migrate:
	alembic upgrade head

migrate-down:
	alembic downgrade base

migrate-new:
	alembic revision -m "$(m)"

# ----- Caddyfile rendering -----------------------------------------------
# Two modes:
#   1. sslip.io prototype:  make caddyfile-prod IP=13.235.50.100
#   2. real domain:         make caddyfile-prod DOMAIN=agroguardian.in
#
# Output: deploy/caddy/Caddyfile.prod
caddyfile-prod:
ifdef DOMAIN
	@echo "Rendering Caddyfile for domain: $(DOMAIN)"
	@sed \
		-e "s/api-IP-WITH-DASHES.sslip.io/api.$(DOMAIN)/g" \
		-e "s/mqtts-IP-WITH-DASHES.sslip.io/mqtts.$(DOMAIN)/g" \
		-e "s/dashboard-IP-WITH-DASHES.sslip.io/dashboard.$(DOMAIN)/g" \
		-e "s/metrics-IP-WITH-DASHES.sslip.io/metrics.$(DOMAIN)/g" \
		$(CADDY_TEMPLATE) > $(CADDY_PROD)
	@echo "Wrote $(CADDY_PROD)"
else ifdef IP
	@echo "Rendering Caddyfile for sslip.io with IP: $(IP)"
	@DASHED_IP=$$(echo $(IP) | tr '.' '-') && \
		sed "s/IP-WITH-DASHES/$$DASHED_IP/g" $(CADDY_TEMPLATE) > $(CADDY_PROD)
	@echo "Wrote $(CADDY_PROD)"
else
	@echo "Usage: make caddyfile-prod IP=<static-ip>  or  make caddyfile-prod DOMAIN=<your.domain>"
	@exit 1
endif

clean:
	rm -rf .venv build dist *.egg-info .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
