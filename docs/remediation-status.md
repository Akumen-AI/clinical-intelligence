# Remediation Status Baseline

## 1. Current Architecture as Actually Implemented
The repository claims to implement the SDD architecture but deviates significantly:
- Instead of separate RAG services, PostgreSQL/pgvector, and Celery workers, it is implemented as a single FastAPI application using SQLite.
- It lacks proper Docker containerization, `docker-compose.yml`, and `nginx` configurations, contrary to the SDD.
- RAG relies on JSON embeddings and in-memory Python similarity calculation rather than a true vector store.

## 2. Current Runtime Dependencies
- **Backend**: FastAPI, SQLAlchemy (both sync and async), PyMuPDF, PaddleOCR, google-genai, Ollama, pytest.
- **Frontend**: React 18, Vite 5, Tailwind CSS. (Dependencies not fully installed or locked in provided environment).
- **Missing**: Celery, Redis, PostgreSQL drivers (not active by default).

## 3. Database and Migration Model
- **Database**: SQLite by default, rather than PostgreSQL.
- **Migrations**: Alembic reports two independent heads (`007_add_dept_completeness` and `c1a2b3c4d5e6`) and multiple branchpoints. 
- The system mixes Alembic, raw SQL migrations, `create_all()`, and ad-hoc `ALTER TABLE` statements at startup, creating an unsafe migration strategy.

## 4. Authentication and Authorization Model
- **Authentication**: JWT-based, but tokens are accepted in query parameters (`?token=`) and stored in `localStorage` on the frontend. Refresh tokens are not revalidated.
- **Authorization (RBAC)**: Trusts the JWT claims directly without server-side revalidation against the database.
- **Patient-Level Access**: Inconsistent. Many routes (like `/documents`, `link-patient`, notes, completeness, and reports) only check role and fail to verify record-level access.

## 5. Document Storage Model
- **Storage**: Local filesystem (`/uploads`) rather than MinIO/S3.
- **Security**: Uploaded files are mounted as public static files via FastAPI `StaticFiles`, exposing sensitive clinical data without authentication.

## 6. Job/Background Processing Model
- **Processing**: Uses FastAPI `BackgroundTasks` instead of durable Celery workers. 
- **Issues**: Jobs run in the same web process, sharing live database sessions. Bulk uploads can starve the API, and failed jobs do not reliably reach a terminal failure state.

## 7. RAG Architecture
- **Patient RAG**: Loads all chunks and computes cosine similarity in Python. Uses Gemini directly, breaking provider-agnosticism.
- **Policy RAG**: Uses a hashed bag-of-words approach, not semantic embeddings.
- **Isolation**: Both live in the same process/database, lacking true network-level separation.
- **Grounding**: Citations are too coarse (often just document/page), and grounding guarantees are weak.

## 8. Audit Model
- **Implementation**: Performed locally in individual services rather than as a central gateway interceptor.
- **Immutability**: Retroactive updates (e.g., `backfill_patient_id_for_document`) break the append-only guarantee.
- **Coverage**: Missing in report generation and some extraction paths.

## 9. Frontend User Journeys
- **Journeys Included**: Document upload, pipeline status (polling), low-confidence review queue, patient dashboard, patient timeline, RAG Q&A.
- **Issues**: Reviewers can overwrite each other (no locking); no pagination on lists; hardcoded development URLs; naive polling that does not handle all terminal states.

## 10. Current Test/Build/Lint Status
- **Backend Compilation**: Succeeded (`python3 -m compileall`).
- **Backend Test Collection**: Succeeded (363 tests collected).
- **Frontend Build/Lint**: Failed (ESLint is invoked but not installed/configured in `package.json`).
- **Alembic**: Displays a split history with multiple heads.
- **Evaluations**: Included reports show 0% extraction accuracy on 20 synthetic handwriting samples, failing the 90% KPI.

## 11. Remediation Backlog

1. **Prompt 1**: Remove public `/uploads` access.
2. **Prompt 2**: [DONE] Eliminate query-string bearer tokens.
3. **Prompt 3**: Enforce database-backed authorization and patient-level checks on every patient/document path.
4. **Prompt 4**: Lock down `link-patient`.
5. **Prompt 5**: Fix notes/completeness/report authorization.
6. **Prompt 6**: [DONE] Remove silent invalid-role fallback.
7. **Prompt 7**: [DONE] Replace token refresh with a proper session/revocation design.
8. **Prompt 8**: Make audit truly append-only.
9. **Prompt 9**: Stop physical deletion of clinical records without retention semantics.
10. **Prompt 10**: Fix the migration system and remove startup schema mutation.
11. **Prompt 11**: Replace web-process `BackgroundTasks` with durable jobs.
12. **Prompt 12**: Make failure states explicit and observable.
13. **Prompt 13**: Resolve the handwriting pipeline quality problem.
14. **Prompt 14**: Align codebase with the actual SDD architecture.
15. **Prompt 15**: Implement scheduled reports and terminology normalization.
16. **Prompt 16**: Add proper repository hygiene (LICENSE, CI, frontend tests, linting, pinned dependencies).

## 12. Requirements Matrix

| ID | Requirement | Status |
|---|---|---|
| FR-01 | Multi-format upload/bulk | PASS (caveats: weak size/memory controls) |
| FR-02 | Scanner-folder intake | PARTIAL |
| FR-03 | Image preprocessing | PASS |
| FR-04 | Reject invalid/corrupt files | PASS |
| FR-05 | Document classification | PARTIAL |
| FR-06 | Layout detection | PARTIAL |
| FR-07 | Key field extraction | PARTIAL |
| FR-08 | Field confidence | PASS |
| FR-09 | Handwriting extraction | PARTIAL (0% accuracy on included eval) |
| FR-10 | Low-confidence verification routing | PASS |
| FR-11 | Side-by-side verification | PASS |
| FR-12 | Correction feedback logging | PARTIAL |
| FR-13 | Write-gate | PASS (caveats: classification bypass) |
| FR-14 | Canonical patient record | PARTIAL |
| FR-15 | Terminology normalization | PARTIAL (effectively not complete) |
| FR-16 | Patient timeline | PASS |
| FR-17 | Duplicate detection/reconciliation | PARTIAL |
| FR-18 | Patient NL query | PARTIAL |
| FR-19 | Patient RAG grounding/citations | PARTIAL |
| FR-20 | Patient authorization | FAIL |
| FR-21 | No-grounded-answer fallback | PARTIAL |
| FR-22 | Conversational follow-up | PARTIAL |
| FR-23 | Policy chatbot isolation | PARTIAL |
| FR-24 | Policy citations | PARTIAL |
| FR-25 | Policy re-ingestion | PASS (caveats: weak versioning) |
| FR-26 | Doctor dashboard | PASS |
| FR-27 | Department/hospital dashboards | PARTIAL |
| FR-28 | Natural-language reports | PARTIAL |
| FR-29 | Scheduled + on-demand export | FAIL |
| FR-30 | RBAC across modules | FAIL |
| FR-31 | AI action audit logging | PARTIAL |
| FR-32 | Proactive context surfacing | PASS |
| FR-33 | Documentation completeness | PASS |
| FR-34 | No diagnosis/treatment suggestions | PARTIAL |
| FR-35 | Level 2/3 prototype | FUTURE / OK |
