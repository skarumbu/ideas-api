# ADR: Enforce Project Linkage On Idea Creation
**Date:** 2026-08-09  **Status:** Proposed  **PR:** [ideas-api#13](https://github.com/skarumbu/ideas-api/pull/13)

## Context
Ideas were being created without a valid project association, leading to orphaned ideas with no linkable project page. This undermined data integrity and made project navigation inconsistent.

## Decision
Require every idea to resolve to a valid project during creation. Projects are identified by their name, and ideas without a matching project are rejected. A one-time backfill script ensures existing ideas are updated to comply with this rule, improving system consistency.

## Alternatives Considered
- **Auto-create projects on idea creation:** Rejected to avoid unintended proliferation of projects and ensure deliberate registration.
- **Key projects by `repo` instead of `name`:** Rejected due to existing system conventions that identify projects by name.
- **Expose backfill as an API endpoint:** Rejected for security and operational simplicity; backfill is a one-time manual script.

## Consequences
**Positive:**
- Ensures all ideas are linked to valid projects, improving data integrity.
- Prevents creation of orphaned ideas, enhancing navigation and usability.
- Aligns with existing project registration workflows.

**Trade-offs:**
- Requires stricter validation during idea creation, which may reject some inputs that previously succeeded.
- Adds one-time operational overhead to run the backfill script.

## Relevant Code
- [`ideas.py`](https://github.com/skarumbu/ideas-api/blob/main/ideas.py): Enforces project resolution during idea creation.
- [`projects.py`](https://github.com/skarumbu/ideas-api/blob/main/projects.py): Adds helper function to resolve projects by name.
- [`scripts/backfill_project_ids.py`](https://github.com/skarumbu/ideas-api/blob/main/scripts/backfill_project_ids.py): One-time script to update existing data.
