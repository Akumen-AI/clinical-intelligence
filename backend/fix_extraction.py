import re

with open("app/services/field_extraction_service.py", "r") as f:
    content = f.read()

# Replace the ExtractedField delete block
replace_delete = """    doc_id = document.document_id
    # Instead of deleting fields, we create a new ExtractionRun
    from app.models.extraction_run import ExtractionRun
    import os
    
    previous_run_id = document.current_extraction_run_id
    
    new_run = ExtractionRun(
        run_id=str(uuid.uuid4()),
        document_id=doc_id,
        extractor_name=os.getenv("AI_PROVIDER", "gemini_multimodal") if not pre_extracted_fields else "pre_extracted",
        extractor_version="1.0", # hardcoded for now, could be dynamic based on models
        status="completed",
        supersedes_run_id=previous_run_id
    )
    db.add(new_run)
    db.flush()
    
    document.current_extraction_run_id = new_run.run_id
    document.document_version += 1"""

content = re.sub(
    r'    doc_id = document.document_id\n    db.query\(ExtractedField\).filter\(ExtractedField.document_id == doc_id\).delete\(\n        synchronize_session=False\n    \)',
    replace_delete,
    content
)

# Replace ExtractedField instantiation to include extraction_run_id
replace_field = """        record = ExtractedField(
            field_id=str(uuid.uuid4()),
            document_id=doc_id,
            extraction_run_id=new_run.run_id,
            field_name=field_name,"""
            
content = re.sub(
    r'        record = ExtractedField\(\n            field_id=str\(uuid.uuid4\(\)\),\n            document_id=doc_id,\n            field_name=field_name,',
    replace_field,
    content
)

# Update get_document_fields_response to filter by current extraction run!
replace_get_fields = """    query = (
        db.query(ExtractedField)
        .filter(ExtractedField.document_id == document_id)
        .filter(ExtractedField.extraction_run_id == doc.current_extraction_run_id)
    )"""

content = re.sub(
    r'    query = \(\n        db.query\(ExtractedField\)\n        .filter\(ExtractedField.document_id == document_id\)\n    \)',
    replace_get_fields,
    content
)

with open("app/services/field_extraction_service.py", "w") as f:
    f.write(content)
