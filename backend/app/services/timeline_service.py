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
    """
    events: List[TimelineEventSchema] = []

    # 1. Document Date Events (from CanonicalPatientRecord)
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
        
    for canonical, doc, field in query.all():
        raw_val = canonical.value
        if not raw_val: continue
        event_date = str(raw_val.get("date") or raw_val.get("value") or list(raw_val.values())[0]) if isinstance(raw_val, dict) else str(raw_val).strip()
        if not event_date: continue

        events.append(
            TimelineEventSchema(
                event_id=f"{doc.document_id}:document_date",
                patient_id=doc.patient_id,
                event_date=event_date,
                event_type=doc.document_type or "Document",
                summary=f"Document: {doc.document_type or 'Unknown'} — {doc.filename}",
                document_id=doc.document_id,
                filename=doc.filename,
                document_type=doc.document_type,
                source_field_name="document_date",
                confidence_score=field.confidence_score if field and field.confidence_score is not None else 1.0,
                verification_status=field.verification_status if field and field.verification_status else "auto_passed",
            )
        )

    # 2. Diagnoses
    from app.models.clinical_entities import Diagnosis
    diag_query = db.query(Diagnosis, Document, ExtractedField).join(ExtractedField, Diagnosis.source_field_id == ExtractedField.field_id).join(Document, ExtractedField.document_id == Document.document_id).filter(Document.status == DocumentStatus.COMMITTED.value)
    if patient_id: diag_query = diag_query.filter(Diagnosis.patient_id == patient_id)
    for diag, doc, field in diag_query.all():
        # Fallback to document date since Diagnosis has no date
        doc_date_record = db.query(CanonicalPatientRecord).filter(CanonicalPatientRecord.document_id == doc.document_id, CanonicalPatientRecord.field_name == "document_date").first()
        event_date = str(doc_date_record.value).strip() if doc_date_record and doc_date_record.value else "Unknown"
        events.append(
            TimelineEventSchema(
                event_id=f"diag:{diag.id}",
                patient_id=diag.patient_id,
                event_date=event_date,
                event_type="Diagnosis",
                summary=f"Diagnosis: {diag.raw_text}",
                document_id=doc.document_id,
                filename=doc.filename,
                document_type=doc.document_type,
                source_field_name="diagnoses",
                confidence_score=field.confidence_score if field and field.confidence_score is not None else 1.0,
                verification_status=field.verification_status if field and field.verification_status else "auto_passed",
            )
        )

    # 3. Procedures
    from app.models.clinical_entities import Procedure
    proc_query = db.query(Procedure, Document, ExtractedField).join(ExtractedField, Procedure.source_field_id == ExtractedField.field_id).join(Document, ExtractedField.document_id == Document.document_id).filter(Document.status == DocumentStatus.COMMITTED.value)
    if patient_id: proc_query = proc_query.filter(Procedure.patient_id == patient_id)
    for proc, doc, field in proc_query.all():
        doc_date_record = db.query(CanonicalPatientRecord).filter(CanonicalPatientRecord.document_id == doc.document_id, CanonicalPatientRecord.field_name == "document_date").first()
        event_date = proc.date or (str(doc_date_record.value).strip() if doc_date_record and doc_date_record.value else "Unknown")
        events.append(
            TimelineEventSchema(
                event_id=f"proc:{proc.id}",
                patient_id=proc.patient_id,
                event_date=event_date,
                event_type="Procedure",
                summary=f"Procedure: {proc.raw_text}",
                document_id=doc.document_id,
                filename=doc.filename,
                document_type=doc.document_type,
                source_field_name="procedures",
                confidence_score=field.confidence_score if field and field.confidence_score is not None else 1.0,
                verification_status=field.verification_status if field and field.verification_status else "auto_passed",
            )
        )

    # 4. Medications
    from app.models.clinical_entities import Medication
    med_query = db.query(Medication, Document, ExtractedField).join(ExtractedField, Medication.source_field_id == ExtractedField.field_id).join(Document, ExtractedField.document_id == Document.document_id).filter(Document.status == DocumentStatus.COMMITTED.value)
    if patient_id: med_query = med_query.filter(Medication.patient_id == patient_id)
    for med, doc, field in med_query.all():
        doc_date_record = db.query(CanonicalPatientRecord).filter(CanonicalPatientRecord.document_id == doc.document_id, CanonicalPatientRecord.field_name == "document_date").first()
        event_date = str(doc_date_record.value).strip() if doc_date_record and doc_date_record.value else "Unknown"
        events.append(
            TimelineEventSchema(
                event_id=f"med:{med.id}",
                patient_id=med.patient_id,
                event_date=event_date,
                event_type="Medication",
                summary=f"Medication: {med.raw_text}",
                document_id=doc.document_id,
                filename=doc.filename,
                document_type=doc.document_type,
                source_field_name="medications",
                confidence_score=field.confidence_score if field and field.confidence_score is not None else 1.0,
                verification_status=field.verification_status if field and field.verification_status else "auto_passed",
            )
        )

    events.sort(key=lambda e: e.event_date if e.event_date != "Unknown" else "9999-99-99")

    return PatientTimelineResponse(
        patient_id=patient_id,
        total_events=len(events),
        events=events,
    )
