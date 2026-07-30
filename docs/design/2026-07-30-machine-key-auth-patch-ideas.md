# ADR: Machine Key Auth Patch Ideas
**Date:** 2026-07-30  **Status:** Proposed  **PR:** [ideas-api#7](https://github.com/skarumbu/ideas-api/pull/7)

## Context
The `PATCH /ideas/{id}` endpoint previously required user authentication, limiting its usage to individual users. To support automated systems, the authentication mechanism is modified to allow machine key-based authentication alongside user authentication.

## Decision
The authentication logic for the `PATCH /ideas/{id}` endpoint is updated to use `_machine_or_user_auth(req)`, enabling both machine key-based and user-based authentication. This change ensures flexibility for automated systems while maintaining security for user access.

## Alternatives Considered
- **Retain user-only authentication:** Rejected as it limits automated system access and scalability.
- **Create a separate endpoint for machine authentication:** Rejected due to added complexity and redundancy.
- **Use API tokens instead of machine keys:** Rejected as machine keys are already established in the system.

## Consequences
**Positive:**  
- Enables automated systems to interact with the endpoint securely.  
- Improves scalability and flexibility for integrations.  

**Trade-offs:**  
- Requires additional documentation for machine key usage.  
- Slightly increases complexity in authentication logic.  

## Relevant Code
- [`function_app.py`](https://github.com/skarumbu/ideas-api/blob/main/function_app.py)
