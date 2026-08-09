# Standardize project linkage for ideas

**Status:** Accepted
**Supersedes:** #9 ("fix: auto-resolve project_id on idea creation")

## Goal

Every idea has a real, linkable project, and every project has its own page
on the site. `ProjectPage.tsx` (`/ideas/projects/{id}`) already builds that
page — links out to `project.repo` on GitHub and to the architecture page —
but only when `project_id` is actually set. It isn't reliably set today:
`create_idea` trusts the caller for `project`/`project_id`, with no lookup
or validation, so some ideas end up with a project *name* but no
`project_id` and no clickable project tag.

- Every **project** is identified by its `name` (unchanged from today —
  `create_project` already dedupes on `name`; `repo` stays an optional field
  used for the GitHub/architecture links, not for identity).
- Every **idea** has a `project_id`, set at creation time, no exceptions.

## Design

### 1. `create_idea` requires a resolvable project — no silent creation

`create_idea(data)` resolves the target project:

- If `project_id` is given, use it directly.
- Else, resolve `project` (name) via `get_project_by_name(project)`.

If no matching project is found, **reject the idea** with a 400:

> No project found named '<project>'. Register it first via Manage Projects.

This replaces PR #9's behavior of auto-creating a new project on a miss.
Projects are a deliberate, pre-registered set — an idea can only target one
that already exists.

If resolution succeeds, `project_id` is always set server-side, regardless
of what the caller passed. This closes the original gap: callers that only
send a name can no longer produce a project-less idea.

`update_idea` is unchanged. PR #9 flagged the same trust gap there (PATCHing
`project` without `project_id`), but there's no evidence of it happening in
practice — left out of scope here, same as the original PR.

### 2. Backfill is a one-time script, not an API endpoint

A script, run once by hand, scans the `ideas` table for entries with no
`project_id` and resolves each by matching its `project` string against an
existing project's `name`. Where no project exists yet for that name (e.g.
a project that was only ever referenced in idea text, never registered), it
is created — this is the deliberate registration step the reject-on-miss
behavior above expects to have already happened; a one-time backfill is the
one place it's appropriate to do it automatically rather than by hand
through Manage Projects.

Not wired into the deploy pipeline or exposed as a route.

### 3. Callers

- `ideas-bot`'s `create_idea` tool already resolves `project_name` against a
  known projects list and passes `project_id` — no change required. It now
  gets a hard rejection instead of a silent auto-create if it ever passes an
  unrecognized name, which is strictly safer.
- The local MCP server needs to pass a `project` name that matches an
  existing project's `name` (or a `project_id` directly) once this ships.

## Out of scope

- Retroactively fixing `update_idea`'s equivalent trust gap.
- Any change to how `repo` works — it remains an optional field set via
  Manage Projects, unrelated to project identity.

## Revision history

- **2026-08-03:** Initial version keyed project identity by `repo` instead
  of `name`, requiring `repo` on every project. Reverted — project identity
  stays `name`-based, matching the system's existing convention
  (`create_project` already dedupes on name; nothing else in the codebase
  keys off `repo`). `repo` remains optional, used only for the GitHub/
  architecture links on a project's page.
