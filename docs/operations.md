# Operations

## Background Processing
The platform heavily leverages asynchronous processing to ensure the API remains responsive.
- **Celery Workers**: Run computationally intensive tasks like image preprocessing, OCR, and LLM classification.
- **Redis**: Serves as the Celery message broker and distributed lock manager for idempotency constraints.

## Observability
- Logs are strictly JSON formatted using `structlog`.
- A unique `X-Correlation-ID` is generated for every request and propagates down to the Celery workers and database transactions.

## Folder Watcher
A Celery Beat scheduler continuously monitors a configured directory (default `./data/scanner_intake`) to automatically ingest raw documents dumped by network scanners. Idempotency is guaranteed via distributed Redis locks, ensuring duplicate files are skipped.
