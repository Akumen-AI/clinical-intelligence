import json
import uuid
import sys
import os

from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal, Base, engine
from app.models.document import Document
from app.models.extraction_field import ExtractionField
from app.workers.ocr_tasks import extract_fields_task

print("==================================================")
print("     STORY 2.3 END-TO-END DEMONSTRATION RUN      ")
print("==================================================")

Base.metadata.create_all(bind=engine)

# 1. Create parent Document record in DB
doc_id = str(uuid.uuid4())
db = SessionLocal()
doc_record = Document(
    document_id=doc_id,
    filename="patient_intake_scan.pdf",
    raw_uri="uploads/patient_intake_scan.pdf",
    filetype="pdf",
    status="NEW"
)
db.add(doc_record)
db.commit()
db.close()

print(f"\n1. Created parent document in DB: {doc_id}")

# 2. Define synthetic field extraction configuration
sample_fields = [
    {
        "field_name": "patient_id",
        "raw_value": "P-88391",
        "char_confidences": [0.98, 0.96, 0.97, 0.99, 0.95, 0.98, 0.96]
    },
    {
        "field_name": "patient_name",
        "raw_value": "Alice Johnson",
        "char_confidences": [0.92, 0.94, 0.95, 0.91, 0.93, 0.96, 0.94]
    },
    {
        "field_name": "blood_pressure",
        "raw_value": "120/80",
        "char_confidences": [0.65, 0.70, 0.62, 0.68, 0.71, 0.69]
    },
    {
        "field_name": "signature_note",
        "raw_value": "",
        "char_confidences": []
    }
]

print("\n2. Executing Celery worker task (extract_fields_task):")
extracted_records = extract_fields_task(
    document_id=doc_id,
    fields_config=sample_fields
)

for r in extracted_records:
    print(f"   - Field: {r['field_name']:<16} | Value: {str(r['raw_value']):<15} | Confidence: {r['confidence']:.4f} | Status: {r['status']}")

print("\n3. Querying API GET /documents/{document_id}/fields:")
client = TestClient(app)
response = client.get(f"/documents/{doc_id}/fields")

print(f"   HTTP Response Code : {response.status_code}")
print("   API Response Payload:")
print(json.dumps(response.json(), indent=4))
print("\n==================================================")
