# MacBook Setup — Round 8 (Phase 3 Stage 8)


Applies on top of a green Round 7. Everything below assumes you're in
the directory that contains `agro_backend/`.


---


## 0. Apply the bootstrap


```bash
bash bootstrap_phase3_stage8.sh
```


This writes 40 files into `agro_backend/` (idempotent — re-running just
overwrites the Round 8 files).


---


## 1. Set up the shell


```bash
cd agro_backend
source .venv/bin/activate


# Pull the dev secrets into the shell:
set -a; source .env; set +a


# Verify the password landed:
echo "$POSTGRES_PASSWORD"    # must NOT be empty


# Build the URLs the test conftest reads:
export DATABASE_URL_SYNC="postgresql://agro:$POSTGRES_PASSWORD@localhost:5433/agro"
export DATABASE_URL="postgresql+asyncpg://agro:$POSTGRES_PASSWORD@localhost:5433/agro"


# Sanity-check that psycopg2 can reach the DB:
psql "$DATABASE_URL_SYNC" -c "SELECT 1;"
```


If the URLs show as empty when you echo them, source `.env` again.


---


## 2. Apply migration 0009


```bash
alembic upgrade head
```


Expected output ends with:


```
INFO  [alembic.runtime.migration] Running upgrade 0008 -> 0009, 0009 OTP challenges + auth sessions
```


Verify the tables landed:


```bash
psql "$DATABASE_URL_SYNC" -c "\d otp_challenges"
psql "$DATABASE_URL_SYNC" -c "\d auth_sessions"
```


---


## 3. Run the test suite


```bash
pytest tests -v
```


Expected: roughly **250 passed, 1 skipped, 0 errors, 0 failures**.


Breakdown:
- Domain auth: 21 tests
- Application use cases: ~25 tests
- Infra JWT: 5 tests
- Infra WhatsApp (respx): 5 tests
- Infra Pg repos: ~15 tests (need Postgres; otherwise skipped)
- Infra HTTP routes: ~20 tests
- Plus everything that passed in Rounds 1-7


If anything fails, paste only the `short test summary info` block (the
last block of the pytest output, not the full traces) and we'll fix it
in one targeted edit.


---


## 4. Hit the API locally


```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```


Then in another terminal:


```bash
# Open the docs:
open http://localhost:8000/api/v1/docs
```


Or test the OTP flow end-to-end (replace the phone with whatever you
seeded in Round 1):


```bash
# 1. Send OTP. The code shows up in the uvicorn log because the dev
#    sender is the log-only adapter.
curl -X POST http://localhost:8000/api/v1/auth/send_otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"+91XXXXXXXXXX"}'


# 2. Look at the uvicorn log for a line like:
#    whatsapp.log_only_sender.fake_send ... otp_code='123456'
#    Copy that code.


# 3. Exchange it for tokens:
TOKENS=$(curl -s -X POST http://localhost:8000/api/v1/auth/verify_otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"+91XXXXXXXXXX","code":"123456"}')
echo "$TOKENS" | python -m json.tool


# 4. Use the access token:
ACCESS=$(echo "$TOKENS" | python -c "import json,sys;print(json.load(sys.stdin)['access_token'])")
curl -H "Authorization: Bearer $ACCESS" http://localhost:8000/api/v1/me
curl -H "Authorization: Bearer $ACCESS" http://localhost:8000/api/v1/plots
```


If `/plots` returns an empty list, that's expected unless you also have a
plot seeded for your test farmer.


---


## 5. Switching to real WhatsApp (deferred)


Round 8 defaults to the **log-only sender**: the OTP code is printed
to the uvicorn log rather than sent over WhatsApp. That keeps the
flow working without a verified Meta business account.


To switch to Meta when your account is ready:


1. Set in `.env`:
   ```
   APP_ENV=production
   META_WHATSAPP_PHONE_NUMBER_ID=<your phone number id>
   META_WHATSAPP_TOKEN=<your permanent access token>
   ```
2. Restart the server.
3. `app/infra/http/deps.py::get_whatsapp_sender` will pick the Meta
   adapter automatically.


No code change needed — that branching lives in `get_whatsapp_sender`.


---


## 6. Common gotchas


- **`echo "$DATABASE_URL_SYNC"` prints empty**: you need to re-source
  `.env` or re-export the URL after opening a new terminal. The
  `set -a; source .env; set +a` line is the only thing that pulls
  `POSTGRES_PASSWORD` into your shell.
- **`alembic upgrade head` says "no migrations to run"**: that means
  `0009` was already applied (the bootstrap is idempotent; the
  migration runs once).
- **`/api/v1/me` returns 401**: the access token is malformed or
  expired. Get a fresh pair from `/auth/verify_otp`.
- **The OTP code doesn't show up in the uvicorn log**: check that
  `APP_ENV` is NOT `production`. In production the log-only sender is
  refused and the Meta adapter is used; in dev/test the log-only
  sender is the default.


---


## After this round


When the tests are all green and you've tried the live API at least
once, tell me on the next session. Round 9 (Pure derived metrics +
rule engine — original Rounds 10+11 clubbed) is next.
