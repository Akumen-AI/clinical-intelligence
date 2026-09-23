import re

with open("app/services/canonical_record_service.py", "r") as f:
    content = f.read()

# Update route_to_normalized_tables to delete all UNVERIFIED canonical entities for the document
# We can do this by finding all field_ids for this document that are not human verified.

replacement = """def clean_unverified_canonical_entities(db, document_id: str, field_name: str):
    from app.models.extracted_field import ExtractedField, VerificationStatus
    
    # Find all field IDs for this document that are NOT human verified
    unverified_field_ids = [
        f[0] for f in db.query(ExtractedField.field_id).filter(
            ExtractedField.document_id == document_id,
            ExtractedField.field_name == field_name,
            ExtractedField.verification_status != VerificationStatus.HUMAN_VERIFIED
        ).all()
    ]
    if not unverified_field_ids:
        return
        
    if field_name == "medications":
        from app.models.clinical_entities import Medication
        db.query(Medication).filter(Medication.source_field_id.in_(unverified_field_ids)).delete(synchronize_session=False)
    elif field_name in ("diagnoses", "diagnosis"):
        from app.models.clinical_entities import Diagnosis
        db.query(Diagnosis).filter(Diagnosis.source_field_id.in_(unverified_field_ids)).delete(synchronize_session=False)
    elif field_name == "allergies":
        from app.models.clinical_entities import Allergy
        db.query(Allergy).filter(Allergy.source_field_id.in_(unverified_field_ids)).delete(synchronize_session=False)
    elif field_name == "lab_results":
        from app.models.clinical_entities import LabResult
        db.query(LabResult).filter(LabResult.source_field_id.in_(unverified_field_ids)).delete(synchronize_session=False)
    elif field_name == "procedures":
        from app.models.clinical_entities import Procedure
        db.query(Procedure).filter(Procedure.source_field_id.in_(unverified_field_ids)).delete(synchronize_session=False)
    elif field_name == "vitals":
        from app.models.clinical_entities import Vital
        db.query(Vital).filter(Vital.source_field_id.in_(unverified_field_ids)).delete(synchronize_session=False)

def route_to_normalized_tables(
    db: Session,
    patient_id: str,
    field_name: str,
    field_id: str,
    final_value: Any,
    document_id: str
):
    \"\"\"Helper to route a structured value to its normalized clinical entity table.\"\"\"
    
    # Clean up previous unverified entities for idempotency across runs
    clean_unverified_canonical_entities(db, document_id, field_name)
    
    if final_value and isinstance(final_value, list):
        if field_name == "medications":
            from app.models.clinical_entities import Medication
            for item in final_value:
"""

content = re.sub(
    r'def route_to_normalized_tables\([\s\S]*?if final_value and isinstance\(final_value, list\):\n\s*if field_name == "medications":\n\s*from app.models.clinical_entities import Medication\n\s*db.query\(Medication\).filter\(Medication.source_field_id == field_id\).delete\(\)',
    replacement,
    content
)

# And similarly for the other delete() calls in route_to_normalized_tables:
content = re.sub(r'db.query\(Diagnosis\).filter\(Diagnosis.source_field_id == field_id\).delete\(\)\n', '', content)
content = re.sub(r'db.query\(Allergy\).filter\(Allergy.source_field_id == field_id\).delete\(\)\n', '', content)
content = re.sub(r'db.query\(LabResult\).filter\(LabResult.source_field_id == field_id\).delete\(\)\n\s*', '', content)
content = re.sub(r'db.query\(Procedure\).filter\(Procedure.source_field_id == field_id\).delete\(\)\n', '', content)
content = re.sub(r'db.query\(Vital\).filter\(Vital.source_field_id == field_id\).delete\(\)\n', '', content)

# update the call to route_to_normalized_tables to pass document_id
content = re.sub(
    r'route_to_normalized_tables\(db, patient_id, field.field_name, field.field_id, final_value\)',
    'route_to_normalized_tables(db, patient_id, field.field_name, field.field_id, final_value, field.document_id)',
    content
)
content = re.sub(
    r'route_to_normalized_tables\(\s*db=db,\s*patient_id=patient_id,\s*field_name=record.field_name,\s*field_id=record.source_field_id,\s*final_value=record.value,\s*\)',
    'route_to_normalized_tables(db=db, patient_id=patient_id, field_name=record.field_name, field_id=record.source_field_id, final_value=record.value, document_id=document_id)',
    content
)

# Now for upsert_field: check existing by extraction_run_id as well!
# We can do this by getting document.current_extraction_run_id
upsert_replacement = """def upsert_field(
    document_id: str,
    field_name: str,
    value: Any,
    confidence: float,
    db: Optional[Session] = None,
    human_verified: bool = False,
    actor_user_id: Optional[uuid.UUID] = None,
) -> CanonicalPatientRecord:
    \"\"\"Compatibility adapter; all persistence delegates to the verification gate.\"\"\"
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        from app.models.document import Document
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        run_id = doc.current_extraction_run_id if doc else None
        
        # Check if an earlier run produced a HUMAN_VERIFIED field. If so, do not overwrite unless forced.
        if not human_verified:
            verified_field = (
                db.query(ExtractedField)
                .filter(ExtractedField.document_id == document_id, ExtractedField.field_name == field_name, ExtractedField.verification_status == VerificationStatus.HUMAN_VERIFIED)
                .first()
            )
            if verified_field:
                logger.info(f"[CanonicalRecordService] Skipping automatic canonical write for {field_name} because a human-verified version exists.")
                return None

        field = (
            db.query(ExtractedField)
            .filter(ExtractedField.document_id == document_id, ExtractedField.field_name == field_name, ExtractedField.extraction_run_id == run_id)
            .first()
        )"""

content = re.sub(
    r'def upsert_field\([\s\S]*?\.first\(\)\n\s*\)',
    upsert_replacement,
    content
)

with open("app/services/canonical_record_service.py", "w") as f:
    f.write(content)
