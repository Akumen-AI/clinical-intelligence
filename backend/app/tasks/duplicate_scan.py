import asyncio
from app.celery_app import celery_app
from app.db.session import AsyncSessionLocal
from app.services.duplicate_detection import DuplicateDetectionService


@celery_app.task(name="tasks.scan_duplicates")
def scan_duplicates_task():
    """
    Runs DuplicateDetectionService.scan_all_patients() asynchronously.
    Triggered automatically after every new verified document write
    (hook into the existing write-gate from Story 3.3).
    Also exposed as a manual admin trigger via the API (Task 5).
    """
    async def _run():
        async with AsyncSessionLocal() as session:
            service = DuplicateDetectionService()
            return await service.scan_all_patients(session)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            return asyncio.ensure_future(_run())
        else:
            return loop.run_until_complete(_run())
    except RuntimeError:
        return asyncio.run(_run())
