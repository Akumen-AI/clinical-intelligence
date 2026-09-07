# Audit Logging Contract

This document defines the strict contract and standards for writing to the audit log. All state-changing actions and PHI-access events must adhere to these guidelines to ensure the system remains auditable, compliant, and correctly scoped to patients where applicable.

## 1. The Write Contract

The audit log is interacted with via the `audit_service` in `backend/app/services/audit_service.py`.

There are two primary methods for writing to the audit log:
- **`audit_service.write_entry(...)`**: The standard synchronous call. Must be used for all standard API requests handled on a single thread (using `SessionLocal`).
- **`audit_service.write_entry_async(...)`**: The asynchronous call. Must be used in Celery tasks and background processes utilizing an `AsyncSession` to prevent database locks and concurrency issues (particularly relevant for SQLite).

### Required Parameters
All write calls **MUST** explicitly define the following parameters:
- `action_type`: A string representing the action (see naming convention below).
- `target_entity`: A string representing the entity being operated on (e.g., `document:<id>`, `pending_review:<id>`, `patient:<id>`).
- `patient_id`: A string representing the ID of the patient affected by the action. This parameter is strictly enforced: you **must pass it explicitly**. If the action is patient-scoped and the ID is known, pass the ID. If the action is aggregate, cross-patient, or the patient is genuinely unknown at that step of the pipeline (e.g., a raw document upload), you must explicitly pass `None`. Do not omit it or guess its value.
- `actor_user_id`: The UUID of the user performing the action.
- `rationale`: A human-readable description of what changed or what was viewed, stripped of actual clinical values or raw PHI.

## 2. Naming Conventions

The `action_type` parameter must strictly adhere to a **snake_case, verb-object-ish** naming convention to maintain a consistent ontology.

Examples of established `action_type` formats:
- `document_uploaded`
- `document_extracted`
- `review_approve`
- `review_reject`
- `patient_dashboard_viewed`
- `department_dashboard_viewed`
- `correction_log_export`
- `rag_query`
- `policy_rag_query`

Do not invent ad-hoc naming patterns (e.g., avoid `UploadedDocument`, `Export_Action`, `viewDashboard`).

## 3. Epic 8 (Agent-Assisted Report Generation) Contract

Epic 8 (BRD FR-28 and FR-29) is currently unimplemented. When this epic is built, its audit logging implementation must strictly adhere to the following contracts from the first commit to ensure compliance:

### POST `/reports/generate` (FR-28)
- **`action_type`**: `"agent_report_generated"`
- **`patient_id`**: Set to the specific patient's ID if the natural-language request resolves to a single-patient query. Leave as `None` if it is an aggregate/cohort query (e.g., "all diabetic patients this quarter").
- **`rationale`**: Must include both the natural-language request text and the structured query/filters the agent derived from it. This ensures that the audit trail and the user-facing transparency requirement (FR-28: "shown to the user, not hidden as a black box") are backed by the exact same captured data, rather than two separate implementations. 

### GET/POST `/reports/export` (FR-29)
- **`action_type`**: `"report_exported"`
- **`target_entity`**: Must identify the specific report or export batch (e.g., `export_batch:<id>`).
- **`patient_id`**: Typically `None` since exports are usually cross-patient batch exports. 
- **`rationale`**: Must state the export format (e.g., PDF/Excel/CSV) and the row/record count. It must **never** include the exported data, PHI values, or sensitive record details.

## 4. Test Enforcement

To prevent the structural test suite from drifting out of sync with this contract, the test suite actively enforces declarative audit coverage for all state-changing endpoints.

When Epic 8 ships, you **must** update the declarative mapping in `backend/tests/test_audit_coverage_enforced.py` by adding the two new routes (`/reports/generate` and `/reports/export`) and their expected `action_type`s to the verification matrix. This ensures continuous CI/CD enforcement of the audit trail.
