# API Reference

The Clinical Intelligence Platform provides a RESTful API powered by FastAPI.

For full interactive API documentation, run the application and navigate to:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Core Endpoints

### Documents (`/api/v1/documents`)
- `POST /upload` - Upload documents for processing.
- `GET /{id}` - Retrieve document metadata and status.
- `GET /{id}/fields` - Retrieve extracted clinical fields.
- `POST /{id}/extract` - Trigger or re-run clinical field extraction.

### Review Queue (`/api/v1/review`)
- `GET /pending` - Retrieve fields flagged for manual review.
- `PATCH /pending/{id}` - Approve or reject extracted fields.

### Patients (`/api/v1/patients`)
- `GET /{id}` - Retrieve canonical patient record.
- `POST /{id}/ask` - RAG-powered patient Q&A.

### Dashboards & Reporting (`/api/v1/dashboards`)
- `GET /patient/{id}` - Comprehensive clinical dashboard for a patient.
- `GET /hospital` - System-wide operations metrics.

### System (`/api/v1/health`)
- `GET /liveness` - Basic health check.
- `GET /readiness` - Database readiness check.
- `GET /queue` - Celery/Redis queue depth check.
