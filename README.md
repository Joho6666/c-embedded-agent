# Universal AI Gateway

Self-hosted AI API Gateway: Next.js control plane + FastAPI data plane.

```
BASE_URL=http://localhost:8000/v1
API_KEY=sk-gw-xxxx
```

## Implemented

- OpenAI-compatible `GET /v1/models`, `POST /v1/chat/completions` (SSE), `POST /v1/responses`
- Virtual models, credential pool, failover (429 / 5xx / timeout)
- Circuit breaker; API Key and Credential RPM/TPM/daily/monthly quotas with auto recovery
- Routing strategies from backend: priority, failover, round_robin, weighted_round_robin, least_latency, highest_success, quota_aware, health_aware, random, hybrid
- Request logs and Usage from RequestLog (cost is 0 until model pricing is set)
- Control plane BFF `/api/control/*` — admin secret is not shipped to the browser
- Optional login: `ADMIN_USERNAME` + `ADMIN_PASSWORD_HASH` (sha256 hex) → HttpOnly cookie
- Adapters: OpenAI Compatible, Gemini, Ollama, CLIProxy bridge

## Experimental

- CLIProxy / EasyCLIProxy official OAuth bridge (`:8317`). Management API varies by version; if login URL is unavailable, use the EasyCLIProxy tray. No cookie scraping.
- `ALLOW_LOCAL_UPSTREAM=true` for local mock/Ollama/CLIProxy loopback URLs on OpenAI-compatible adapters
- Optional Redis (`docker compose --profile redis up -d`) — State Backend becomes Redis when reachable; otherwise Memory

## Planned

- OIDC / GitHub / Google login (production login is env + cookie today)
- `least_load` / live `lowest_cost` (hidden until implemented)
- Embeddings / images / audio data plane

## Quick start

```bash
# backend
cd backend
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
set PYTHONPATH=.
set GATEWAY_ADMIN_API_KEY=dev-admin
set GATEWAY_SECRET_KEY=dev-secret
set CREDENTIAL_ENCRYPTION_KEY=dev-cred
set ALLOW_LOCAL_UPSTREAM=true
uvicorn app.main:app --port 8000

# frontend (another terminal)
cd ..
copy .env.example .env.local
# set GATEWAY_BACKEND_URL=http://127.0.0.1:8000
# set GATEWAY_ADMIN_API_KEY=dev-admin
# set GATEWAY_SECRET_KEY=dev-secret
npx next dev --port 3000
```

Do not run `npm run dev` from the `default` workspace (C-Embedded Agent). Use this repo only.

## Docker

Set secrets in the environment (no defaults in compose):

```bash
set GATEWAY_ADMIN_API_KEY=...
set GATEWAY_SECRET_KEY=...
set CREDENTIAL_ENCRYPTION_KEY=...
docker compose up -d --build
```

Redis: `docker compose --profile redis up -d --build`

Health page should show `State Backend = Redis` when the redis profile is running.

Backup: `python backend/scripts/backup.py` writes `gateway-backup-YYYYMMDD.zip`. Restore SQLite by stopping the backend and replacing `/data/gateway.db`. Encrypted credentials are not exported in plaintext.

Log cleanup: `python -m app.tasks.cleanup_logs` (also runs periodically on startup).

## Security notes

- Admin key never uses `NEXT_PUBLIC_*`
- Upstream URLs must be http/https; private/loopback hosts are rejected unless the adapter is local or `ALLOW_LOCAL_UPSTREAM=true`
- SQL uses bound parameters
- Secrets come from environment variables
