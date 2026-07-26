#!/usr/bin/env bash
# Provision an MQTT credential for a hardware device (Main Node).
#
# Uses the running Mosquitto container's mosquitto_passwd tool to bcrypt
# the password directly into deploy/mosquitto/passwd, then appends the
# ACL entry that scopes this user to the telemetry namespace. The pilot uses
# one credential for the Main Node publisher and backend subscriber.
#
# Idempotent: if the username already exists in passwd, we UPDATE (mosquitto_passwd
# overwrites the entry). ACL append is guarded with a grep so re-runs don't
# duplicate lines.
#
# Usage:
#   scripts/dev/provision_mqtt_credential.sh <username> <password>
#
# After running:
#   1. Restart the mosquitto container so it picks up the new passwd/acl:
#        docker compose -f docker-compose.dev.yml restart mosquitto
#   2. Test from another machine:
#        mosquitto_pub -h <mac-lan-ip> -p 1883 -u <username> -P <password> \
#          -t 'agro/v2/<tenant>/<farm>/<node>/telemetry' -m '{"$schema":"..."}'
#
# Notes:
# - Development port 1883 remains anonymous in mosquitto.conf for local tests.
# - Staging/production use mosquitto.prod.conf, where the internal listener
#   is authenticated and Caddy terminates public TLS on 8883.
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <username> <password>" >&2
    echo "Example: $0 main-node-001 <strong-random-secret>" >&2
    exit 1
fi

USERNAME="$1"
PASSWORD="$2"

# Locate agro_backend root (this script lives at scripts/dev/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PASSWD_FILE="$ROOT_DIR/deploy/mosquitto/passwd"
ACL_FILE="$ROOT_DIR/deploy/mosquitto/acl"

if [[ ! -f "$PASSWD_FILE" ]]; then
    echo "ERROR: passwd file not found at $PASSWD_FILE" >&2
    exit 2
fi
if [[ ! -f "$ACL_FILE" ]]; then
    echo "ERROR: acl file not found at $ACL_FILE" >&2
    exit 2
fi

# Ensure the mosquitto container is up so we can invoke its passwd tool.
if ! docker ps --format '{{.Names}}' | grep -q '^agro_mosquitto$'; then
    echo "ERROR: agro_mosquitto container is not running." >&2
    echo "       Start it with: docker compose -f docker-compose.dev.yml up -d mosquitto" >&2
    exit 3
fi

# 1. Set / update the password via mosquitto_passwd inside the container.
#    -b: batch mode (non-interactive)
#    -c: create file (only used if empty; safe to omit because file exists)
echo ">>> Updating $PASSWD_FILE for user '$USERNAME'"
docker exec -i agro_mosquitto mosquitto_passwd -b /mosquitto/config/passwd "$USERNAME" "$PASSWORD"

# 2. Append ACL entry if it isn't already present. Scope: publish + subscribe
#    on ``agro/v2/#``. Tighten to a specific tenant/farm prefix if you're
#    onboarding a multi-tenant deployment.
ACL_LINE_USER="user $USERNAME"
if ! grep -qxF "$ACL_LINE_USER" "$ACL_FILE"; then
    echo ">>> Appending ACL entry for '$USERNAME'"
    {
        echo ""
        echo "# device credential provisioned $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "$ACL_LINE_USER"
        echo "topic readwrite agro/v2/#"
        echo "topic read \$SYS/#"
    } >> "$ACL_FILE"
else
    echo ">>> ACL entry for '$USERNAME' already present; leaving as-is"
fi

echo ""
echo ">>> Restart mosquitto to pick up the new credentials:"
echo "    docker compose -f docker-compose.dev.yml restart mosquitto"
echo ""
echo ">>> Credential summary:"
echo "    username: $USERNAME"
echo "    password: (as supplied, not echoed)"
echo "    ACL scope: read/write agro/v2/#"
