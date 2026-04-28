# CLAUDE.md

## Project Overview

Ideas API is an Azure Functions (Python 3.11) backend that stores and serves AI-generated feature ideas. The Feature Ideator Container App Job posts ideas here instead of GitHub. A login-gated `/ideas` page on my-website reads from this API.

## Commands

```bash
pip install -r requirements.txt
func start   # requires Azure Functions Core Tools v4 and a local.settings.json
```

## Architecture

- `function_app.py` — route handlers
- `auth.py` — EasyAuth principal header parsing (`require_auth`)
- `ideas.py` — Table Storage CRUD for the `ideas` table

## Authentication

Two auth paths:
- **Browser (EasyAuth):** Azure Functions App Service Authentication validates tokens. Injects `X-MS-CLIENT-PRINCIPAL` header parsed by `require_auth()`. App Registration: `ideas-api`, audience: `api://ideas-api`.
- **Machine (write key):** Ideator job sends `X-Ideas-Key` header with `IDEAS_WRITE_KEY` value. Accepted by `GET /api/ideas` and `POST /api/ideas` only.

## Endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /api/health` | None | Liveness |
| `GET /api/ideas` | EasyAuth or key | List ideas (optional `?status=open\|done\|dismissed`) |
| `POST /api/ideas` | EasyAuth or key | Create idea; 409 if open duplicate `feature_name` exists |
| `PATCH /api/ideas/{id}` | EasyAuth | Update `status` field |
| `DELETE /api/ideas/{id}` | EasyAuth | Delete idea |

## Environment Variables

- `IDEAS_TABLE_CONNECTION_STRING` — Azure Table Storage connection string (table: `ideas`)
- `IDEAS_WRITE_KEY` — shared secret for machine-to-machine writes from the ideator job

## CI/CD

`.github/workflows/deploy.yml` triggers on push to `master`. GitHub Actions secrets needed: `AZURE_CREDENTIALS`, `IDEAS_API_APP_NAME`.
