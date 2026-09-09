# RBAC & Route Audit Checklist

This document serves as the single source of truth for mapping and auditing all frontend and backend routes against the System Design Document (SDD) §8.1 RBAC Role & Permission Matrix.

## Frontend Routes & Screens

The following frontend routes/screens and their RBAC role mappings are defined in `frontend/src/App.jsx` and `frontend/src/components/Sidebar.jsx`.

| Route Key | Screen/Component | Allowed Roles (per `Sidebar.jsx`) | Notes |
|---|---|---|---|
| `intake` | `UploadPage` | doctor, nurse, hospital_admin | |
| `review` | `ReviewQueuePage` | doctor, nurse, hospital_admin | |
| `canonical` | (None currently) | doctor, nurse, hospital_admin | |
| `patients` | `PatientsPage`, `TimelinePage`, `PatientQAPage` | doctor, nurse, hospital_admin | |
| `patientDashboard` | `PatientDashboardPage` | doctor, hospital_admin | |
| `dashboards` | `OperationsDashboardPage` | hospital_admin, department_head | |
| `policyChat` | `PolicyChatbot` | doctor, nurse, hospital_admin | |
| `policyUpload` | `PolicyDocumentUploader` | hospital_admin, it, compliance | **FLAG**: This key is defined in `Sidebar.jsx`'s `RBAC_MATRIX`, but is never consumed by a route or nav link. `PolicyChatbot.jsx` currently hardcodes its own array `['hospital_admin', 'it', 'compliance']` rather than using `hasAccess('policyUpload')`. |

---

## Backend Routes vs SDD Mapping

The table below enumerates every backend route, cross-referencing its current code-level RBAC protection with the intended SDD column.

| Method | Path | Module (SDD column) | Roles allowed by code today | Roles allowed by SDD §8.1 | Status | Test file(s) covering it | Frontend screen(s) |
|---|---|---|---|---|---|---|---|
| **Auth** | | | | | | | |
| POST | `/api/v1/auth/login` | N/A | None (Public) | Public | MATCH | | `LoginPage` |
| POST | `/api/v1/auth/refresh` | N/A | None (Public) | Public | MATCH | | Internal only |
| **Upload / Intake** | | | | | | | |
| POST | `/api/v1/documents/upload` | Upload | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_upload.py`, `test_validation.py` | `UploadPage` |
| GET | `/api/v1/documents` | Upload | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_upload.py` | `UploadPage` |
| GET | `/api/v1/documents/{id}` | Upload | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_upload.py` | `UploadPage` |
| GET | `/api/v1/documents/{id}/status` | Upload | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_upload.py` | `UploadPage` |
| DELETE| `/api/v1/documents/{id}` | Upload | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_upload.py` | `UploadPage` |
| DELETE| `/api/v1/documents` | Upload | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_upload.py` | `UploadPage` |
| **Verify / Review** | | | | | | | |
| POST | `/api/v1/documents/{id}/link-patient` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_link_patient.py` | `ReviewQueuePage` |
| GET | `/api/v1/documents/{id}/file` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | | `ReviewQueuePage` |
| GET | `/api/v1/layout/{id}/layout` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_layout_detection.py` | `ReviewQueuePage` |
| GET | `/api/v1/fields/{id}/fields` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_field_extraction.py` | `ReviewQueuePage` |
| POST | `/api/v1/fields/{id}/extract` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_field_extraction.py` | `ReviewQueuePage` |
| GET | `/api/v1/review/pending` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_confidence_router.py` | `ReviewQueuePage` |
| GET | `/api/v1/review/pending/{id}/context` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | | `ReviewQueuePage` |
| GET | `/api/v1/review/pending/{id}/image` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | | `ReviewQueuePage` |
| PATCH | `/api/v1/review/pending/{id}` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_confidence_router.py` | `ReviewQueuePage` |
| GET | `/api/v1/review/config/threshold` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_confidence_router.py` | `ReviewQueuePage` |
| PUT | `/api/v1/review/config/threshold` | Verify | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_confidence_router.py` | `ReviewQueuePage` |
| **Patient Record Read** | | | | | | | |
| POST | `/api/v1/patients` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_patients_api.py` | `PatientsPage` |
| GET | `/api/v1/patients` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_patients_api.py` | `PatientsPage` |
| GET | `/api/v1/patients/{id}` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_patients_api.py` | `PatientsPage` |
| PATCH | `/api/v1/patients/{id}` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_patients_api.py` | `PatientsPage` |
| GET | `/api/v1/patients/{id}/records` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_patients_api.py` | `PatientsPage` |
| GET | `/api/v1/timeline` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_timeline.py` | `TimelinePage` |
| GET | `/api/v1/timeline/{id}` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_timeline.py` | `TimelinePage` |
| GET | `/api/v1/canonical-records/{id}` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_patient_rbac_endpoints.py`| Internal |
| GET | `/api/v1/canonical-records/{id}/full` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | | Internal |
| GET | `/api/v1/context-panel/{id}` | Patient record read | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_10_1_context_panel.py`, `test_patient_rbac_endpoints.py` | `PatientDashboardPage` |
| POST | `/api/v1/notes` | Patient record read | Doctor, Nurse | Doctor, Nurse | MATCH | `test_patient_rbac_endpoints.py` | `PatientDashboardPage` |
| GET | `/api/v1/notes/{patient_id}` | Patient record read | Doctor, Nurse, Admin, Dept Head | Doctor, Nurse, Admin, Dept Head | MATCH | `test_patient_rbac_endpoints.py` | `PatientDashboardPage` |
| **Patient RAG** | | | | | | | |
| POST | `/api/v1/patients/{id}/ask` | Patient RAG | Doctor | Doctor | MATCH | `test_rag_ask.py`, `test_5_3_rbac_rag.py` | `PatientQAPage` |
| POST | `/api/v1/rag/query` | Patient RAG | **Deleted** | Doctor, Nurse, Admin | **Deleted** | | `PatientQAPage` |
| **Dashboards** | | | | | | | |
| GET | `/api/v1/dashboards/department` | Dashboards | Admin, Dept Head | Admin, Dept Head | MATCH | `test_dashboard.py` | `OperationsDashboardPage` |
| GET | `/api/v1/dashboards/hospital` | Dashboards | Admin, Dept Head | Admin, Dept Head | MATCH | `test_dashboard.py` | `OperationsDashboardPage` |
| GET | `/api/v1/dashboards/hospital/export` | Dashboards | Admin, Dept Head | Admin, Dept Head | MATCH | `test_dashboard_export.py` | `OperationsDashboardPage` |
| GET | `/api/v1/dashboards/patient/{id}` | Dashboards | Doctor, Admin | Doctor, Admin | MATCH | `test_dashboard_api.py` | `PatientDashboardPage` |
| **Policy RAG & Doc Mgmt** | | | | | | | |
| POST | `/api/v1/policy-chat` | Policy RAG | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | `test_policy_chatbot_audit.py`| `PolicyChatbot` |
| GET | `/api/v1/policy-chat/source/{id}`| Policy RAG | Doctor, Nurse, Admin | Doctor, Nurse, Admin | MATCH | | `PolicyChatbot` |
| POST | `/api/v1/policy-chat/upload` | Policy doc mgmt | Admin, IT, Compliance | Admin, IT, Compliance | MATCH | | `PolicyChatbot` |
| **Audit Logs** | | | | | | | |
| GET | `/api/v1/audit-log` | Audit log | Compliance | Compliance | MATCH | `test_audit_logging.py` | Internal / UI |
| GET | `/api/v1/audit-log/patient/{id}`| Audit log | Compliance | Compliance | MATCH | | Internal / UI |
| GET | `/api/v1/documents/upload-logs` | Audit log | Compliance | Compliance | MATCH | `test_validation.py` | `UploadPage` |
| POST | `/api/v1/correction-logs/` | Audit log | Admin, Compliance | Compliance / Admin | MATCH | `test_correction_logs.py` | Internal / UI |
| POST | `/api/v1/correction-logs/export` | Audit log | Admin, Compliance | Compliance / Admin | MATCH | | Internal / UI |
| GET | `/api/v1/correction-logs/` | Audit log | Admin, Compliance | Compliance / Admin | MATCH | `test_correction_logs.py` | Internal / UI |
| GET | `/api/v1/correction-logs/{id}` | Audit log | Admin, Compliance | Compliance / Admin | MATCH | `test_correction_logs.py` | Internal / UI |
| GET | `/api/v1/correction-logs/patient/{id}`| Audit log | Admin, Compliance | Compliance / Admin | MATCH | `test_correction_logs.py` | Internal / UI |
