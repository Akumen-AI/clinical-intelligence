import uuid
from typing import Tuple, List, Optional, Dict, Any
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField
from app.schemas.extracted_field import (
    ClinicalFieldsSchema,
    DocumentFieldsResponseSchema,
    ExtractedFieldRecordSchema,
    PatientIdentifierSchema,
    PhysicianSchema,
    VitalsSchema,
    DiagnosisItemSchema,
    MedicationItemSchema,
    LabResultItemSchema,
)
from app.services.extraction.factory import get_field_extractor
from app.services.text_extraction_service import extract_text


def extract_and_persist_fields(
    db: Session,
    document: Document,
    ocr_text: Optional[str] = None,
) -> Tuple[ClinicalFieldsSchema, List[ExtractedField]]:
    """
    Extracts key fields from document text using the configured extraction engine
    and persists ExtractedField records into the database.
    """
    if ocr_text is None:
        ocr_text = extract_text(document.raw_uri, document.filetype)
        if not ocr_text and document.processed_uri:
            ocr_text = extract_text(document.processed_uri, document.filetype)

    extractor = get_field_extractor()
    result = extractor.extract(ocr_text or "", document_type=document.document_type)
    fields = result.fields

    # Remove any existing field records for this document
    db.query(ExtractedField).filter(ExtractedField.document_id == document.document_id).delete(
        synchronize_session=False
    )

    records: List[ExtractedField] = []
    field_mapping = {
        "patient_identifier": fields.patient_identifier.model_dump() if fields.patient_identifier else None,
        "document_date": fields.document_date,
        "ordering_physician": fields.ordering_physician.model_dump() if fields.ordering_physician else None,
        "vitals": fields.vitals.model_dump() if fields.vitals else None,
        "diagnosis": [d.model_dump() for d in fields.diagnosis] if fields.diagnosis else None,
        "medications": [m.model_dump() for m in fields.medications] if fields.medications else None,
        "lab_results": [l.model_dump() for l in fields.lab_results] if fields.lab_results else None,
        "symptoms": fields.symptoms if fields.symptoms else None,
        "procedures": fields.procedures if fields.procedures else None,
    }

    for field_name, value in field_mapping.items():
        score = result.field_confidences.get(field_name, result.confidence if value is not None else 0.0)
        record = ExtractedField(
            field_id=str(uuid.uuid4()),
            document_id=document.document_id,
            field_name=field_name,
            raw_value=value,
            confidence_score=score if value is not None else 0.0,
            verification_status="extracted",
        )
        records.append(record)

    db.add_all(records)
    target_doc = db.query(Document).filter(Document.document_id == document.document_id).first()
    if target_doc:
        target_doc.status = DocumentStatus.EXTRACTED.value
    db.commit()
    if target_doc:
        db.refresh(target_doc)

    print(f"[Field Extraction] Persisted {len(records)} fields for document {document.document_id}")
    return fields, records


def get_document_fields_response(db: Session, document_id: str) -> Optional[DocumentFieldsResponseSchema]:
    """
    Retrieves and formats extracted fields for a document into a structured JSON schema
    with explicit null values for missing fields.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        return None

    records = (
        db.query(ExtractedField)
        .filter(ExtractedField.document_id == document_id)
        .order_by(ExtractedField.created_at.asc())
        .all()
    )

    field_dict: Dict[str, Any] = {
        "patient_identifier": None,
        "document_date": None,
        "ordering_physician": None,
        "vitals": None,
        "diagnosis": None,
        "medications": None,
        "lab_results": None,
        "symptoms": None,
        "procedures": None,
    }

    for rec in records:
        if rec.raw_value is not None and rec.field_name in field_dict:
            field_dict[rec.field_name] = rec.raw_value

    structured_fields = ClinicalFieldsSchema.model_validate(field_dict)

    record_schemas = [
        ExtractedFieldRecordSchema(
            field_id=rec.field_id,
            document_id=rec.document_id,
            field_name=rec.field_name,
            raw_value=rec.raw_value,
            confidence_score=rec.confidence_score,
            bounding_box=rec.bounding_box,
            verification_status=rec.verification_status,
            verified_value=rec.verified_value,
            reviewer_id=rec.reviewer_id,
            created_at=rec.created_at,
        )
        for rec in records
    ]

    return DocumentFieldsResponseSchema(
        document_id=doc.document_id,
        document_type=doc.document_type,
        fields=structured_fields,
        field_records=record_schemas,
    )
