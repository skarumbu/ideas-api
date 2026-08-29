# ADR: Machine Key Auth For Project Creation
**Date:** 2026-08-29  **Status:** Proposed  **PR:** [ideas-api#17](https://github.com/skarumbu/ideas-api/pull/17)

## Context
The `POST /api/projects` endpoint previously required EasyAuth for authentication, limiting usage to authenticated users. This change introduces machine-key authentication, enabling external systems or automated processes to create projects without user-specific credentials, broadening API accessibility.

## Decision
The authentication mechanism for `POST /api/projects` was updated to support both EasyAuth and machine-key authentication. This decision balances usability for automated systems with security considerations, ensuring flexibility while maintaining controlled access.

## Alternatives Considered
- **Retain EasyAuth-only authentication:** Rejected due to limited support for non-user-based integrations.
- **Require machine-key authentication exclusively:** Rejected as it would exclude user-based interactions and reduce flexibility.
- **Custom token-based authentication:** Rejected due to increased implementation complexity and maintenance overhead.

## Consequences
**Positive:**
- Enables automated systems to interact with the API without user-specific credentials.
- Broadens the API's applicability for external integrations.

**Trade-offs:**
- Requires additional documentation and monitoring to address potential security risks.
- Introduces complexity in managing machine keys securely.

## Relevant Code
- [`CLAUDE.md`](https://github.com/skarumbu/ideas-api/blob/main/CLAUDE.md)
- [`function_app.py`](https://github.com/skarumbu/ideas-api/blob/main/function_app.py)
