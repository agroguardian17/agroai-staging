# Postgres backups (finding F-013)

Nightly `pg_dump` of the running `agro_postgres` container to an S3-compatible
bucket (Cloudflare **R2** or Backblaze **B2**), with local + remote retention
pruning. Fills the "Nightly `pg_dump` backups to B2/R2 — add and test restore
before real farmer data flows" to-do in `deploy/staging/README.md`.

> **Status: dormant until you provide a bucket + credentials.** The script is
> fail-loud — with no config the timer run errors (visibly) rather than
> silently backing up nothing. Nothing runs until you do the setup below.

## Files
| file | role |
|---|---|
| `pg_backup.sh` | the backup job: `pg_dump -Fc` → local file → `aws s3 cp` → prune |
| `agro-pg-backup.service` | systemd oneshot that runs the script with the env file |
| `agro-pg-backup.timer` | daily schedule (02:30 UTC / 08:00 IST) |

## One-time setup (on the VPS, as root)

1. **Create a bucket** in R2 or B2 (e.g. `agro-staging-backups`) and an
   access key scoped to it.

2. **Install the AWS CLI** (the script uses it as a generic S3 client):
   ```bash
   sudo apt-get update && sudo apt-get install -y awscli
   ```

3. **Write the credentials env file** (root-owned, `chmod 600` — never in git):
   ```bash
   sudo install -d -m 700 /etc/agro
   sudo tee /etc/agro/backup.env >/dev/null <<'ENV'
   POSTGRES_USER=agro
   POSTGRES_DB=agro
   BACKUP_LOCAL_DIR=/var/backups/agro-pg
   BACKUP_S3_BUCKET=s3://agro-staging-backups
   BACKUP_S3_ENDPOINT=https://<ACCOUNT_ID>.r2.cloudflarestorage.com
   AWS_ACCESS_KEY_ID=<key>
   AWS_SECRET_ACCESS_KEY=<secret>
   AWS_DEFAULT_REGION=auto
   RETENTION_DAYS=14
   ENV
   sudo chmod 600 /etc/agro/backup.env
   ```
   (B2: use the bucket's S3 endpoint, e.g.
   `https://s3.us-west-004.backblazeb2.com`, and its region instead of `auto`.)

4. **Install and enable the unit + timer** (paths in the unit assume the
   canonical deploy dir `/home/ubuntu/agri-AI-live/agro_backend`; edit if yours
   differs):
   ```bash
   sudo cp deploy/backup/agro-pg-backup.{service,timer} /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now agro-pg-backup.timer
   ```

5. **Prove it end-to-end** (run once by hand and watch the log):
   ```bash
   sudo systemctl start agro-pg-backup.service
   journalctl -u agro-pg-backup.service -n 50 --no-pager
   aws s3 ls s3://agro-staging-backups/ --endpoint-url "$BACKUP_S3_ENDPOINT"
   ```

## Restore drill (do this before real farmer data flows)

Restore into a throwaway database and diff, never straight over prod:

```bash
# 1. pull a dump locally
aws s3 cp s3://agro-staging-backups/agro-agro-<STAMP>.dump /tmp/restore.dump \
  --endpoint-url "$BACKUP_S3_ENDPOINT"

# 2. copy it into the container and restore into a scratch DB
docker cp /tmp/restore.dump agro_postgres:/tmp/restore.dump
docker exec agro_postgres psql -U agro -d postgres -c "DROP DATABASE IF EXISTS agro_restore_test;" -c "CREATE DATABASE agro_restore_test;"
docker exec agro_postgres pg_restore -U agro -d agro_restore_test --no-owner --no-privileges /tmp/restore.dump

# 3. sanity-check, then drop the scratch DB
docker exec agro_postgres psql -U agro -d agro_restore_test -c "SELECT count(*) FROM tenants;"
docker exec agro_postgres psql -U agro -d postgres -c "DROP DATABASE agro_restore_test;"
docker exec agro_postgres rm -f /tmp/restore.dump
```

A backup you have never restored is not a backup. Re-run the drill after any
Postgres major-version bump.
