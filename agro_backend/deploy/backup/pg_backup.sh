#!/usr/bin/env bash
#
# Nightly Postgres backup for AgroGuardian staging/prod (finding F-013).
#
# Dumps the running `agro_postgres` container with pg_dump's custom format
# (-Fc, already compressed + selective-restore capable), writes it locally,
# uploads it to an S3-compatible bucket (Cloudflare R2 or Backblaze B2), then
# prunes both local and remote copies older than the retention window.
#
# It is intentionally FAIL-LOUD: if the bucket/credentials are not configured
# it exits non-zero so the systemd timer surfaces the misconfiguration rather
# than silently producing no backups. Nothing here runs until you install the
# unit + timer and provide the env file (see deploy/backup/README.md).
#
# Config (environment, e.g. from /etc/agro/backup.env):
#   PG_CONTAINER        default: agro_postgres
#   POSTGRES_USER       default: agro
#   POSTGRES_DB         default: agro
#   BACKUP_LOCAL_DIR    default: /var/backups/agro-pg
#   BACKUP_S3_BUCKET    required, e.g. s3://agro-staging-backups
#   BACKUP_S3_ENDPOINT  required, e.g. https://<acct>.r2.cloudflarestorage.com
#   AWS_ACCESS_KEY_ID   required (R2/B2 access key)
#   AWS_SECRET_ACCESS_KEY required
#   AWS_DEFAULT_REGION  default: auto  (R2 uses "auto"; B2 uses its region)
#   RETENTION_DAYS      default: 14
#
set -euo pipefail

PG_CONTAINER="${PG_CONTAINER:-agro_postgres}"
POSTGRES_USER="${POSTGRES_USER:-agro}"
POSTGRES_DB="${POSTGRES_DB:-agro}"
BACKUP_LOCAL_DIR="${BACKUP_LOCAL_DIR:-/var/backups/agro-pg}"
AWS_DEFAULT_REGION="${AWS_DEFAULT_REGION:-auto}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
export AWS_DEFAULT_REGION

log() { printf '%s agro-pg-backup: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
die() { log "ERROR: $*" >&2; exit 1; }

command -v aws >/dev/null 2>&1 || die "aws CLI not found on PATH (needed for S3/R2/B2 upload)."
command -v docker >/dev/null 2>&1 || die "docker not found on PATH."
: "${BACKUP_S3_BUCKET:?BACKUP_S3_BUCKET must be set (e.g. s3://agro-staging-backups)}"
: "${BACKUP_S3_ENDPOINT:?BACKUP_S3_ENDPOINT must be set (R2/B2 S3 endpoint URL)}"
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID must be set}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY must be set}"

docker inspect -f '{{.State.Running}}' "$PG_CONTAINER" 2>/dev/null | grep -q true \
  || die "container '$PG_CONTAINER' is not running."

mkdir -p "$BACKUP_LOCAL_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
FILE="agro-${POSTGRES_DB}-${STAMP}.dump"
LOCAL_PATH="${BACKUP_LOCAL_DIR}/${FILE}"

log "dumping ${POSTGRES_DB} from ${PG_CONTAINER} -> ${LOCAL_PATH}"
# -Fc custom format; stream out of the container to a local file.
if ! docker exec -t "$PG_CONTAINER" \
      pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-privileges \
      > "$LOCAL_PATH"; then
  rm -f "$LOCAL_PATH"
  die "pg_dump failed."
fi

SIZE="$(wc -c < "$LOCAL_PATH" | tr -d '[:space:]')"
[ "${SIZE:-0}" -gt 0 ] || { rm -f "$LOCAL_PATH"; die "dump is empty."; }
log "dump ok (${SIZE} bytes); uploading to ${BACKUP_S3_BUCKET}/${FILE}"

aws s3 cp "$LOCAL_PATH" "${BACKUP_S3_BUCKET%/}/${FILE}" \
  --endpoint-url "$BACKUP_S3_ENDPOINT" --only-show-errors \
  || die "upload failed."
log "upload ok"

# Prune local copies older than retention.
find "$BACKUP_LOCAL_DIR" -name 'agro-*.dump' -type f -mtime "+${RETENTION_DAYS}" -print -delete \
  | sed 's/^/pruned local: /' || true

# Prune remote objects older than retention (compare against object LastModified).
CUTOFF_EPOCH="$(date -u -d "-${RETENTION_DAYS} days" +%s 2>/dev/null || date -u -v-"${RETENTION_DAYS}"d +%s)"
aws s3 ls "${BACKUP_S3_BUCKET%/}/" --endpoint-url "$BACKUP_S3_ENDPOINT" 2>/dev/null \
  | while read -r d t _size name; do
      [ -n "${name:-}" ] || continue
      obj_epoch="$(date -u -d "${d} ${t}" +%s 2>/dev/null || echo 0)"
      if [ "$obj_epoch" -gt 0 ] && [ "$obj_epoch" -lt "$CUTOFF_EPOCH" ]; then
        aws s3 rm "${BACKUP_S3_BUCKET%/}/${name}" --endpoint-url "$BACKUP_S3_ENDPOINT" --only-show-errors \
          && log "pruned remote: ${name}"
      fi
    done

log "done"
