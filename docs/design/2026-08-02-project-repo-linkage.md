# Project/repo linkage for ideas

**Status:** Proposed
**Supersedes:** #9 ("fix: auto-resolve project_id on idea creation")

## Problem

`create_idea()` trusts the caller for `project`/`project_id`, with no lookup or
validation. The frontend composer resolves/creates the project correctly
before submitting, but other callers (the local MCP server, and by extension
anything bot-created) can pass just a project name — `project_id` is
optional. This produces ideas with a project name but no `project_id`, which
means no linkable project page (`Ideas.tsx` only renders the project tag as a
link when `project_id` is set).

Every idea should be required to link to a real project, and every project
should be addressable by its repo — not by a free-text name that can drift
or duplicate.

## Design

### 1. Project identity is keyed by repo

`repo` becomes the unique lookup key for a project. `name` remains a
separate display label (unchanged in the UI), but is no longer used to
resolve or dedupe projects during idea creation.

Add `get_project_by_repo(repo: str) -> dict | None` to `projects.py`,
parallel to the existing `get_project_by_name()`.

### 2. `create_idea` resolves and requires a project — no silent creation

`create_idea(data)` accepts either `repo` or `project` (name) to identify
the target project:

- If `repo` is given, resolve via `get_project_by_repo(repo)`.
- Else if `project` (name) is given, resolve via `get_project_by_name(project)`.

If no matching project is found, **reject the idea** with a 400:

> No project found for repo '<repo>'. Register it first via Manage Projects.

This replaces PR #9's behavior of auto-creating a new project on a miss.
Projects are now a deliberate, pre-registered set — an idea can only target
one that already exists.

If resolution succeeds, `project_id` is always set server-side, regardless
of what the caller passed. This closes the original gap: callers that only
send a name (or repo) can no longer produce a project-less idea.

`update_idea` is unchanged. PR #9 flagged the same trust gap there (PATCHing
`project` without `project_id`), but there's no evidence of it happening in
practice — left out of scope here, same as the original PR.

### 3. Backfill is a one-time script, not an API endpoint

A standalone script scans the `ideas` table for entries with no
`project_id`, resolves each by matching its `project` string against a
project's `name` or `repo`, and PATCHes `project_id` in. Ideas with no
matching project are logged for manual triage rather than guessed at or
auto-assigned — consistent with "no silent project creation" above.

Run once by hand against the table; not wired into the deploy pipeline or
exposed as a route.

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
  project.
