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
from app.services.confidence_engine import ConfidenceEngine


def _stringify_value(value: Any) -> Optional[str]:
    """Convert a raw field value to a string for confidence scoring.

    The ConfidenceEngine's Signal B (format validation) works on strings.
    Complex values (dicts, lists) are converted to a non-None sentinel so
    they register as "present" while still being testable by regex patterns.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value if value.strip() else None
    # dicts / lists — return a sentinel that satisfies non-empty checks
    return str(value) if value else None


def extract_and_persist_fields(
    db: Session,
    document: Document,
    ocr_text: Optional[str] = None,
    pre_extracted_fields: Optional[ClinicalFieldsSchema] = None,
    field_confidences: Optional[Dict[str, Any]] = None,
) -> Tuple[ClinicalFieldsSchema, List[ExtractedField]]:
    """
    Extracts key fields from document text using the configured extraction engine
    or directly persists pre-extracted fields (e.g. from multimodal vision model)
    into the database.

    Confidence scores are computed by the ConfidenceEngine at extraction time
    and stored immutably — they are NEVER recomputed on read (AC-2).
    """
    if pre_extracted_fields is not None:
        fields = pre_extracted_fields
        raw_field_confidences = field_confidences or {}
    else:
        import os
        from app.config import settings
        from app.services.text_extraction_service import extract_text_with_confidence

        file_path = document.processed_uri or document.raw_uri
        ocr_scores = []
        if ocr_text is None:
            # Prefer preprocessed file (PNG) — avoids heavy _ocr_pdf_pages on raw PDFs
            ocr_text = extract_text(document.processed_uri or document.raw_uri, document.filetype)
            if not ocr_text and document.processed_uri:
                ocr_text = extract_text(document.raw_uri, document.filetype)

        handwriting_handled = False
        if settings.HANDWRITING_EXTRACTION_ENABLED and settings.GEMINI_API_KEY:
            from app.services.handwriting.routing import should_route_to_handwriting

            if not ocr_scores:
                try:
                    _, ocr_scores = extract_text_with_confidence(file_path, document.filetype)
                except Exception:
                    ocr_scores = []

            if should_route_to_handwriting(
                ocr_scores,
                confidence_threshold=settings.HANDWRITING_OCR_CONFIDENCE_THRESHOLD,
                proportion_threshold=settings.HANDWRITING_LOW_CONFIDENCE_PROPORTION,
                consecutive_count_threshold=settings.HANDWRITING_CONSECUTIVE_LOW_CONFIDENCE_COUNT,
            ):
                try:
                    from app.services.handwriting.factory import get_handwriting_extractor

                    hw_extractor = get_handwriting_extractor()
                    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    image_abs_path = os.path.abspath(os.path.join(backend_dir, file_path))
                    hw_result = hw_extractor.extract_from_image(
                        image_abs_path,
                        document_type=document.document_type,
                    )
                    if hw_result and hw_result.fields:
                        fields = hw_result.fields
                        raw_field_confidences = hw_result.field_confidences or {}
                        handwriting_handled = True
                except Exception as e:
                    print(f"[Field Extraction] Handwriting fallback failed: {e}")

        if not handwriting_handled:
            extractor = get_field_extractor()
            result = extractor.extract(ocr_text or "", document_type=document.document_type)
            fields = result.fields
            raw_field_confidences = result.field_confidences

    # Remove any existing field records for this document
    db.query(ExtractedField).filter(ExtractedField.document_id == document.document_id).delete(
        synchronize_session=False
    )

    # Build the full field_map first (needed for Signal D cross-field consistency)
    field_mapping: Dict[str, Any] = {
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

    # Build string-valued field_map for cross-field consistency check
    field_map_for_signal_d: Dict[str, Optional[str]] = {
        k: _stringify_value(v) for k, v in field_mapping.items()
    }

    engine = ConfidenceEngine()
    records: List[ExtractedField] = []

    for field_name, value in field_mapping.items():
        field_conf = raw_field_confidences.get(field_name)
        if isinstance(field_conf, list):
            ocr_confidences = field_conf
        elif isinstance(field_conf, (int, float)):
            ocr_confidences = [float(field_conf)]
        else:
            ocr_confidences = []

        score = engine.score_field(
            field_name=field_name,
            raw_value=_stringify_value(value),
            ocr_word_confidences=ocr_confidences,
            layout_region="body",  # default; layout detection may refine this
            document_type=document.document_type or "unknown",
            field_map=field_map_for_signal_d,
            document_id=document.document_id,
        )
        record = ExtractedField(
            field_id=str(uuid.uuid4()),
            document_id=document.document_id,
            field_name=field_name,
            raw_value=value,
            confidence_score=score,
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


def get_document_fields_response(
    db: Session,
    document_id: str,
    min_confidence: Optional[float] = None,
    max_confidence: Optional[float] = None,
) -> Optional[DocumentFieldsResponseSchema]:
    """
    Retrieves and formats extracted fields for a document into a structured JSON schema
    with explicit null values for missing fields.

    Supports optional confidence-range filtering for low-confidence routing (Story 2.5).
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        return None

    query = (
        db.query(ExtractedField)
        .filter(ExtractedField.document_id == document_id)
    )
    if min_confidence is not None:
        query = query.filter(ExtractedField.confidence_score >= min_confidence)
    if max_confidence is not None:
        query = query.filter(ExtractedField.confidence_score <= max_confidence)

    records = query.order_by(ExtractedField.created_at.asc()).all()

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
