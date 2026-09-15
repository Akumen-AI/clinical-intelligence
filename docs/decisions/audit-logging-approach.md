# ADR: Audit Logging Approach - Manual vs. Interceptor

## Context
The System Design Document (SDD §8.3) specifies that audit logging should flow through a central "Access Control & Audit Service" acting as a gateway layer. In an ideal state, this means audit events would be intercepted and logged automatically via middleware or a FastAPI dependency at the API boundary, guaranteeing that all sensitive actions are recorded without relying on developers to explicitly invoke a logger.

## Current Implementation
Despite the SDD's architectural vision, the current implementation relies on explicit, manual calls to `app.services.audit_service.write_entry()` (or `write_entry_async()`) dispersed throughout individual service modules (e.g., `canonical_record_service`, `field_extraction_service`). 

### Why this is the case today
- **Expediency during initial build:** Direct, manual calls were faster to implement while the data models for extracted fields and RAG queries were still stabilizing. 
- **Complex Rationale Strings:** Some logging events require rich, context-specific `rationale` strings (like "Extracted 10 fields. 2 below threshold.") which are easily constructed in the heart of the service logic, but difficult to reverse-engineer purely from an HTTP response in generic middleware.
- **Background Tasks:** Actions such as background folder watching and async confidence routing happen outside the context of an HTTP request. Standard FastAPI middleware wouldn't capture these internal system events.

## Consequences & Gaps
- **Compliance Risk:** The manual approach introduces the risk of human error (forgetting to log an action), leading to gaps in compliance against BRD FR-31. For instance, `field_extraction_service.py` initially lacked audit logging entirely.
- **Code Duplication:** Logging logic is scattered, making global changes to the audit schema harder.
- **Inconsistency with SDD:** We are carrying architectural debt by explicitly diverging from the documented gateway design.

## Future Refactor Path
To bring the codebase in line with the SDD, a future refactor should introduce an **interceptor-based approach**:
1. **API Middleware/Dependency:** Create a FastAPI dependency (e.g., `AuditLogger`) that can be injected into routes. It would automatically log the route's execution, capturing the user ID from the auth token, the targeted entity from the path parameters, and the action type from route metadata.
2. **Standardized Response Envelopes:** To capture rich internal logic (like threshold counts), services could yield structured events or append metadata to a shared request context (e.g., `request.state.audit_metadata`) that the middleware consumes on the way out.
3. **Event Bus for Background Tasks:** For non-HTTP tasks, a lightweight event bus (e.g., pub/sub or simple signals) could be used to emit domain events (`FieldExtractionCompletedEvent`) which a central audit listener persists, decoupling the logging from the core logic.
