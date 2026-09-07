# Audit Coverage Report 9.3

## 1. FR-31 Core Actions Coverage

| FR-31 Action | Currently Logged? | File:Line | Notes |
| :--- | :--- | :--- | :--- |
| AI extraction | Partial | `backend/app/services/upload_service.py:93, 327` | Logged via `document_extracted` (and `document_uploaded`) action types when preprocessing/extraction begins. However, `backend/app/services/field_extraction_service.py` (which actually populates ExtractedField rows with per-field confidence) **has no audit call**. This is a known Sprint 1 gap outside this story's scope but affects the FR-31 completeness check. Flagged for follow-up in Epic 1/9. |
| human correction | Yes | `backend/app/routers/review.py:394, 439` | Logged via `review_{action}`. The subsequent canonical write is logged in `backend/app/services/canonical_record_service.py:185, 209`. |
| chatbot answer - patient | Yes | `backend/app/api/v1/patients.py:223` | Logged via `rag_query`. |
| chatbot answer - policy | Yes | `backend/app/routers/policy_chatbot.py:47` | Logged via `policy_rag_query`. |
| report generation | No | N/A | Feature does not exist in the codebase. |

## 2. Story Modules Coverage

| Module | Endpoint / Action | Currently Logged? | File:Line | Notes |
| :--- | :--- | :--- | :--- | :--- |
| dashboards | `GET /dashboards/department` | Yes | `backend/app/api/dashboards.py:33` | Logged via `department_dashboard_viewed`. |
| dashboards | `GET /dashboards/hospital` | Yes | `backend/app/api/dashboards.py:52` | Logged via `hospital_dashboard_viewed`. |
| dashboards | `GET /dashboards/patient/{patient_id}` | Yes | `backend/app/api/v1/dashboards.py:99` | Logged via `patient_dashboard_viewed`. |
| exports | `POST /correction-logs/export/retraining` | Yes | `backend/app/services/correction_log_service.py:160` | PHI-safe bulk export is logged via async `correction_log_export`. |
| agent report generation | N/A | No | N/A | Not implemented. |
| policy chatbot | `POST /api/v1/policy-chat` | Yes | `backend/app/routers/policy_chatbot.py:47` | Queries are logged. |
| policy chatbot | `POST /api/v1/policy-chat/upload` | Yes | `backend/app/routers/policy_chatbot.py:135` | Ingestion of new policies is logged. |
| policy chatbot | `GET /api/v1/policy-chat/source/{filename}` | Yes | `backend/app/routers/policy_chatbot.py:82` | Policy source viewed is logged. |

## 3. Epic 8 Status (Agent-Assisted Report Generation)

A comprehensive search of the codebase (frontend and backend) for strings relating to Epic 8 (e.g. "reports/generate", "reports/export", "agent_report", "ReportRequest", "generate_report", "POST /reports") yielded **no results**. Epic 8 (agent-assisted natural-language report generation, BRD FR-28/FR-29) does **not** currently exist anywhere in this codebase.

Note: "Agent report generation" and report export (FR-28/FR-29, Epic 8) are completely unimplemented as of this story. Prompt 9 (`audit_logging_contract.md`) defines the requirements for whenever Epic 8 ships, rather than this story closing that line item.

## 4. Out of Scope Bugs Discovered

The following pre-existing bugs were discovered as a side effect of this work. They are out of scope for this story but should be filed as separate tickets:
- **Duplicate RBAC Key**: In `backend/app/core/rbac.py`, there are two entries for `"/api/v1/dashboards"`. The dictionary overwrites the first one (which included `DEPARTMENT_HEAD`), silently dropping `DEPARTMENT_HEAD` access for dashboards.
- **SQLite Concurrency with Async Tasks**: The Celery background tasks running on `AsyncSession` require an asynchronous `write_entry_async` path because the synchronous `write_entry` using `SessionLocal` causes blocking database locks on SQLite. (Addressed strictly for `correction_log_service.py` in this story).
