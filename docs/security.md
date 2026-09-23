# Security & Authorization

## Authentication
The platform uses JWT-based authentication.

## Role-Based Access Control (RBAC)
Strict role-based access control is enforced at both the API routing layer and frontend navigation layer.

Supported Roles:
- **Doctor**: Clinical access to assigned patients.
- **Nurse**: Clinical access and correction capabilities for assigned patients.
- **Hospital Admin**: System-wide operations and policy management.
- **Department Head**: Read-only aggregated operations dashboards.
- **IT**: System maintenance and RAG knowledge base uploads.
- **Compliance**: Audit log and policy management.

## Patient-Level Access Guardrails
Beyond endpoint-level role protection, the system enforces **record-level access controls** via a server-side `AuthorizationService`. If an authenticated clinical user attempts to access a patient record not explicitly bound to their access list, the service rejects the request with a `403 Forbidden` error.

## Audit Logging
The platform includes an append-only audit log that records all security-sensitive and AI-driven actions. Actions are tied to unique request `correlation_id`s, allowing trace-ability across asynchronous background tasks.
