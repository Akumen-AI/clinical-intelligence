import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file before anything else
load_dotenv()

# Ensure backend root directory is in python search path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from fastapi import FastAPI, Depends
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
from app.models.correction_log import CorrectionLog
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.clinical_entities import Medication, Diagnosis, LabResult, Vital, Procedure, Allergy
from app.models.rag_chunk import PatientRAGChunk
from app.models.rag_conversation import RAGConversation
from app.models.report_request import ReportRequest
from app.models.refresh_token import RefreshToken

# Register SQLAlchemy hooks
import app.services.layout_trigger  # noqa

from app.api import upload
from app.api import layout
from app.api import fields
from app.api import timeline
from app.api import canonical_records
from app.api.reports import router as reports_router
from app.api.ops_dashboards import router as ops_dashboards_router
from app.routers import review
from app.routers.policy_chatbot import router as policy_chatbot_router
from app.api.v1.patients import router as patients_router
from app.api.v1.patient_dashboards import router as patient_dashboards_router
from app.api.v1.correction_logs import router as correction_logs_router
from app.api.v1.audit_log import router as audit_log_router
from app.api.v1.auth import router as auth_router
from app.models.patient_duplicate_flag import PatientDuplicateFlag
from app.routers.notes import router as notes_router
from app.routers.rag_context_compliance import router as rag_context_compliance_router
from app.routers.duplicates import router as duplicates_router
from app.routers.completeness import router as completeness_router
from app.core.compliance import ComplianceViolationError
from app.core.rbac import check_rbac
from app.services.upload_service import ensure_upload_directory_exists

from fastapi.responses import JSONResponse, FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
import uuid
from app.core.context import set_correlation_id
from app.core.logging_config import configure_logging
from app.core.rate_limit import limiter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import structlog

# Initialize structured logging
configure_logging()
logger = structlog.get_logger("app.main")

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        set_correlation_id(correlation_id)
        # Store in request state for convenient access if needed
        request.state.correlation_id = correlation_id
        
        # Add a simple metrics log for request duration
        import time
        start_time = time.time()
        
        try:
            response = await call_next(request)
            duration_ms = (time.time() - start_time) * 1000
            logger.info("request_completed", method=request.method, url=str(request.url), status_code=response.status_code, duration_ms=round(duration_ms, 2))
            response.headers["X-Correlation-ID"] = correlation_id
            return response
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error("request_failed", method=request.method, url=str(request.url), error=str(e), duration_ms=round(duration_ms, 2))
            raise

# Create database tables automatically on startup (Removed - use Alembic migrations instead)


# Ensure upload storage folder exists
upload_dir = ensure_upload_directory_exists()

# Ensure watched folder exists
try:
    from app.services.watched_folder_config_service import get_watched_folder_path_info
    import logging
    logger = logging.getLogger("app.main")
    watched_path, _ = get_watched_folder_path_info()
    os.makedirs(watched_path, exist_ok=True)
    logger.info(f"Verified watched folder exists at: {watched_path}")
except Exception as e:
    # If logger is not fully configured yet, print as fallback
    print(f"Failed to ensure watched folder exists: {e}")

from contextlib import asynccontextmanager
import logging
from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext

logger = logging.getLogger("app.main")

def check_schema_status():
    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)
    
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()
        head_rev = script.get_current_head()
        
        if current_rev != head_rev:
            raise RuntimeError(
                f"Database schema is not up to date! "
                f"Current revision: {current_rev}, Head revision: {head_rev}. "
                f"Please run 'alembic upgrade head'."
            )
        logger.info("Database schema validation passed (Alembic heads match).")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Validate schema at startup
    check_schema_status()
    yield

app = FastAPI(
    title="AI Clinical Intelligence Platform API",
    description="Document Intake & File Validation Module (Epic 1.1 FR-01 & Epic 1.3 FR-04)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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

app.add_middleware(CorrelationIdMiddleware)

# Include routers
app.include_router(policy_chatbot_router)
app.include_router(upload.router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(layout.router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(fields.router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(timeline.router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(canonical_records.router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(reports_router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(ops_dashboards_router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(review.router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(correction_logs_router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(audit_log_router, prefix="/api/v1/audit-log", tags=["Audit Log"], dependencies=[Depends(check_rbac)])
app.include_router(patients_router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(patient_dashboards_router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(notes_router)
app.include_router(rag_context_compliance_router)
app.include_router(duplicates_router, prefix="/api/v1", dependencies=[Depends(check_rbac)])
app.include_router(completeness_router, prefix="/api/v1", dependencies=[Depends(check_rbac)])

@app.exception_handler(ComplianceViolationError)
async def compliance_violation_handler(request, exc):
    return JSONResponse(status_code=422, content={"detail": str(exc)})

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/ui", include_in_schema=False)
async def serve_ui():
    ui_path = os.path.join(static_dir, "index.html")
    return FileResponse(ui_path)

@app.get("/api/v1/health", tags=["Health Check"])
async def health():
    return {"status": "Healthy"}

@app.get("/api/v1/health/liveness", tags=["Health Check"])
async def liveness():
    return {"status": "ok"}

@app.get("/api/v1/health/readiness", tags=["Health Check"])
async def readiness():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        logger.error("readiness_db_failure", error=str(e))
        return JSONResponse(status_code=503, content={"status": "unhealthy", "db": "failed"})
    
    return {"status": "healthy", "db": db_status}

@app.get("/api/v1/health/queue", tags=["Health Check"])
async def queue_health():
    try:
        import redis
        import os
        r = redis.Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
        # Using Celery's default queue name 'celery'
        q_len = r.llen("celery")
        return {"status": "healthy", "queue_length": q_len}
    except Exception as e:
        logger.error("queue_health_failure", error=str(e))
        return JSONResponse(status_code=503, content={"status": "unhealthy", "queue": "failed"})

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
