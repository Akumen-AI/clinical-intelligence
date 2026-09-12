# AI Clinical Intelligence Platform

An enterprise-grade clinical document intake, computer vision preprocessing, dual-engine OCR, multimodal handwriting recognition, LLM-based classification, and structured clinical field extraction platform. Built with **FastAPI** (backend) and **React + Vite** (frontend).

---

## 🌟 Key Capabilities

- **Document Intake & Multi-Layer Validation**  
  Accepts single or bulk document uploads (`PDF`, `PNG`, `JPG`, `JPEG`, `TIFF`, up to 20 MB). Validates file signatures, MIME types, file sizes, and corruption before processing. Maintains an audit trail of all accepted and rejected attempts in an `UploadLog` table. Includes an automated **Background Folder Watcher** that continuously monitors a configured local directory for new scanned documents and ingests them directly.

- **Computer Vision Preprocessing Pipeline**  
  Automated document cleanup using OpenCV and PyMuPDF: deskewing, noise reduction, contrast enhancement (CLAHE), adaptive binarization, and multi-page PDF rendering.

- **Dual-Engine OCR & Text Extraction**  
  Extracts embedded digital text from born-digital PDFs via PyMuPDF (near-instantaneous, zero overhead). Scanned documents and image files are routed to an isolated PaddleOCR subprocess with per-page timeouts to prevent memory leaks and hangs.

- **Intelligent Handwriting Recognition & Auto-Routing**  
  Analyzes OCR fragment confidence scores to detect degraded or handwritten content (e.g., doctor handwriting, prescription slips). Automatically routes handwritten documents to a multimodal vision model (Google Gemini) for handwriting transcription, and flags illegible fields for manual review.

- **LLM-Based Document Classification**  
  Categorizes clinical records into `Prescription`, `Lab Report`, `Discharge Summary`, `Referral`, `Admission Form`, or `Unknown`. Supports local **Ollama** models (e.g., `qwen3:4b`, `llama3`) with automatic cloud fallback to **Google Gemini** if the local provider is unreachable. Documents falling below the confidence threshold are automatically flagged for manual review.

- **Structured Clinical Field Extraction & Confidence Scoring**  
  Extracts structured, standardized clinical entities including:
  - **Patient Demographics:** Name, Age/DOB, Gender, MRN/Patient ID
  - **Vital Signs:** Blood Pressure, Heart Rate, Respiratory Rate, Temperature, SpO2, Weight, Height, BMI
  - **Diagnoses:** Condition names, ICD-10 codes, clinical notes
  - **Medications:** Drug names, dosage, frequency, route, duration, instructions
  - **Clinical Dates:** Document/encounter dates, admission and discharge dates
  - **Ordering / Attending Physician:** Doctor name, license/NPI, department
  - **Lab / Test Results:** Test names, quantitative values, units, reference ranges, abnormal flags
  - Includes a multi-factor confidence scoring engine that validates formats, value ranges, and OCR quality.

- **Document Layout & Region Detection**  
  Detects and logs bounding box regions across document pages (headers, patient demographic blocks, vitals tables, medication lists, signatures).

- **Interactive Dashboard & Inspection UI**  
  React-based single-page application featuring live pipeline status tracking, upload audit logs, document management, and a clinical field inspection modal with confidence meters, status indicators, and raw JSON export.

- **Authentication & Role-Based Access Control (RBAC)**  
  Secure JWT-based authentication enforcing granular access control with distinct roles (e.g., Doctor, Nurse, Admin, IT, Compliance). Includes strict controls for patient data access tailored by user roles.

- **Comprehensive Audit Logging & Correction Tracking**  
  Centralized logging of critical actions (authentication, document uploads, patient access, configuration changes) and a correction log for tracking manual overrides to extracted clinical fields.

- **Clinical Policy Chatbot (RAG)**  
  AI-powered chatbot integrating internal policies via Retrieval-Augmented Generation (RAG) to answer operational and clinical policy queries based on the hospital's knowledge base.

---

## 🔄 Processing Pipeline

```
┌─────────────────┐
│ Document Upload │  (PDF, PNG, JPG, JPEG, TIFF)
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│ File Validation & Audit │  (Magic bytes, MIME, size check, corruption check)
└────────┬────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Computer Vision Preproc  │  (Deskew, denoise, CLAHE contrast, page rendering)
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│   OCR & Text Extraction  │  (PyMuPDF digital text + PaddleOCR subprocess)
└────────┬─────────────────┘
         │
         ├─────────────────────────────────────────┐
         │ [Low OCR Confidence / Handwriting]      │ [Standard Printed Text]
         ▼                                         │
┌──────────────────────────┐                       │
│ Multimodal Vision (Gemini│                       │
│ Handwriting & Illegible) │                       │
└────────┬─────────────────┘                       │
         │                                         │
         ├─────────────────────────────────────────┘
         ▼
┌──────────────────────────┐
│ Document Classification  │  (Ollama LLM with Gemini fallback)
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Clinical Field Extraction│  (Demographics, Vitals, Meds, Diagnoses, Labs, Dates)
└────────┬─────────────────┘
         │
         ▼
┌──────────────────────────┐
│ Confidence Calibration & │  (Field-level confidence scoring & illegible flags)
│ Persistence / Review Gating│
└──────────────────────────┘
```

---

## 📁 Project Structure

```text
clinical-intelligence/
├── alembic/                               # Database migration scripts (project root)
├── backend/
│   ├── alembic/                           # Backend-scoped Alembic migrations
│   ├── app/
│   │   ├── api/                           # API Route Definitions
│   │   │   ├── v1/                        # V1 endpoints (Auth, Audit, Patients, etc.)
│   │   │   │   ├── auth.py                # JWT authentication & login
│   │   │   │   ├── audit_log.py           # Comprehensive system audit trails
│   │   │   │   ├── dashboards.py          # Clinical dashboard composition & analytics
│   │   │   │   ├── patients.py            # Patient record access with RBAC
│   │   │   │   └── correction_logs.py     # Manual field correction history
│   │   │   ├── upload.py                  # Document intake & status
│   │   │   ├── fields.py                  # Clinical field extraction
│   │   │   ├── layout.py                  # Layout region detection
│   │   │   ├── timeline.py                # Patient clinical timeline endpoints
│   │   │   └── canonical_records.py       # Canonical patient record management
│   │   ├── core/                          # Core application logic
│   │   │   ├── security.py                # Password hashing & JWT token generation
│   │   │   ├── rbac.py                    # Role-Based Access Control logic
│   │   │   └── patient_access_guard.py    # Strict role-based patient data filtering
│   │   ├── db/                            # Database setup
│   │   │   ├── base.py                    # SQLAlchemy declarative base
│   │   │   └── session.py                 # Database session dependency
│   │   ├── routers/
│   │   │   ├── review.py                  # Confidence review queue CRUD endpoints
│   │   │   └── policy_chatbot.py          # RAG-powered clinical policy chatbot
│   │   ├── tasks/                         # Celery background tasks
│   │   │   ├── routing_tasks.py           # Async confidence routing
│   │   │   ├── rag_tasks.py               # RAG chunk ingestion background task
│   │   │   └── correction_export.py       # Correction log periodic exports
│   │   ├── services/                      # Business logic layer
│   │   │   ├── audit_service.py           # Centralized audit logging
│   │   │   ├── policy_rag_service.py      # Vector similarity & RAG querying
│   │   │   ├── policy_ingestion_service.py# Policy PDF chunking & embeddings
│   │   │   ├── classification/            # Document classification engines
│   │   │   ├── extraction/                # Structured data extraction engines
│   │   │   └── handwriting/               # Multimodal handwriting recognition
│   │   ├── models/                        # SQLAlchemy database models
│   │   │   ├── user.py                    # User identity & roles
│   │   │   ├── patient.py                 # Core patient demographic model
│   │   │   ├── audit_log.py               # Audit trail events
│   │   │   ├── correction_log.py          # Field correction logging
│   │   │   ├── policy_rag_chunk.py        # Vector chunks for policy chatbot
│   │   │   └── document.py                # Document tracking
│   │   ├── schemas/                       # Pydantic validation schemas
│   │   ├── celery_app.py                  # Celery worker configuration
│   │   ├── config.py                      # Environment configuration
│   │   └── main.py                        # FastAPI entry point
│   ├── eval_reports/                      # Evaluation reports
│   └── tests/                             # Pytest test suite
│
├── frontend/                              # React + Vite Dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUploader.jsx
│   │   │   ├── ExtractedFieldsModal.jsx
│   │   │   ├── DynamicJSONEditor.jsx      # Manual JSON correction modal
│   │   │   ├── PolicyChatbot.jsx          # Embedded RAG policy chat UI
│   │   │   ├── LabTrendChart.jsx          # Recharts-based clinical lab trends
│   │   │   ├── PatientHeaderBanner.jsx    # Standardized patient context header
│   │   │   └── PolicyDocumentUploader.jsx # RAG policy admin uploader
│   │   ├── pages/
│   │   │   ├── UploadPage.jsx             # Document management
│   │   │   ├── PatientsPage.jsx           # Global patient directory
│   │   │   ├── PatientDashboardPage.jsx   # Holistic patient clinical dashboard
│   │   │   ├── TimelinePage.jsx           # Patient clinical timeline visualization
│   │   │   ├── ReviewQueuePage.jsx        # Low confidence manual review queue
│   │   │   └── PatientQAPage.jsx          # Context-aware patient QA
│   │   └── services/
│   │       └── api.js                     # API client
│   └── package.json
└── README.md
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) |
| **Database & ORM** | SQLite + [SQLAlchemy 2.0](https://www.sqlalchemy.org/) |
| **Validation & Serialization** | [Pydantic V2](https://docs.pydantic.dev/latest/) |
| **Computer Vision** | [OpenCV](https://opencv.org/) (`opencv-python-headless`), [PyMuPDF](https://pymupdf.readthedocs.io/) |
| **OCR Engines** | [PaddleOCR 3.7](https://github.com/PaddlePaddle/PaddleOCR), PyMuPDF (digital text) |
| **Multimodal Vision & Handwriting** | [Google Gemini API](https://ai.google.dev/) (`google-genai`) |
| **LLM Classification & Extraction** | [Ollama](https://ollama.com/) (Local) / [Google Gemini](https://ai.google.dev/) (Cloud) |
| **Task Queue** | [Celery](https://docs.celeryq.dev/) (async confidence routing) |
| **Security & Auth** | JWT Authentication, Role-Based Access Control (RBAC) |
| **Database Migrations** | [Alembic](https://alembic.sqlalchemy.org/) |
| **Frontend SPA** | React 18, Vite 5, Tailwind CSS, Lucide Icons, Axios |
| **Testing** | Pytest, Pytest-Mock |

---

## 🛠️ Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** & **npm**
- *(Optional)* [Ollama](https://ollama.com/) running locally for on-device inference
- *(Optional)* [Google Gemini API Key](https://aistudio.google.com/) for handwriting recognition and cloud LLM fallback

---

### 1. Backend Setup

1. Navigate to the backend directory and set up a virtual environment:
   ```bash
   cd backend
   python3 -m venv .venv
   ```

2. Activate the virtual environment:
   - **macOS / Linux:**
     ```bash
     source .venv/bin/activate
     ```
   - **Windows:**
     ```cmd
     .venv\Scripts\activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in `backend/` (see [Configuration](#-configuration) below):
   ```env
   AI_PROVIDER=ollama
   GEMINI_API_KEY=your-gemini-api-key-here
   OLLAMA_MODEL=qwen3:4b
   DOCUMENT_CLASSIFICATION_THRESHOLD=0.80
   ```

5. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Demo Accounts

The platform includes a script to generate synthetic demo accounts for testing role-based access. **These are synthetic demo accounts only and should not be used in a production environment.**

Run the seed script in dev mode:
```bash
DEV_MODE=true python scripts/seed_users.py
```

The generated accounts are:
- `doctor@demo.com` (Password: `doctorPassword123!`) - Role: `doctor`
- `nurse@demo.com` (Password: `nursePassword123!`) - Role: `nurse`
- `admin@demo.com` (Password: `adminPassword123!`) - Role: `hospital_admin`
- `head@demo.com` (Password: `headPassword123!`) - Role: `department_head`
- `it@demo.com` (Password: `itPassword123!`) - Role: `it`
- `compliance@demo.com` (Password: `compliancePassword123!`) - Role: `compliance`

The backend will be available at **http://localhost:8000**.

| URL | Description |
|---|---|
| [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger API documentation |
| [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc API specification |
| [http://localhost:8000/ui](http://localhost:8000/ui) | Built-in standalone web interface |

### Demo Patient Data

The platform includes a script to seed a rich, believable clinical dataset into the database for demonstration and testing purposes. All data is purely synthetic with no real PHI, and uses a fixed random seed for reproducibility.

Run the seed script in dev mode (it will automatically seed users if needed, then seed the patient data):
```bash
DEV_MODE=true python scripts/seed_all_demo_data.py
```

This single command populates the database with the following patient roster:
- **MRN-2001, "Meena Pillai"**: Type 2 Diabetes Mellitus with a 5-point declining HbA1c trend and a medication switch (Glimepiride to Metformin) explicitly narrated in clinical notes for RAG querying.
- **MRN-2002, "Thomas Varghese"**: Essential Hypertension with a rising Creatinine lab trend indicating declining renal function.
- **MRN-2003, "Aleyamma Jacob"**: Asthma with stable Peak Flow measurements and multiple active inhalers.
- **MRN-2004, "Rajeev Menon"**: Status post total knee replacement, demonstrating post-op medication discontinuation and document type variety (Admission Form, Discharge Summary, Referral).
- **MRN-2005, "Kunjamma Thomas"**: Complex patient with CHF, CKD stage 3, and Type 2 Diabetes, featuring multiple lab trends (rising HbA1c, declining eGFR) and severe allergies.
- **MRN-2006, "Sara K. Abraham"** and **MRN-2007, "Sara Abraham"**: A near-duplicate pair testing patient matching logic.
- **MRN-2008, "Neha Fernandes"**: Prenatal patient showcasing non-standard document types (Admission Form and Referral).
- **MRN-2009, "Vinod Kurian"**: Includes a document in `PENDING_REVIEW` state to populate the Review Queue, testing verification threshold gating.
- **MRN-2010, "Priya Nair"**: Contains a human-verified correction log entry tracing a fixed OCR misread.

---

### 2. Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   npm install
   ```

2. Start the Vite development server:
   ```bash
   npm run dev
   ```

The frontend dashboard will be running at **http://localhost:5173**.

---

### 3. Running the app

During development, run both the backend and frontend dev servers simultaneously:
- Run the backend on **:8000**
- Run the frontend dev server on **:5173**

Vite proxies `/api` calls to `:8000` — the frontend dev server (`:5173`) is the one you should use day to day.

> **Note on `:8000/ui`:** This endpoint only serves whatever was last built with `npm run build` inside the `frontend/` directory. It doesn't hot-reload, and will silently go stale if not rebuilt. Treat it as a deploy-time preview, not a second app.

---

### 4. Running Backend Tests

Run the full automated test suite with pytest:

```bash
cd backend
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
PYTHONPATH=. pytest tests/ -v
```

---

## 🔐 Role-Based Access Control (RBAC)

The platform enforces strict Role-Based Access Control (RBAC) at both the API routing layer and the frontend navigation layer. All requests are authenticated via JWT tokens.

### User Roles & Capabilities
| Role | Permissions |
|---|---|
| **Doctor** | Access to document intake, review queue, canonical patient records, patient timelines, patient Q&A, and clinical policy queries. Limited to their assigned patients. |
| **Nurse** | Access to document intake, canonical patient records, and clinical policy queries. Can perform manual corrections in the review queue. Limited to their assigned patients. |
| **Hospital Admin** | System-wide visibility. Full access to document intake, review queue, canonical patient records, operations dashboards, and policy management (upload and query). |
| **Department Head** | Read-only access to aggregated department and hospital operations dashboards. |
| **IT** | System maintenance access, including uploading new hospital policies to the RAG knowledge base. |
| **Compliance** | Access to system-wide audit logs and policy management (uploading policies). |

### Patient-Level Access Guardrails
Beyond endpoint-level role protection, the system enforces **record-level access controls** for clinical roles (`Doctor`, `Nurse`). If an authenticated clinical user attempts to access a patient record, document, or RAG context panel for a patient not explicitly bound to their access list, the `RbacAccessGuard` rejects the request with a `403 Forbidden` error.

---

## ⚙️ Configuration

Configure backend settings via environment variables or a `backend/.env` file:

| Variable | Type | Default | Description |
|---|---|---|---|
| `AI_PROVIDER` | `string` | `ollama` | Primary AI provider: `ollama` or `gemini`. |
| `GEMINI_API_KEY` | `string` | `""` | Google Gemini API key. Required for handwriting recognition or when `AI_PROVIDER=gemini`. |
| `OLLAMA_MODEL` | `string` | `qwen3:4b` | Ollama model identifier to use for classification and extraction. |
| `DOCUMENT_CLASSIFICATION_THRESHOLD` | `float` | `0.80` | Confidence threshold below which documents are flagged for manual review (`needs_manual_review = true`). |
| `CONFIDENCE_THRESHOLD` | `float` | `0.80` | Field-level confidence threshold for routing extracted fields to the canonical record vs. the pending review queue. |
| `OLLAMA_TIMEOUT` | `int` | `120` | Read timeout (in seconds) for Ollama HTTP API requests. |
| `OCR_PAGE_TIMEOUT` | `int` | `120` | Maximum timeout (in seconds) per page for the PaddleOCR subprocess worker. |
| `HANDWRITING_EXTRACTION_ENABLED` | `bool` | `true` | Enables or disables the multimodal handwriting extraction route. |
| `HANDWRITING_OCR_CONFIDENCE_THRESHOLD` | `float` | `0.85` | Per-fragment OCR score below which text is marked as low confidence. |
| `HANDWRITING_LOW_CONFIDENCE_PROPORTION` | `float` | `0.15` | Minimum ratio of low-confidence fragments that triggers handwriting routing. |
| `HANDWRITING_CONSECUTIVE_LOW_CONFIDENCE_COUNT` | `int` | `3` | Number of consecutive low-confidence fragments that triggers handwriting routing regardless of total page proportion. |
| `WATCHED_FOLDER_PATH` | `string` | `./data/scanner_intake` | Local directory path for the background scanner to monitor for new incoming documents. |
| `WATCHED_FOLDER_POLL_INTERVAL_SECONDS` | `int` | `30` | Polling interval (in seconds) for the background folder watcher task. |

---

## 📡 API Reference

All document routes are served under `/api/v1/documents`.

### Document Intake & Management

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload one or more documents (PDF, PNG, JPG, JPEG, TIFF; max 20 MB). Initiates background processing. |
| `GET` | `/api/v1/documents` | List all uploaded documents. Supports `?needs_review=true/false` and `?document_type=` filters. |
| `GET` | `/api/v1/documents/{document_id}` | Retrieve metadata and pipeline status for a specific document by UUID. |
| `GET` | `/api/v1/documents/{document_id}/status` | Poll the current processing status of a document. |
| `GET` | `/api/v1/documents/upload-logs` | Retrieve the intake audit trail (accepted and rejected attempts). |
| `DELETE` | `/api/v1/documents/{document_id}` | Delete a document record and purge its files from storage. |
| `DELETE` | `/api/v1/documents` | Purge all documents and clear the uploads storage directory. |
| `GET` | `/api/v1/documents/config/watched-folder` | Retrieve active watched folder path and poll interval. |
| `PUT` | `/api/v1/documents/config/watched-folder` | Update watched folder path dynamically. (Hospital Admin only) |

### Clinical Field Extraction & Layout

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/documents/{document_id}/fields` | Retrieve extracted clinical fields (demographics, vitals, medications, diagnoses, dates, physician, labs). Supports `?min_confidence=` and `?max_confidence=` filters. |
| `POST` | `/api/v1/documents/{document_id}/extract` | Manually trigger or re-run clinical field extraction for a document. |
| `GET` | `/api/v1/documents/{document_id}/layout` | Retrieve detected layout bounding box regions for a document. |

### Confidence Review Queue

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/review/pending` | Retrieve paginated pending review fields (`status=PENDING`). |
| `PATCH` | `/api/v1/review/pending/{review_id}` | Approve or reject a field. Approving writes the field to the canonical patient record. |
| `GET` | `/api/v1/review/config/threshold` | Retrieve active confidence threshold and its source (`env` or `db`). |
| `PUT` | `/api/v1/review/config/threshold` | Update threshold dynamically (validated 0.0 < threshold ≤ 1.0), stored in the `system_config` table. |

### Security, Identity, and Auditing

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/auth/login` | Authenticate and obtain JWT token for RBAC. |
| `GET` | `/api/v1/audit-log` | Retrieve comprehensive audit logs for compliance monitoring. |
| `GET` | `/api/v1/correction_logs` | Retrieve manual correction history on clinical records. |

### Patient & Policy Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/patients/{patient_id}` | Retrieve canonical patient records (RBAC protected). |
| `GET` | `/api/v1/dashboards/{patient_id}` | Retrieve comprehensive clinical dashboard data including lab trends and active medications (RBAC protected). |
| `POST` | `/api/v1/policy-chatbot/query` | Ask clinical and operational policy questions (RAG). |

---

## 🚦 Confidence Routing

Automated routing for extracted clinical fields based on confidence scores.

### Routing Logic & Default Threshold
- **Default Threshold**: `CONFIDENCE_THRESHOLD = 0.80` (configured in `app/config.py` and `.env`).
- **Canonical Routing**: Fields with `confidence_score >= CONFIDENCE_THRESHOLD` (inclusive) flow directly to the canonical patient record (`canonical_record_service.upsert_field()`).
- **Pending Review Queue**: Fields with `confidence_score < CONFIDENCE_THRESHOLD` are automatically routed to the mandatory human-verification queue (`pending_review` table).

### Endpoints
- `GET /api/v1/review/pending`: Retrieve paginated pending review fields (`status=PENDING`).
- `PATCH /api/v1/review/pending/{review_id}`: Approve or reject a field in the review queue. Approving automatically writes the field to the canonical patient record.
- `GET /api/v1/review/config/threshold`: Retrieve active confidence threshold and its source (`env` or `db`).
- `PUT /api/v1/review/config/threshold`: Update threshold dynamically (validated $0.0 < \text{threshold} \le 1.0$) stored in the `system_config` table.

---

## 📋 Extracted Data Schema

The platform structures extracted data into a unified, typed schema:

| Entity Category | Fields Extracted |
|---|---|
| **Patient Demographics** | `patient_id` (MRN), `name`, `dob`, `gender` |
| **Vital Signs** | `blood_pressure`, `heart_rate`, `respiratory_rate`, `temperature`, `spo2`, `weight`, `height`, `bmi` |
| **Diagnoses** | `condition_name`, `icd10_code`, `notes` |
| **Medications** | `medication_name`, `dosage`, `frequency`, `route`, `duration`, `instructions` |
| **Lab Results** | `test_name`, `value`, `unit`, `reference_range`, `flag` (Normal / High / Low / Abnormal) |
| **Clinical Dates** | `document_date`, `admission_date`, `discharge_date`, `encounter_date` |
| **Physician Info** | `name`, `npi_or_license`, `department` |
| **Symptoms & Procedures**| List of documented symptoms and medical procedures performed |

---

## 🚦 Document Processing Statuses

| Status | Meaning |
|---|---|
| `QUEUED` | Document uploaded and validated; queued for background processing |
| `PREPROCESSING` | Image deskewing, denoising, and contrast enhancement in progress |
| `PREPROCESSED` | Preprocessing completed |
| `CLASSIFYING` | Document classification and OCR text extraction in progress |
| `CLASSIFIED` | Document classified by LLM / Vision model |
| `EXTRACTING` | Clinical field extraction in progress |
| `EXTRACTED` | Structured clinical fields successfully extracted and persisted |
| `pending_review` | Confidence score below threshold or illegible fields detected; flagged for human review |
| `failed` | An error occurred during processing (see `rejection_reason`) |
