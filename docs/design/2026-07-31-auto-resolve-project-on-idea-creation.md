# ADR: Auto Resolve Project On Idea Creation
**Date:** 2026-07-31  **Status:** Proposed  **PR:** [ideas-api#9](https://github.com/skarumbu/ideas-api/pull/9)

## Context
Ideas in the system were not consistently linked to valid projects, leading to potential data inconsistencies and usability issues. This change ensures that every idea is associated with a real, linkable project by resolving the project ID based on the project name or creating a new project if it doesn't exist.

## Decision
The system will automatically resolve the project ID for an idea during its creation. If the project name exists, the corresponding project ID will be fetched; otherwise, a new project will be created. This guarantees that all ideas are tied to valid projects, improving data integrity and user experience.

## Alternatives Considered
- **Require explicit project ID input:** Rejected as it places an unnecessary burden on users and external systems.
- **Allow ideas without projects:** Rejected as it leads to orphaned ideas and reduces data consistency.
- **Pre-create all possible projects:** Rejected due to scalability concerns and the impracticality of predicting all potential projects.

## Consequences
**Positive:**  
- Ensures all ideas are linked to valid projects.  
- Improves data consistency and usability across the service.  
- Reduces manual effort for users and external systems.  

**Trade-offs:**  
- Slightly increased complexity in the idea creation logic.  
- Potential for race conditions when creating projects concurrently, though mitigated by fallback logic.  

## Relevant Code
- [`ideas.py`](https://github.com/skarumbu/ideas-api/blob/main/ideas.py)  
- [`projects.py`](https://github.com/skarumbu/ideas-api/blob/main/projects.py)
