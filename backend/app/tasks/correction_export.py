import asyncio
from app.celery_app import celery_app
from app.services.correction_log_service import CorrectionLogService

@celery_app.task(name="correction_logs.export_retraining_batch")
def export_retraining_batch(limit: int = 1000) -> dict:
    """
    Celery-compatible wrapper for the PHI-safe export.
    Can be scheduled with celery beat (e.g. nightly).
    """
    service = CorrectionLogService()
    result = asyncio.run(_run_export(service, limit))
    return {"batch_id": result.batch_id, "exported_count": result.exported_count}

async def _run_export(service: CorrectionLogService, limit: int):
    from app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        return await service.export_for_retraining(db, limit=limit)
