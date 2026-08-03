# Standardize project ↔ repo linkage

**Status:** Proposed
**Supersedes:** #9 ("fix: auto-resolve project_id on idea creation")

## Goal

Every project maps 1:1 to a repo, and every project has its own page on the
site. This is already half-built — `ProjectPage.tsx` (`/ideas/projects/{id}`)
links out to `project.repo` on GitHub and to its architecture page, and
`create_project`/`update_project` already store `repo`. What's missing is
enforcement: `repo` is optional on a project, and idea creation doesn't
reliably set `project_id`, so the project ↔ repo ↔ page chain isn't
guaranteed to hold for every project or every idea.

This design standardizes that existing setup at the schema/code level rather
than adding new UI or new concepts:

- Every **project** has a `repo`, and `repo` is what identifies it.
- Every **idea** has a `project_id`, set at creation time, no exceptions.

## Design

### 1. `repo` is required and is the project's identity

`create_project` currently accepts `repo` as optional and dedupes on `name`.
Change it to:

- Require `repo` (non-empty) to create a project.
- Dedupe on `repo`, not `name`. `name` stays as a separate, editable display
  label — it just stops being the identity key.

Add `get_project_by_repo(repo: str) -> dict | None` to `projects.py`,
parallel to the existing `get_project_by_name()`, and use it for the dedupe
check in `create_project`.

### 2. `create_idea` requires a resolvable project — no silent creation

`create_idea(data)` accepts either `repo` or `project` (name) to identify
the target project:

- If `repo` is given, resolve via `get_project_by_repo(repo)`.
- Else if `project` (name) is given, resolve via `get_project_by_name(project)`.

If no matching project is found, **reject the idea** with a 400:

> No project found for repo '<repo>'. Register it first via Manage Projects.

This replaces PR #9's behavior of auto-creating a new project on a miss.
Projects are a deliberate, pre-registered set (each one gets a repo and a
page) — an idea can only target one that already exists.

If resolution succeeds, `project_id` is always set server-side, regardless
of what the caller passed. This closes the original gap: callers that only
send a name (or repo) can no longer produce a project-less idea.

`update_idea` is unchanged. PR #9 flagged the same trust gap there (PATCHing
`project` without `project_id`), but there's no evidence of it happening in
practice — left out of scope here, same as the original PR.

### 3. Backfill is a one-time script, not an API endpoint

Making `repo` required and keying on it only holds going forward unless
existing data is brought up to the same standard. One script, run once by
hand, does both:

- **Projects missing a `repo`:** logged for manual assignment (repo is
  project-specific info a script shouldn't guess).
- **Ideas missing a `project_id`:** resolved by matching the idea's `project`
  string against a project's `name` or `repo` and PATCHed in. Ideas with no
  matching project are logged for manual triage rather than guessed at or
  auto-assigned.

Not wired into the deploy pipeline or exposed as a route.

### 4. Callers

- `ideas-bot`'s `create_idea` tool already resolves `project_name` against a
  known projects list and passes `project_id` — no change required. It now
  gets a hard rejection instead of a silent auto-create if it ever passes an
  unrecognized name, which is strictly safer.
- The local MCP server (not in this repo) needs to pass `repo`, or a
  `project` name that matches an existing project's `name`, once this ships.

## Out of scope

- Retroactively fixing `update_idea`'s equivalent trust gap.
- Any UI changes — Manage Projects already supports setting `repo` per
  project; `ProjectPage.tsx` already builds the individual page from it.
