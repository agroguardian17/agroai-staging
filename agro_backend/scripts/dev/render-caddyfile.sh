#!/usr/bin/env bash
# Render the production Caddyfile for AgroGuardian.
#
# Usage:
#   ./scripts/dev/render-caddyfile.sh --ip 13.235.50.100
#   ./scripts/dev/render-caddyfile.sh --domain agroguardian.in
#
# Output: deploy/caddy/Caddyfile.prod
# Coolify mounts this rendered file into the caddy container.
#
# Equivalent to scripts/dev/render-caddyfile.ps1 (PowerShell version for Windows).

set -euo pipefail

usage() {
    cat <<USAGE
Usage:
  $0 --ip 13.235.50.100        # render for sslip.io prototype
  $0 --domain agroguardian.in  # render for real domain

Output: deploy/caddy/Caddyfile.prod
USAGE
    exit 1
}

IP=""
DOMAIN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ip)
            IP="$2"
            shift 2
            ;;
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage
            ;;
    esac
done

if [[ -z "$IP" && -z "$DOMAIN" ]] || [[ -n "$IP" && -n "$DOMAIN" ]]; then
    echo "Error: provide exactly one of --ip or --domain" >&2
    usage
fi

# Resolve repo root from this script's location: scripts/dev/render-caddyfile.sh
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
TEMPLATE="$REPO_ROOT/deploy/caddy/Caddyfile"
OUTPUT="$REPO_ROOT/deploy/caddy/Caddyfile.prod"

if [[ ! -f "$TEMPLATE" ]]; then
    echo "Template not found: $TEMPLATE" >&2
    exit 1
fi

if [[ -n "$DOMAIN" ]]; then
    # macOS ships BSD sed which requires '-i ""' for in-place; we redirect instead so it
    # works identically on macOS, Linux and Git Bash for Windows.
    sed \
        -e "s/api-IP-WITH-DASHES\.sslip\.io/api.${DOMAIN}/g" \
        -e "s/mqtt-IP-WITH-DASHES\.sslip\.io/mqtt.${DOMAIN}/g" \
        -e "s/dashboard-IP-WITH-DASHES\.sslip\.io/dashboard.${DOMAIN}/g" \
        -e "s/metrics-IP-WITH-DASHES\.sslip\.io/metrics.${DOMAIN}/g" \
        "$TEMPLATE" > "$OUTPUT"
    echo "Rendered Caddyfile for domain: $DOMAIN"
else
    if ! [[ "$IP" =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]]; then
        echo "IP '$IP' does not look like a valid IPv4 address" >&2
        exit 1
    fi
    DASHED_IP="${IP//./-}"
    sed "s/IP-WITH-DASHES/${DASHED_IP}/g" "$TEMPLATE" > "$OUTPUT"
    echo "Rendered Caddyfile for sslip.io with IP: $IP (dashed: $DASHED_IP)"
fi

echo "Wrote $OUTPUT"
