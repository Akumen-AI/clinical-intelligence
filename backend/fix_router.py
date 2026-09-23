import re

with open("app/services/confidence_router.py", "r") as f:
    content = f.read()

# Modify route_extraction_result to include the gate
replace_route = """
        document = db.query(Document).filter(Document.document_id == document_id).first()
        
        # Document-Level Trust Gate
        # If classification is uncertain, route EVERYTHING to pending review.
        trust_gate_passed = True
        if document:
            doc_type = (document.document_type or "").lower()
            if doc_type == "unknown":
                trust_gate_passed = False
            elif document.classification_confidence is not None and document.classification_confidence < threshold:
                trust_gate_passed = False
        
        if document and not document.patient_id:"""

content = re.sub(
    r'\n\s*document = db.query\(Document\).filter\(Document.document_id == document_id\).first\(\)\n\s*if document and not document.patient_id:',
    replace_route,
    content
)

replace_loop = """            # Inclusive check: confidence >= threshold -> canonical record
            if confidence >= threshold and trust_gate_passed:
                canonical_record_service.upsert_field("""

content = re.sub(
    r'\s*# Inclusive check: confidence >= threshold -> canonical record\n\s*if confidence >= threshold:\n\s*canonical_record_service.upsert_field\(',
    replace_loop,
    content
)

with open("app/services/confidence_router.py", "w") as f:
    f.write(content)
