"""Additive SQLAlchemy hook for pre-extraction layout detection."""

from sqlalchemy import event
from sqlalchemy.orm import Session

from app.services.layout_detection_service import _run_layout_detection_after_preprocessing


@event.listens_for(Session, "before_commit")
def _capture_preprocessed_documents(session: Session) -> None:
    document_ids = session.info.setdefault("layout_preprocessed_document_ids", set())
    for obj in session.dirty:
        if getattr(obj, "status", None) == "preprocessed" and getattr(obj, "processed_uri", None):
            document_ids.add(obj.document_id)


@event.listens_for(Session, "after_commit")
def _detect_layout_after_commit(session: Session) -> None:
    document_ids = session.info.pop("layout_preprocessed_document_ids", set())
    print(f"DEBUG _detect_layout_after_commit: {document_ids}")
    if document_ids:
        # The preprocessing commit happens immediately before the existing
        # upload pipeline starts OCR. Complete layout detection here so OCR
        # cannot begin until regions have been persisted.
        _run_layout_detection_safely(list(document_ids), session.get_bind())


def _run_layout_detection_safely(document_ids, bind) -> None:
    try:
        _run_layout_detection_after_preprocessing(document_ids, bind)
    except Exception as exc:
        # This is an optional post-processing feature. Never let a model,
        # dependency, or database error turn a completed commit into a
        # failure in the existing upload pipeline.
        print(f"[Layout Detection] Post-commit hook failed: {exc}")
