# AI Clinical Intelligence Platform

An enterprise-grade clinical document intake, OCR, and retrieval-augmented generation (RAG) platform. Built with FastAPI (backend) and React + Vite (frontend).

> **Project Status:** Epic 1 — *Document Intake & Preprocessing* — is mostly complete (1.1 to 1.4).  
> Epics 2–11 are planned but not yet implemented.

---

## ✅ What's Been Built (Epic 1)

Epic 1 delivers an end-to-end pipeline that accepts clinical documents, validates them, preprocesses the images, extracts text, and classifies each document using an LLM.

| Story | Title | Description |
|-------|-------|-------------|
| **1.1** | Document Intake & Upload | Drag-and-drop upload (single or bulk) with UUID tracking, disk storage, and SQLite persistence. |
| **1.2** | Image Preprocessing | Deskew, denoise, and contrast correction (CLAHE) for uploaded images and PDF pages using OpenCV. |
| **1.3** | File Validation & Audit Logging | Extension, MIME type, file-size (< 20 MB), and corruption checks. Every accept/reject is logged to an `upload_logs` audit table. |
| **1.4** | Document Classification | Text extraction (PyMuPDF for PDFs, PaddleOCR for images) followed by LLM-based classification into Prescription, Lab Report, Discharge Summary, Referral, Admission Form, or Unknown. Supports Ollama (local) with automatic fallback to Google Gemini. |

### Processing Pipeline

```
Upload → Validate → Save to Disk → Queue
  ↓ (background)
Preprocess (deskew / denoise / contrast)
  ↓
Extract Text (PyMuPDF / PaddleOCR)
  ↓
Classify (Ollama or Gemini LLM)
  ↓
Update DB (document_type, confidence, needs_manual_review)
```

---

## 📁 Project Structure

```text
clinical-intelligence/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── upload.py                  # REST endpoints (upload, list, get, delete)
│   │   ├── services/
│   │   │   ├── upload_service.py          # Upload orchestration & background pipeline
│   │   │   ├── validation_service.py      # File validation & audit logging
│   │   │   ├── preprocessing_service.py   # Image deskew, denoise, contrast (OpenCV)
│   │   │   ├── text_extraction_service.py # PDF text & OCR extraction (PyMuPDF + PaddleOCR)
│   │   │   └── classification/
│   │   │       ├── base.py                # Abstract classifier & shared prompt
│   │   │       ├── factory.py             # Provider selection with auto-fallback
│   │   │       ├── ollama_classifier.py   # Local Ollama LLM classifier
│   │   │       └── gemini_classifier.py   # Google Gemini API classifier
│   │   ├── models/
│   │   │   ├── document.py                # SQLAlchemy Document model
│   │   │   └── upload_log.py              # SQLAlchemy UploadLog (audit trail)
│   │   ├── schemas/
│   │   │   └── upload.py                  # Pydantic V2 response schemas
│   │   ├── utils/
│   │   │   └── validators.py              # Low-level file validation helpers
│   │   ├── static/
│   │   │   └── index.html                 # Built-in standalone web UI
│   │   ├── config.py                      # Settings (AI provider, thresholds)
│   │   ├── database.py                    # SQLite engine & session manager
│   │   └── main.py                        # FastAPI application entry point
│   ├── tests/
│   │   ├── conftest.py                    # Shared fixtures
│   │   ├── test_upload.py                 # Upload endpoint tests
│   │   ├── test_validation.py             # File validation tests
│   │   └── test_classification.py         # Classification logic tests
│   ├── uploads/                           # Stored documents (gitignored)
│   └── requirements.txt
│
├── frontend/                              # React + Vite SPA
│   ├── src/
│   │   ├── pages/
│   │   │   └── UploadPage.jsx             # Document Intake dashboard page
│   │   ├── components/
│   │   │   └── FileUploader.jsx           # Drag-and-drop uploader component
│   │   ├── services/
│   │   │   └── api.js                     # Axios API wrapper
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── README.md
```

---

## 🛠️ Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the frontend)
- *(Optional)* [Ollama](https://ollama.com/) running locally for on-device classification
- *(Optional)* A Google Gemini API key as a cloud fallback

### 1. Backend (FastAPI)

**Mac / Linux:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Windows:**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The backend starts at **http://localhost:8000**.

| URL | Description |
|-----|-------------|
| [http://localhost:8000/ui](http://localhost:8000/ui) | Built-in web UI |
| [http://localhost:8000/docs](http://localhost:8000/docs) | Swagger / OpenAPI docs |
| [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc API reference |

### 2. Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

The frontend dev server starts at **http://localhost:5173** and proxies API calls to the backend.

### 3. Run Tests

```bash
cd backend
source .venv/bin/activate        # or .venv\Scripts\activate on Windows
PYTHONPATH=. pytest tests/ -v
```

---

## ⚙️ Environment Configuration

Create a `.env` file in the `backend/` directory:

```env
# AI provider: "ollama" (default) or "gemini"
AI_PROVIDER=ollama

# Required only if using Gemini (or as fallback)
GEMINI_API_KEY=your-gemini-api-key-here

# Optional: override the default Ollama model (default: qwen3:4b)
# OLLAMA_MODEL=qwen3:4b

# Optional: confidence threshold below which documents are flagged for manual review (default: 0.80)
# DOCUMENT_CLASSIFICATION_THRESHOLD=0.80
```

**LLM Provider Fallback:** When `AI_PROVIDER=ollama`, the system automatically checks if Ollama is running. If it's unreachable, it falls back to Gemini (provided `GEMINI_API_KEY` is set).

---

## 📡 API Reference

All endpoints are prefixed with `/api/v1/documents`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/upload` | Upload one or more clinical documents (PDF, PNG, JPG, JPEG, TIFF). Max 20 MB per file. |
| `GET` | `/` | List all documents with metadata, status, and classification results. |
| `GET` | `/{document_id}` | Get a single document's metadata by UUID. |
| `GET` | `/{document_id}/status` | Poll the processing pipeline status for a document. |
| `GET` | `/upload-logs` | Retrieve the audit trail of accepted and rejected upload attempts. |
| `DELETE` | `/{document_id}` | Delete a specific document (DB record + files on disk). |
| `DELETE` | `/` | Delete all documents. |

### Document Statuses

| Status | Meaning |
|--------|---------|
| `QUEUED` | File accepted, waiting for background processing |
| `preprocessed` | Image preprocessing complete |
| `classified` | LLM classification complete |
| `failed` | An error occurred during processing |
| `pending_review` | Confidence below threshold; needs manual review |

### Supported Document Types (Classification Output)

`Prescription` · `Lab Report` · `Discharge Summary` · `Referral` · `Admission Form` · `Unknown`

---

## 🧰 Tech Stack

| Layer | Technology |
|-------|------------|
| **Backend Framework** | FastAPI |
| **Database** | SQLite (via SQLAlchemy ORM) |
| **Image Processing** | OpenCV, PyMuPDF |
| **OCR** | PaddleOCR 3.7 |
| **LLM Classification** | Ollama (local) / Google Gemini (cloud) |
| **Frontend** | React 18, Vite 5, Axios |
| **Validation** | Pydantic V2 |

---

## 🗺️ Roadmap

- [ ] **Epic 1** — Document Intake & Preprocessing
  - [x] 1.1 Document Intake & Upload
  - [x] 1.2 Image Preprocessing
  - [x] 1.3 File Validation & Audit Logging
  - [x] 1.4 Document Classification (LLM)
  - [ ] 1.5 Scanner-folder intake
- [ ] **Epic 2** — CV / OCR & Handwriting Recognition Pipeline
- [ ] **Epic 3** — Human Verification & Continuous Improvement
- [ ] **Epic 4** — Canonical Patient Record & Timeline
- [ ] **Epic 5** — Patient-Scoped Clinical RAG Assistant
- [ ] **Epic 6** — Hospital Policy RAG Chatbot
- [ ] **Epic 7** — Dashboards & Reporting
- [ ] **Epic 8** — Agent-Assisted Natural-Language Report Generation
- [ ] **Epic 9** — Access Control & Audit
- [ ] **Epic 10** — Proactive Clinical Context Surfacing (Level 1 only)
- [ ] **Epic 11** — Integration, Hardening & Demo Readiness
