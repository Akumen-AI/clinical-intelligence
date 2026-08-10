import os
import sys

# Ensure backend root directory is in python search path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from sqlalchemy import text
from app.database import engine, Base
from app.models.document import Document
from app.models.upload_log import UploadLog
from app.models.layout_region import LayoutRegion
from app.models.extracted_field import ExtractedField
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.pending_review import PendingReview, SystemConfig
from app.api import upload
from app.api import layout
from app.api import fields
from app.routers import review
from app.services import layout_trigger
from app.services.upload_service import ensure_upload_directory_exists

# Create database tables automatically on startup
Base.metadata.create_all(bind=engine)

# Add column safety migration for existing DB files
with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE documents ADD COLUMN processing_time_ms INTEGER;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE documents RENAME COLUMN doc_type TO document_type;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE documents ADD COLUMN document_type VARCHAR(100);"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE documents ADD COLUMN classification_confidence FLOAT;"))
        conn.commit()
    except Exception:
        pass
    try:
        conn.execute(text("ALTER TABLE documents ADD COLUMN needs_manual_review BOOLEAN NOT NULL DEFAULT 0;"))
        conn.commit()
    except Exception:
        pass
    # Story 2.3: composite index for efficient low-confidence routing (Story 2.5)
    try:
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_extracted_fields_doc_confidence "
            "ON extracted_fields(document_id, confidence_score);"
        ))
        conn.commit()
    except Exception:
        pass


# Ensure upload storage folder exists
upload_dir = ensure_upload_directory_exists()

app = FastAPI(
    title="AI Clinical Intelligence Platform API",
    description="Document Intake & File Validation Module (Epic 1.1 FR-01 & Epic 1.3 FR-04)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS for frontend access
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded documents statically
app.mount("/uploads", StaticFiles(directory=upload_dir), name="uploads")

# Include routers
app.include_router(upload.router, prefix="/api/v1")
app.include_router(layout.router, prefix="/api/v1")
app.include_router(fields.router, prefix="/api/v1")
app.include_router(review.router, prefix="/api/v1")

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/ui", include_in_schema=False)
async def serve_ui():
    ui_path = os.path.join(static_dir, "index.html")
    return FileResponse(ui_path)

@app.get("/", tags=["Health Check"])
async def root():
    return {
        "platform": "AI Clinical Intelligence Platform",
        "module": "Epic 1.1 Document Intake Service",
        "status": "Healthy",
        "swagger_docs": "/docs",
        "web_ui": "/ui"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
