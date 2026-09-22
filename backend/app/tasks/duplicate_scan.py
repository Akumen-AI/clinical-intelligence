import asyncio
from app.celery_app import celery_app
from app.db.session import SyncSessionLocal
from app.services.duplicate_detection import DuplicateDetectionService


@celery_app.task(name="tasks.scan_duplicates")
def scan_duplicates_task():
    """
    Runs DuplicateDetectionService.scan_all_patients() asynchronously.
    Triggered automatically after every new verified document write
    (hook into the existing write-gate from Story 3.3).
    Also exposed as a manual admin trigger via the API (Task 5).
    """
    with SyncSessionLocal() as session:
        service = DuplicateDetectionService()
        return service.scan_all_patients(session)
