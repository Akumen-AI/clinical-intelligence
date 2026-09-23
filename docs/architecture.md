# Architecture

The Clinical Intelligence Platform is designed with a modern, decoupled architecture centered around FastAPI, Celery, and React.

## System Components

- **Frontend Application (React/Vite)**
  - Single-page application providing document ingestion, review queue, and clinical dashboard interfaces.
  
- **Backend API (FastAPI)**
  - Handles authentication, REST endpoints, and orchestration of the document pipeline.
  - Relies on SQLite for relational data storage and Alembic for schema migrations.
  - Interacts with local or cloud-based LLM providers (Ollama / Gemini).

- **Asynchronous Task Queue (Celery + Redis)**
  - Background processing for document ingestion (`document_tasks.py`).
  - Scheduled jobs and background folder monitoring.
  
- **Document Processing Pipeline**
  - **Preprocessing**: OpenCV and PyMuPDF.
  - **OCR**: PyMuPDF for digital text and PaddleOCR for scanned content.
  - **Handwriting Extraction**: Multimodal vision via Google Gemini.
  - **Classification/Extraction**: Local Ollama LLM with cloud fallback.

## Retrieval-Augmented Generation (RAG)
- Uses FAISS for in-memory vector storage and similarity search.
- **Policy RAG**: Grounded question-answering over hospital policies.
- **Patient RAG**: Q&A restricted to a specific patient's clinical history.
