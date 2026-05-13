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
- `projects.py` — Table Storage CRUD for the `projects` table
- `updates.py` — Table Storage CRUD for the `updates` table (per-idea status updates)

## Infrastructure

All Azure infrastructure is managed in the **`azure-infrastructure`** package (`../azure-infrastructure/modules/ideasapi.bicep`). This includes:
- The Azure Functions app and app service plan
- All Azure Table Storage tables (`ideas`, `projects`, `updates`)
- EasyAuth / App Registration config
- RBAC role assignments

**Do not create Azure resources (tables, storage, etc.) lazily in Python code.** Declare them in `ideasapi.bicep` and let the infrastructure manage their lifecycle.

## Authentication

Two auth paths:
- **Browser (EasyAuth):** Azure Functions App Service Authentication validates tokens. Injects `X-MS-CLIENT-PRINCIPAL` header parsed by `require_auth()`. App Registration: `ideas-api`, audience: `api://ideas-api`.
- **Machine (write key):** Ideator job and bot send `X-Ideas-Key` header with `IDEAS_WRITE_KEY` value.

Helper in `function_app.py`:
- `_machine_or_user_auth(req)` — accepts either EasyAuth or the write key
- `require_auth(req)` — EasyAuth only; returns `(oid, email, display_name)`

## Endpoints

| Endpoint | Auth | Purpose |
|---|---|---|
| `GET /api/health` | None | Liveness |
| `GET /api/projects` | EasyAuth | List all projects |
| `POST /api/projects` | EasyAuth | Create a project |
| `GET /api/ideas` | EasyAuth or key | List ideas (optional `?status=open\|done\|dismissed`) |
| `POST /api/ideas` | EasyAuth or key | Create idea |
| `PATCH /api/ideas/{id}` | EasyAuth | Update idea fields (`status`, `project`, `title`, `body`) |
| `DELETE /api/ideas/{id}` | EasyAuth | Delete idea |
| `PATCH /api/ideas/{id}/bot` | Key only | Bot writes back `bot_status`, `bot_pr_url`, `bot_error` |
| `POST /api/ideas/{id}/run-bot` | EasyAuth | Trigger the ideas-bot Container App Job for an idea |
| `GET /api/ideas/{id}/updates` | EasyAuth or key | List status updates for an idea (oldest first) |
| `POST /api/ideas/{id}/updates` | EasyAuth or key | Post a status update; author from EasyAuth or `"bot"` for key |
| `DELETE /api/ideas/{id}/updates/{update_id}` | EasyAuth | Delete a status update |

## Table Storage Schema

All tables use `IDEAS_TABLE_CONNECTION_STRING`. Table names are hardcoded in each module.

**`ideas`** (PartitionKey: `"ideas"`, RowKey: UUID)
- `project`, `project_id`, `title`, `body`, `status` (`open`/`done`/`dismissed`), `created_at`, `source`, `bot_status`, `bot_pr_url`, `bot_error`

**`projects`** (PartitionKey: `"projects"`, RowKey: UUID)
- `name`

**`updates`** (PartitionKey: `idea_id`, RowKey: UUID)
- `content`, `created_at`, `author_email`, `author_name`

## Environment Variables

- `IDEAS_TABLE_CONNECTION_STRING` — Azure Table Storage connection string
- `IDEAS_WRITE_KEY` — shared secret for machine-to-machine writes
- `IDEAS_CLIENT_SECRET` — EasyAuth App Registration client secret
- `BOT_JOB_SUBSCRIPTION_ID` — Azure subscription for the ideas-bot Container App Job
- `BOT_JOB_RESOURCE_GROUP` — resource group for the ideas-bot job
- `BOT_JOB_NAME` — name of the ideas-bot Container App Job

## CI/CD

`.github/workflows/deploy.yml` triggers on push to `main`. After deploy it updates architecture metadata and triggers an arch-content refresh in `my-website`.

GitHub Actions secrets needed: `AZURE_CREDENTIALS`, `IDEAS_API_APP_NAME`, `DESIGN_DOC_GH_TOKEN`, `ARCH_CONTENT_FOUNDRY_KEY`.
