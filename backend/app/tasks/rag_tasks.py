import json
import logging
from app.database import SessionLocal
from app.models.document import Document
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.services.rag_service import index_document

logger = logging.getLogger("app.tasks.rag_tasks")

def index_document_task(document_id: str):
    """
    Background task to index a document for RAG after it is linked to a patient.
    Uses verified extracted fields and canonical patient records.
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            logger.error(f"[RAG Task] Document {document_id} not found")
            return
            
        if not doc.patient_id:
            logger.warning(f"[RAG Task] Document {document_id} is not linked to a patient")
            return
            
        # 1. Fetch verified fields from ExtractedField
        verified_fields = db.query(ExtractedField).filter(
            ExtractedField.document_id == document_id,
            ExtractedField.verification_status.in_([VerificationStatus.AUTO_PASSED, VerificationStatus.HUMAN_VERIFIED])
        ).all()
        
        extracted_data = {}
        for f in verified_fields:
            val = f.verified_value if f.verified_value is not None else f.raw_value
            if val is not None:
                extracted_data[f.field_name] = val
                
        # 2. Fetch from CanonicalPatientRecord
        canonical_records = db.query(CanonicalPatientRecord).filter(
            CanonicalPatientRecord.document_id == document_id
        ).all()
        
        for r in canonical_records:
            if r.field_name not in extracted_data and r.value is not None:
                extracted_data[r.field_name] = r.value
                
        # Build document text
        text_parts = []
        for k, v in extracted_data.items():
            if isinstance(v, (dict, list)):
                v_str = json.dumps(v)
            else:
                v_str = str(v)
            text_parts.append(f"{k}: {v_str}")
            
        ocr_text = "\n".join(text_parts)
        
        if ocr_text:
            index_document(db, doc, ocr_text)
        else:
            logger.warning(f"[RAG Task] No verified text found for document {document_id}")
            
    except Exception as e:
        logger.error(f"[RAG Task] Error indexing document {document_id}: {e}")
    finally:
        db.close()
