# AI Clinical Intelligence Platform

An enterprise-grade clinical document intake, computer vision preprocessing, dual-engine OCR, multimodal handwriting recognition, LLM-based classification, and structured clinical field extraction platform. Built with **FastAPI** (backend) and **React + Vite** (frontend).

---

## 🌟 Key Capabilities

- **Document Intake & Multi-Layer Validation**  
  Accepts single or bulk document uploads (`PDF`, `PNG`, `JPG`, `JPEG`, `TIFF`, up to 20 MB). Validates file signatures, MIME types, file sizes, and corruption before processing. Maintains an audit trail of all accepted and rejected attempts in an `UploadLog` table.

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
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── upload.py                  # Document intake, status polling, audit logs, deletion
│   │   │   ├── fields.py                  # Extracted clinical field retrieval & manual extraction
│   │   │   └── layout.py                  # Layout region detection endpoints
│   │   ├── services/
│   │   │   ├── upload_service.py          # Pipeline orchestration & background tasks
│   │   │   ├── validation_service.py      # File validation & audit logging
│   │   │   ├── preprocessing_service.py   # OpenCV deskewing, denoising, CLAHE contrast
│   │   │   ├── text_extraction_service.py # PyMuPDF & PaddleOCR text extraction
│   │   │   ├── confidence_engine.py       # Multi-factor confidence calibration
│   │   │   ├── field_extraction_service.py# Structured entity extraction & persistence
│   │   │   ├── layout_detection_service.py# Layout bounding box detection
│   │   │   ├── layout_trigger.py          # Layout pipeline hooks
│   │   │   ├── classification/
│   │   │   │   ├── base.py                # Classifier interface & prompts
│   │   │   │   ├── factory.py             # LLM provider factory with auto-fallback
│   │   │   │   ├── ollama_classifier.py   # Local Ollama classification
│   │   │   │   └── gemini_classifier.py   # Cloud Gemini classification
│   │   │   ├── extraction/
│   │   │   │   ├── base.py                # Base entity extractor
│   │   │   │   ├── factory.py             # Extraction engine factory
│   │   │   │   ├── rule_based_extractor.py# Deterministic regex & pattern extractors
│   │   │   │   ├── ollama_extractor.py    # LLM-based field extractor (Ollama)
│   │   │   │   └── gemini_extractor.py    # LLM-based field extractor (Gemini)
│   │   │   └── handwriting/
│   │   │       ├── base.py                # Handwriting extractor interface
│   │   │       ├── factory.py             # Handwriting provider factory
│   │   │       ├── gemini_handwriting_extractor.py # Multimodal vision handwriting engine
│   │   │       └── routing.py             # Heuristic routing based on OCR confidence
│   │   ├── models/
│   │   │   ├── document.py                # Document record model
│   │   │   ├── extracted_field.py         # Extracted clinical field model & confidence index
│   │   │   ├── layout_region.py           # Layout region bounding box model
│   │   │   └── upload_log.py              # Upload audit trail model
│   │   ├── schemas/
│   │   │   ├── upload.py                  # Document & upload response schemas
│   │   │   ├── extracted_field.py         # Standardized clinical fields schema
│   │   │   └── layout.py                  # Layout response schema
│   │   ├── utils/
│   │   │   └── validators.py              # Low-level file validation & magic byte checks
│   │   ├── static/
│   │   │   └── index.html                 # Standalone web UI fallback
│   │   ├── config.py                      # Application settings & environment variables
│   │   ├── database.py                    # SQLite engine & session management
│   │   └── main.py                        # FastAPI application entry point & CORS configuration
│   ├── tests/                             # Pytest test suite
│   │   ├── conftest.py
│   │   ├── test_upload.py
│   │   ├── test_validation.py
│   │   ├── test_classification.py
│   │   ├── test_confidence_scoring.py
│   │   ├── test_field_extraction.py
│   │   ├── test_handwriting_routing.py
│   │   ├── test_illegible_mapping.py
│   │   ├── test_json_parser.py
│   │   ├── test_layout_detection.py
│   │   └── test_eval_accuracy.py
│   ├── uploads/                           # Local storage for uploaded files (gitignored)
│   └── requirements.txt                   # Backend dependencies
│
├── frontend/                              # React + Vite Dashboard
│   ├── src/
│   │   ├── components/
│   │   │   ├── FileUploader.jsx           # Drag-and-drop file upload with validation
│   │   │   └── ExtractedFieldsModal.jsx   # Clinical fields inspector with confidence meters
│   │   ├── pages/
│   │   │   └── UploadPage.jsx             # Document management & status dashboard
│   │   ├── services/
│   │   │   └── api.js                     # Backend API client
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css                      # Modern dark/light design system styling
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
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
| **Frontend SPA** | React 18, Vite 5, Lucide Icons, Axios |
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

The backend will be available at **http://localhost:8000**.

| URL | Description |
|---|---|
| [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger API documentation |
| [http://localhost:8000/redoc](http://localhost:8000/redoc) | ReDoc API specification |
| [http://localhost:8000/ui](http://localhost:8000/ui) | Built-in standalone web interface |

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

### 3. Running Backend Tests

Run the full automated test suite with pytest:

```bash
cd backend
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
PYTHONPATH=. pytest tests/ -v
```

---

## ⚙️ Configuration

Configure backend settings via environment variables or a `backend/.env` file:

| Variable | Type | Default | Description |
|---|---|---|---|
| `AI_PROVIDER` | `string` | `ollama` | Primary AI provider: `ollama` or `gemini`. |
| `GEMINI_API_KEY` | `string` | `""` | Google Gemini API key. Required for handwriting recognition or when `AI_PROVIDER=gemini`. |
| `OLLAMA_MODEL` | `string` | `qwen3:4b` | Ollama model identifier to use for classification and extraction. |
| `DOCUMENT_CLASSIFICATION_THRESHOLD` | `float` | `0.80` | Confidence threshold below which documents are flagged for manual review (`needs_manual_review = true`). |
| `OLLAMA_TIMEOUT` | `int` | `120` | Read timeout (in seconds) for Ollama HTTP API requests. |
| `OCR_PAGE_TIMEOUT` | `int` | `120` | Maximum timeout (in seconds) per page for the PaddleOCR subprocess worker. |
| `HANDWRITING_EXTRACTION_ENABLED` | `bool` | `true` | Enables or disables the multimodal handwriting extraction route. |
| `HANDWRITING_OCR_CONFIDENCE_THRESHOLD` | `float` | `0.85` | Per-fragment OCR score below which text is marked as low confidence. |
| `HANDWRITING_LOW_CONFIDENCE_PROPORTION` | `float` | `0.15` | Minimum ratio of low-confidence fragments that triggers handwriting routing. |
| `HANDWRITING_CONSECUTIVE_LOW_CONFIDENCE_COUNT` | `int` | `3` | Number of consecutive low-confidence fragments that triggers handwriting routing regardless of total page proportion. |

---

## 📡 API Reference

All document routes are served under `/api/v1/documents`.

### Document Intake & Management

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/documents/upload` | Upload one or more documents (PDF, PNG, JPG, JPEG, TIFF; max 20 MB). Initiates background processing. |
| `GET` | `/api/v1/documents` | List all uploaded documents with metadata, classification results, and status. |
| `GET` | `/api/v1/documents/{document_id}` | Retrieve metadata and pipeline status for a specific document by UUID. |
| `GET` | `/api/v1/documents/{document_id}/status` | Poll the current processing status of a document. |
| `GET` | `/api/v1/documents/upload-logs` | Retrieve the intake audit trail (accepted and rejected attempts). |
| `DELETE` | `/api/v1/documents/{document_id}` | Delete a document record and purge its files from storage. |
| `DELETE` | `/api/v1/documents` | Purge all documents and clear the uploads storage directory. |

### Clinical Field Extraction & Layout

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/v1/documents/{document_id}/fields` | Retrieve extracted clinical fields (demographics, vitals, medications, diagnoses, dates, physician, labs). Supports `?min_confidence=` and `?max_confidence=` filters. |
| `POST` | `/api/v1/documents/{document_id}/extract` | Manually trigger or re-run clinical field extraction for a document. |
| `GET` | `/api/v1/documents/{document_id}/layout` | Retrieve detected layout bounding box regions for a document. |

---

## 📋 Extracted Clinical Entities

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
