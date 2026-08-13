import os
import sys
import uuid
import random

# Ensure backend root directory is in python search path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.patient import Patient
from app.models.document import Document
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.models.clinical_entities import Diagnosis, Medication, LabResult, Vital
from app.models.rag_chunk import PatientRAGChunk

# Ensure tables exist
Base.metadata.create_all(bind=engine)

SYNTHETIC_PATIENTS = [
    {
        "mrn": "MRN-1001", "name": "John Doe", "dob": "1980-05-12", "sex": "Male",
        "diagnoses": [{"text": "Type 2 Diabetes Mellitus", "code": "E11.9"}],
        "medications": [{"text": "Metformin 500mg", "code": "860975"}],
        "labs": [{"text": "HbA1c: 7.2%", "code": "4548-4"}],
        "note": "Patient presents for routine checkup. Diagnosed with Type 2 Diabetes. Prescribed Metformin 500mg twice daily. Advised on diet and exercise. Last HbA1c is 7.2%."
    },
    {
        "mrn": "MRN-1002", "name": "Jane Smith", "dob": "1992-08-24", "sex": "Female",
        "diagnoses": [{"text": "Essential Hypertension", "code": "I10"}],
        "medications": [{"text": "Lisinopril 10mg", "code": "314076"}],
        "labs": [{"text": "Serum Creatinine: 0.9 mg/dL", "code": "2160-0"}],
        "note": "Patient has elevated blood pressure readings. Diagnosed with Essential Hypertension. Started on Lisinopril 10mg daily. Renal function normal with Creatinine at 0.9."
    },
    {
        "mrn": "MRN-1003", "name": "Alice Johnson", "dob": "1975-11-03", "sex": "Female",
        "diagnoses": [{"text": "Asthma", "code": "J45.909"}],
        "medications": [{"text": "Albuterol inhaler", "code": "745679"}],
        "labs": [{"text": "Peak Flow: 350 L/min", "code": "19933-1"}],
        "note": "Patient complains of shortness of breath. Diagnosed with Asthma. Provided Albuterol inhaler. Peak flow measured at 350 L/min in clinic."
    }
]

def seed_patients():
    db: Session = SessionLocal()
    try:
        from app.services.rag_service import get_embedding, chunk_text
    except ImportError:
        def get_embedding(text): return [0.0] * 768
        def chunk_text(text): return [text]
        
    try:
        inserted_count = 0
        skipped_count = 0
        current_pt_number = 1001

        for patient_data in SYNTHETIC_PATIENTS:
            existing = db.query(Patient).filter(Patient.mrn == patient_data["mrn"]).first()
            if existing:
                print(f"Skipping {patient_data['name']} (MRN: {patient_data['mrn']}) - already exists.")
                skipped_count += 1
                continue

            custom_id = f"P{str(uuid.uuid4())[1:]}"
            patient_number = f"PT-{current_pt_number}"
            current_pt_number += 1
            
            new_patient = Patient(
                patient_id=custom_id,
                patient_number=patient_number,
                mrn=patient_data["mrn"],
                name=patient_data["name"],
                dob=patient_data["dob"],
                sex=patient_data["sex"]
            )
            db.add(new_patient)

            # Create mock document (Clinical Note)
            doc_id = str(uuid.uuid4())
            doc = Document(
                document_id=doc_id,
                patient_id=custom_id,
                filename="clinical_note.txt",
                raw_uri="s3://mock/clinical_note.txt",
                filetype="text/plain",
                status="COMMITTED",
                document_type="Clinical Note"
            )
            db.add(doc)

            # Create mock fields and entities
            def create_entity(EntityClass, text, code, field_name, attr_name):
                field_id = str(uuid.uuid4())
                field = ExtractedField(
                    field_id=field_id,
                    document_id=doc_id,
                    field_name=field_name,
                    raw_value=text,
                    confidence_score=0.95,
                    verification_status=VerificationStatus.AUTO_PASSED
                )
                db.add(field)
                entity = EntityClass(
                    id=str(uuid.uuid4()),
                    patient_id=custom_id,
                    source_field_id=field_id,
                    raw_text=text
                )
                setattr(entity, attr_name, code)
                db.add(entity)

            for diag in patient_data["diagnoses"]:
                create_entity(Diagnosis, diag["text"], diag["code"], "Diagnosis", "icd10_code")
            
            for med in patient_data["medications"]:
                create_entity(Medication, med["text"], med["code"], "Medication", "rxnorm_code")
                
            for lab in patient_data["labs"]:
                create_entity(LabResult, lab["text"], lab["code"], "Lab Result", "loinc_code")

            # Create RAG chunk for clinical note
            try:
                text = patient_data["note"]
                chunks = chunk_text(text)
                for chunk in chunks:
                    embedding = get_embedding(chunk)
                    rag_chunk = PatientRAGChunk(
                        id=str(uuid.uuid4()),
                        patient_id=custom_id,
                        source_document_id=doc_id,
                        content=chunk,
                        embedding=embedding,
                        metadata_json={"type": "clinical_note"}
                    )
                    db.add(rag_chunk)
            except Exception as e:
                print(f"Warning: Failed to create embeddings for {patient_data['name']}: {e}")

            inserted_count += 1

        db.commit()
        print(f"\\nSeed Complete! Inserted: {inserted_count}, Skipped: {skipped_count}")
        
    except Exception as e:
        print(f"Error seeding patients: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting rich patient seeding...")
    seed_patients()
