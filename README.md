# AI Clinical Intelligence Platform

An enterprise-grade clinical document intake, optical character recognition (OCR), and retrieval-augmented generation (RAG) platform.

## 🚀 Epic 1.1: Document Intake Service (FR-01)

Epic 1.1 provides the entry point for patient documents entering the processing pipeline. It validates, securely stores, assigns unique document UUIDs, tracks document status (`QUEUED`), and presents hooks for downstream processing modules (Epic 1.2+ Image Preprocessing).

### 📁 Project Structure

```text
ai-clinical-intelligence-platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── upload.py        # POST /api/v1/documents/upload & GET endpoints
│   │   ├── services/
│   │   │   └── upload_service.py # Validation, UUID generation, disk storage & Epic 1.2 hook
│   │   ├── models/
│   │   │   └── document.py      # SQLAlchemy ORM Document model
│   │   ├── schemas/
│   │   │   └── upload.py        # Pydantic V2 response schemas
│   │   ├── static/
│   │   │   └── index.html       # Built-in standalone web dashboard
│   │   ├── database.py          # SQLite engine & Session manager
│   │   └── main.py              # FastAPI application entry point
│   ├── uploads/                  # Secure file storage
│   ├── tests/
│   │   └── test_upload.py       # Pytest unit & integration test suite
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── UploadPage.jsx   # Document Intake Dashboard page
│   │   ├── components/
│   │   │   └── FileUploader.jsx # Drag-and-drop uploader with validation
│   │   └── services/
│   │       └── api.js           # Axios API wrapper
│   └── package.json
│
└── README.md
```

---

## 🛠️ Quick Start

### 1. Install & Run Backend (FastAPI)
```bash
cd backend
pip install -r requirements.txt
python app/main.py
```
- **Web Interface**: [http://localhost:8000/ui](http://localhost:8000/ui)
- **API Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Run Test Suite
```bash
cd backend
python -m pytest tests/test_upload.py
```

---

## ⚡ Git & GitHub Setup

To push this repository to GitHub, run the following commands in your terminal from the project directory:

```bash
cd C:\Users\LENOVO\.gemini\antigravity-ide\scratch\ai-clinical-intelligence-platform
git init
git add .
git commit -m "feat(epic-1.1): implement document intake service & UI"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/ai-clinical-intelligence-platform.git
git push -u origin main
```
