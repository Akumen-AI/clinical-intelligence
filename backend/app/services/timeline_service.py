from typing import Optional, List
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.extracted_field import ExtractedField
from app.schemas.timeline import PatientTimelineResponse, TimelineEventSchema


def build_patient_timeline(
    patient_id: Optional[str], db: Session
) -> PatientTimelineResponse:
    """
    Build an auto-generated chronological patient timeline from all committed documents.
    Reads canonical patient records where field_name is 'document_date'.
    """
    # Query canonical records joined with Document and optional ExtractedField
    query = (
        db.query(CanonicalPatientRecord, Document, ExtractedField)
        .join(Document, CanonicalPatientRecord.document_id == Document.document_id)
        .outerjoin(ExtractedField, CanonicalPatientRecord.source_field_id == ExtractedField.field_id)
        .filter(
            CanonicalPatientRecord.field_name == "document_date",
            Document.status == DocumentStatus.COMMITTED.value,
        )
    )

    if patient_id:
        query = query.filter(Document.patient_id == patient_id)

    results = query.all()

    events: List[TimelineEventSchema] = []

    for canonical, doc, field in results:
        raw_val = canonical.value
        if raw_val is None:
            continue

        if isinstance(raw_val, dict):
            # Extract string value if nested in dict
            event_date = str(raw_val.get("date") or raw_val.get("value") or list(raw_val.values())[0])
        else:
            event_date = str(raw_val).strip()

        if not event_date:
            continue

        doc_type = doc.document_type or "Unknown"
        summary = f"{doc_type} — {doc.filename}"

        confidence = field.confidence_score if field and field.confidence_score is not None else 1.0
        status = field.verification_status if field and field.verification_status else "auto_passed"

        events.append(
            TimelineEventSchema(
                event_id=f"{doc.document_id}:document_date",
                patient_id=doc.patient_id,
                event_date=event_date,
                event_type=doc_type,
                summary=summary,
                document_id=doc.document_id,
                filename=doc.filename,
                document_type=doc.document_type,
                source_field_name="document_date",
                confidence_score=confidence,
                verification_status=status,
            )
        )

    # Sort ascending by event_date (lexicographic ISO string sort)
    events.sort(key=lambda e: e.event_date)

    return PatientTimelineResponse(
        patient_id=patient_id,
        total_events=len(events),
        events=events,
    )
