# ADR: Project Repo Linked Idea Creation
**Date:** 2026-08-03  **Status:** Proposed  **PR:** [ideas-api#11](https://github.com/skarumbu/ideas-api/pull/11)

## Context
The `create_idea` API currently allows ideas to be created with a `project` name but no `project_id`, leading to inconsistent data and unlinked project pages. This change ensures all ideas are linked to pre-registered projects identified by a unique `repo` key, improving data integrity and project traceability.

## Decision
The `create_idea` API now requires a valid project, identified by either `repo` or `project` name, and rejects requests for unregistered projects. Silent project creation is removed, and a one-time backfill script resolves existing ideas missing `project_id`. This enforces stricter validation and ensures all ideas are tied to pre-existing projects.

## Alternatives Considered
- **Auto-create projects on idea creation:** Rejected due to risk of duplicate or unintended projects being created.
- **Continue relying on `project` name:** Rejected as names are prone to drift, duplication, and lack of uniqueness.
- **Expose backfill as an API endpoint:** Rejected to avoid unnecessary complexity and potential misuse.

## Consequences
**Positive:**  
- Ensures all ideas are linked to valid, pre-registered projects.  
- Improves data consistency and project traceability.  
- Prevents unintended project creation by enforcing stricter validation.  

**Trade-offs:**  
- Requires callers to pre-register projects before creating ideas.  
- Adds operational overhead for running the one-time backfill script.  

## Relevant Code
- [`docs/design/2026-08-02-project-repo-linkage.md`](https://github.com/skarumbu/ideas-api/blob/main/docs/design/2026-08-02-project-repo-linkage.md)
- [`projects.py`](https://github.com/skarumbu/ideas-api/blob/main/projects.py)
- [`create_idea`](https://github.com/skarumbu/ideas-api/blob/main/ideas.py#L45)
