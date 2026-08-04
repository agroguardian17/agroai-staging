#!/usr/bin/env bash
# Provision an MQTT credential for a hardware device (Main Node).
#
# Uses a one-off Mosquitto container's mosquitto_passwd tool to bcrypt the
# password directly into deploy/mosquitto/passwd, then appends the ACL entry
# that scopes this user to the telemetry namespace. The one-off container is
# required because staging/production mount passwd read-only in Mosquitto.
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

# Create the bind-mounted files before Docker sees them. This also avoids
# Docker creating a directory at a missing file mount point.
touch "$PASSWD_FILE" "$ACL_FILE"
chmod 644 "$PASSWD_FILE" "$ACL_FILE"

# 1. Set / update the password via mosquitto_passwd in a disposable container.
#    -b: batch mode (non-interactive)
#    -c: create the password file
echo ">>> Updating $PASSWD_FILE for user '$USERNAME'"
docker run --rm \
    -v "$ROOT_DIR/deploy/mosquitto:/mosquitto/config" \
    eclipse-mosquitto:2.0.18 \
    mosquitto_passwd -b -c /mosquitto/config/passwd "$USERNAME" "$PASSWORD"
chmod 644 "$PASSWD_FILE"

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
echo "    docker compose -f docker-compose.prod.yml restart mosquitto"
echo ""
echo ">>> Credential summary:"
echo "    username: $USERNAME"
echo "    password: (as supplied, not echoed)"
echo "    ACL scope: read/write agro/v2/#"
