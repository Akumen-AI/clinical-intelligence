import os
from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app = Celery(
    "clinical_platform",
    broker=broker_url,
    backend=result_backend,
    include=["app.tasks.routing_tasks", "app.tasks.correction_export", "app.tasks.duplicate_scan", "app.tasks.document_tasks", "app.tasks.rag_tasks", "app.tasks.report_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_always_eager=True,  # Added to allow local execution without Redis
)

from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "scan-watched-folder-every-30-seconds": {
        "task": "tasks.scan_watched_folder_task",
        "schedule": 30.0,
    },
    "run-scheduled-reports-every-minute": {
        "task": "tasks.run_scheduled_reports",
        "schedule": 60.0,
    },
}
