from fastapi import APIRouter
from app.api.v1.correction_logs import router as correction_logs_router

router = APIRouter()
router.include_router(correction_logs_router)

__all__ = ["router", "correction_logs_router"]
