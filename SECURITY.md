# Security

Self-host this Gateway behind a reverse proxy. Do not expose the Admin Panel or SQLite file to the public internet.

## Production checklist

- Set `APP_ENV=production`
- Use long random values for `GATEWAY_ADMIN_API_KEY`, `GATEWAY_SECRET_KEY`, and `CREDENTIAL_ENCRYPTION_KEY`
- Set `ADMIN_USERNAME` and `ADMIN_PASSWORD_HASH` (sha256 hex). `REQUIRE_ADMIN_LOGIN=true` refuses boot without username
- Terminate TLS at the reverse proxy
- Restrict Admin (`/admin`, `/api/control`) with firewall or VPN
- Keep `ALLOW_LOCAL_UPSTREAM=false` unless you are developing against Ollama / CLIProxy
- Back up `data/gateway.db` regularly (`python backend/scripts/backup.py`). Restore by replacing the SQLite file while the process is stopped. Encrypted credential blobs stay encrypted
- Rotate Gateway API keys if leaked. Upstream secrets are stored encrypted; the encryption key is the root secret

## Network

- Upstream URLs must be `http` or `https`
- Loopback, RFC1918, link-local, and metadata IPs are rejected for remote providers
- Only Ollama / CLIProxy (or `ALLOW_LOCAL_UPSTREAM` in non-production) may use localhost

## Data

- Redis holds RPM/TPM/RR/WRR counters only. SQLite (or PostgreSQL) holds business data
- Request logs are deleted after `LOG_RETENTION_DAYS` (default 30)
