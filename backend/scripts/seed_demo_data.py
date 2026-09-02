import os
import sys
import uuid
import random
from datetime import datetime

# Ensure backend root directory is in python search path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base
from app.models.patient import Patient
from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.models.clinical_entities import Diagnosis, Medication, LabResult, Vital, Procedure, Allergy
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.rag_chunk import PatientRAGChunk
from app.models.user import User
from app.models.audit_log import AuditLogEntry

# Ensure tables exist
Base.metadata.create_all(bind=engine)

def generate_uuid():
    return str(uuid.uuid4())

def get_iso_date(year, month, day):
    return f"{year:04d}-{month:02d}-{day:02d}"

SYNTHETIC_PATIENTS = [
    {
        "mrn": "MRN-2001", "name": "Meena Pillai", "dob": "1978-02-11", "sex": "Female",
        "note": "Patient presents for routine follow-up. Diagnosed with Type 2 Diabetes Mellitus. Patient was previously on Glimepiride 2mg but this was switched to Metformin monotherapy after GI intolerance. Discontinuation of Glimepiride occurred around visit 2. Currently on Metformin 500mg. Recent HbA1c shows improvement.",
        "documents": [
            {
                "date": "2025-08-10", "type": "Clinical Note",
                "diagnoses": [{"text": "Type 2 Diabetes Mellitus", "code": "E11.9"}],
                "medications": [{"text": "Metformin 500mg", "code": "860975", "status": "active"}],
                "labs": [{"text": "HbA1c: 9.1%", "test_name": "HbA1c", "value": 9.1, "unit": "%", "code": "4548-4", "flag": "High"}]
            },
            {
                "date": "2025-10-15", "type": "Clinical Note",
                "medications": [{"text": "Glimepiride 2mg", "code": "310340", "status": "discontinued", "reason": "Switched to Metformin monotherapy after GI intolerance", "disc_date": "2025-10-15"}],
                "labs": [{"text": "HbA1c: 7.8%", "test_name": "HbA1c", "value": 7.8, "unit": "%", "code": "4548-4", "flag": "High"}]
            },
            {
                "date": "2026-02-20", "type": "Clinical Note",
                "labs": [{"text": "HbA1c: 7.2%", "test_name": "HbA1c", "value": 7.2, "unit": "%", "code": "4548-4", "flag": "Normal"}]
            },
            {
                "date": "2026-05-12", "type": "Clinical Note",
                "labs": [{"text": "HbA1c: 6.9%", "test_name": "HbA1c", "value": 6.9, "unit": "%", "code": "4548-4", "flag": "Normal"}]
            },
            {
                "date": "2026-08-01", "type": "Clinical Note",
                "labs": [{"text": "HbA1c: 6.7%", "test_name": "HbA1c", "value": 6.7, "unit": "%", "code": "4548-4", "flag": "Normal"}]
            }
        ]
    },
    {
        "mrn": "MRN-2002", "name": "Thomas Varghese", "dob": "1965-07-30", "sex": "Male",
        "note": "Patient with Essential Hypertension. Blood pressure has been managed with Lisinopril 10mg. However, serial labs show declining renal function narrative, with creatinine rising over the past 9 months.",
        "documents": [
            {
                "date": "2025-11-15", "type": "Clinical Note",
                "diagnoses": [{"text": "Essential Hypertension", "code": "I10"}],
                "medications": [{"text": "Lisinopril 10mg", "code": "314076", "status": "active"}],
                "allergies": [{"text": "Penicillin", "allergen": "Penicillin", "reaction": "Rash", "severity": "moderate"}],
                "labs": [{"text": "Creatinine: 0.9 mg/dL", "test_name": "Creatinine", "value": 0.9, "unit": "mg/dL", "code": "2160-0", "flag": "Normal"}]
            },
            {
                "date": "2026-02-10", "type": "Clinical Note",
                "labs": [{"text": "Creatinine: 1.1 mg/dL", "test_name": "Creatinine", "value": 1.1, "unit": "mg/dL", "code": "2160-0", "flag": "Normal"}]
            },
            {
                "date": "2026-05-05", "type": "Clinical Note",
                "labs": [{"text": "Creatinine: 1.4 mg/dL", "test_name": "Creatinine", "value": 1.4, "unit": "mg/dL", "code": "2160-0", "flag": "High"}]
            },
            {
                "date": "2026-08-20", "type": "Clinical Note",
                "labs": [{"text": "Creatinine: 1.6 mg/dL", "test_name": "Creatinine", "value": 1.6, "unit": "mg/dL", "code": "2160-0", "flag": "High"}]
            }
        ]
    },
    {
        "mrn": "MRN-2003", "name": "Aleyamma Jacob", "dob": "1990-11-05", "sex": "Female",
        "note": "Asthma patient on Albuterol and Fluticasone inhalers. Peak flow measurements fluctuate but generally stable.",
        "documents": [
            {
                "date": "2026-01-10", "type": "Clinical Note",
                "diagnoses": [{"text": "Asthma", "code": "J45.909"}],
                "medications": [
                    {"text": "Albuterol inhaler", "code": "745679", "status": "active"},
                    {"text": "Fluticasone inhaler", "code": "352362", "status": "active"}
                ],
                "allergies": [{"text": "Sulfa drugs", "allergen": "Sulfa drugs", "reaction": "Hives", "severity": "moderate"}],
                "labs": [{"text": "Peak Flow: 310 L/min", "test_name": "Peak Flow", "value": 310, "unit": "L/min", "code": "19935-6", "flag": "Normal"}]
            },
            {
                "date": "2026-03-22", "type": "Clinical Note",
                "labs": [{"text": "Peak Flow: 280 L/min", "test_name": "Peak Flow", "value": 280, "unit": "L/min", "code": "19935-6", "flag": "Abnormal"}]
            },
            {
                "date": "2026-06-15", "type": "Clinical Note",
                "labs": [{"text": "Peak Flow: 350 L/min", "test_name": "Peak Flow", "value": 350, "unit": "L/min", "code": "19935-6", "flag": "Normal"}]
            },
            {
                "date": "2026-08-30", "type": "Clinical Note",
                "labs": [{"text": "Peak Flow: 365 L/min", "test_name": "Peak Flow", "value": 365, "unit": "L/min", "code": "19935-6", "flag": "Normal"}]
            }
        ]
    },
    {
        "mrn": "MRN-2004", "name": "Rajeev Menon", "dob": "1958-04-18", "sex": "Male",
        "note": "Status post total knee replacement on 2026-07-01. Oxycodone discontinued post-op course completed. Currently on Naproxen for physical therapy.",
        "documents": [
            {
                "date": "2026-07-01", "type": "Admission Form",
                "procedures": [{"text": "Total Knee Arthroplasty, Right", "code": "0SRD0JZ", "date": "2026-07-01"}],
                "medications": [{"text": "Oxycodone 5mg", "code": "161", "status": "active"}]
            },
            {
                "date": "2026-07-05", "type": "Discharge Summary",
                "medications": [{"text": "Naproxen 250mg", "code": "748797", "status": "active"}]
            },
            {
                "date": "2026-07-15", "type": "Referral",
                "medications": [{"text": "Oxycodone 5mg", "code": "161", "status": "discontinued", "reason": "Post-op course completed", "disc_date": "2026-07-15"}]
            }
        ]
    },
    {
        "mrn": "MRN-2005", "name": "Kunjamma Thomas", "dob": "1949-09-02", "sex": "Female",
        "note": "Complex patient with CHF, CKD stage 3, and Type 2 Diabetes. Frequent monitoring reveals declining eGFR and rising HbA1c.",
        "documents": [
            {
                "date": "2025-06-10", "type": "Clinical Note",
                "diagnoses": [
                    {"text": "CHF", "code": "I50.9"},
                    {"text": "CKD stage 3", "code": "N18.3"},
                    {"text": "Type 2 Diabetes", "code": "E11.9"}
                ],
                "allergies": [
                    {"text": "Aspirin", "allergen": "Aspirin", "reaction": "GI bleed", "severity": "moderate"},
                    {"text": "Contrast dye", "allergen": "Contrast dye", "reaction": "Anaphylaxis", "severity": "severe"}
                ],
                "medications": [
                    {"text": "Furosemide 40mg", "code": "315966", "status": "active"},
                    {"text": "Lantus", "code": "274783", "status": "active"}
                ],
                "labs": [
                    {"text": "HbA1c: 6.8%", "test_name": "HbA1c", "value": 6.8, "unit": "%", "code": "4548-4", "flag": "Normal"},
                    {"text": "eGFR: 65", "test_name": "eGFR", "value": 65, "unit": "mL/min", "code": "62238-1", "flag": "Normal"}
                ]
            },
            {
                "date": "2025-09-12", "type": "Clinical Note",
                "labs": [
                    {"text": "HbA1c: 7.0%", "test_name": "HbA1c", "value": 7.0, "unit": "%", "code": "4548-4", "flag": "High"},
                    {"text": "eGFR: 60", "test_name": "eGFR", "value": 60, "unit": "mL/min", "code": "62238-1", "flag": "Normal"}
                ]
            },
            {
                "date": "2025-12-15", "type": "Clinical Note",
                "labs": [
                    {"text": "HbA1c: 7.2%", "test_name": "HbA1c", "value": 7.2, "unit": "%", "code": "4548-4", "flag": "High"},
                    {"text": "eGFR: 55", "test_name": "eGFR", "value": 55, "unit": "mL/min", "code": "62238-1", "flag": "Abnormal"}
                ]
            },
            {
                "date": "2026-03-20", "type": "Clinical Note",
                "labs": [
                    {"text": "HbA1c: 7.4%", "test_name": "HbA1c", "value": 7.4, "unit": "%", "code": "4548-4", "flag": "High"},
                    {"text": "eGFR: 50", "test_name": "eGFR", "value": 50, "unit": "mL/min", "code": "62238-1", "flag": "Abnormal"}
                ]
            },
            {
                "date": "2026-06-25", "type": "Clinical Note",
                "medications": [
                    {"text": "Lisinopril", "code": "314076", "status": "discontinued", "reason": "Worsening renal function", "disc_date": "2026-06-25"},
                    {"text": "Amlodipine 5mg", "code": "197361", "status": "active"}
                ],
                "labs": [
                    {"text": "HbA1c: 7.6%", "test_name": "HbA1c", "value": 7.6, "unit": "%", "code": "4548-4", "flag": "High"},
                    {"text": "eGFR: 48", "test_name": "eGFR", "value": 48, "unit": "mL/min", "code": "62238-1", "flag": "High"}
                ]
            },
            {
                "date": "2026-08-30", "type": "Clinical Note",
                "medications": [] # Just a visit
            }
        ]
    },
    {
        "mrn": "MRN-2006", "name": "Sara K. Abraham", "dob": "1988-03-14", "sex": "Female",
        "note": "Patient presents for general wellness check. No major concerns.",
        "documents": [
            {
                "date": "2026-08-10", "type": "Clinical Note",
                "diagnoses": [{"text": "Vitamin D Deficiency", "code": "E55.9"}]
            }
        ]
    },
    {
        "mrn": "MRN-2007", "name": "Sara Abraham", "dob": "1988-03-14", "sex": "Female",
        "note": "Patient presents for mild back pain.",
        "documents": [
            {
                "date": "2026-08-15", "type": "Clinical Note",
                "diagnoses": [{"text": "Low back pain", "code": "M54.5"}]
            }
        ]
    },
    {
        "mrn": "MRN-2008", "name": "Neha Fernandes", "dob": "1996-01-22", "sex": "Female",
        "note": "Prenatal patient. Routine admission and referral docs generated.",
        "documents": [
            {
                "date": "2026-08-01", "type": "Admission Form",
                "diagnoses": [{"text": "Pregnancy, unspecified", "code": "Z33.1"}]
            },
            {
                "date": "2026-08-05", "type": "Referral",
                "diagnoses": []
            }
        ]
    },
    {
        "mrn": "MRN-2009", "name": "Vinod Kurian", "dob": "1972-06-09", "sex": "Male",
        "note": "Patient has existing diagnosis of GERD. Suspected ulcer under review.",
        "documents": [
            {
                "date": "2026-07-20", "type": "Clinical Note",
                "diagnoses": [{"text": "GERD", "code": "K21.9"}]
            },
            {
                "date": "2026-09-01", "type": "Clinical Note",
                "status": "PENDING_REVIEW",
                "diagnoses_unverified": [{"text": "Peptic Ulcer", "code": "K27.9"}]
            }
        ]
    },
    {
        "mrn": "MRN-2010", "name": "Priya Nair", "dob": "1983-12-30", "sex": "Female",
        "note": "Corrected record for diagnosis from initial scan.",
        "documents": [
            {
                "date": "2026-08-10", "type": "Clinical Note",
                "diagnoses": [{"text": "Hypothyroidism", "code": "E03.9", "corrected_from": "Hypertiroidism"}]
            }
        ]
    }
]

def seed_demo_data():
    random.seed(20260902)
    db: Session = SessionLocal()
    
    try:
        from app.services.rag_service import get_embedding, chunk_text
    except ImportError:
        def get_embedding(text): return [0.0] * 768
        def chunk_text(text): return [text]

    try:
        inserted_count = {"patients": 0, "documents": 0, "diagnoses": 0, "medications": 0, "meds_active": 0, "meds_discontinued": 0, "labs": 0, "allergies": 0, "audit_entries": 0}
        skipped_count = 0
        current_pt_number = 2001

        # Generate 50 high-volume randomized patients for the dashboard
        from datetime import timedelta
        disease_pool = [
            {"text": "Pneumonia", "code": "J18.9"},
            {"text": "COVID-19", "code": "U07.1"},
            {"text": "Essential Hypertension", "code": "I10"},
            {"text": "Type 2 Diabetes", "code": "E11.9"},
            {"text": "Asthma", "code": "J45.909"},
            {"text": "Migraine", "code": "G43.9"},
            {"text": "Bone Fracture", "code": "S82.8"}
        ]
        
        base_date = datetime(2026, 8, 1)
        for i in range(50):
            mrn = f"MRN-30{i:02d}"
            pt_name = f"Generated Patient {i}"
            dob = get_iso_date(random.randint(1940, 2000), random.randint(1, 12), random.randint(1, 28))
            sex = random.choice(["Male", "Female"])
            num_visits = random.randint(1, 3)
            docs = []
            
            disease = random.choice(disease_pool)
            
            for v in range(num_visits):
                v_date = base_date + timedelta(days=random.randint(0, 31))
                docs.append({
                    "date": v_date.strftime("%Y-%m-%d"),
                    "type": "Clinical Note",
                    "diagnoses": [disease] if v == 0 else [], # diagnose on first visit
                    "labs": [{"text": "Heart Rate: 80 bpm", "test_name": "Heart Rate", "value": 80 + random.randint(-10, 20), "unit": "bpm", "code": "8867-4", "flag": "Normal"}]
                })
            
            # Sort docs by date
            docs.sort(key=lambda x: x["date"])
            
            SYNTHETIC_PATIENTS.append({
                "mrn": mrn,
                "name": pt_name,
                "dob": dob,
                "sex": sex,
                "note": f"Generated patient with {disease['text']}",
                "documents": docs
            })

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
            inserted_count["patients"] += 1

            for doc_data in patient_data.get("documents", []):
                doc_id = str(uuid.uuid4())
                is_pending = doc_data.get("status") == "PENDING_REVIEW"
                doc = Document(
                    document_id=doc_id,
                    patient_id=custom_id,
                    filename=f"{doc_data['type'].replace(' ', '_').lower()}.txt",
                    raw_uri=f"s3://mock/{doc_data['type'].replace(' ', '_').lower()}.txt",
                    filetype="text/plain",
                    status=DocumentStatus.PENDING_REVIEW.value if is_pending else DocumentStatus.COMMITTED.value,
                    document_type=doc_data["type"]
                )
                db.add(doc)
                
                # Create corresponding Visit record for operations dashboard
                departments = ["Cardiology", "Neurology", "Emergency", "Orthopedics"]
                dept_index = sum(ord(c) for c in patient_data["name"]) % len(departments)
                from app.models.visit import Visit
                visit = Visit(
                    visit_id=str(uuid.uuid4()),
                    patient_id=custom_id,
                    document_id=doc_id,
                    visit_date=datetime.fromisoformat(doc_data["date"]),
                    visit_type=doc_data["type"],
                    provider_name="Dr. Smith",
                    department=departments[dept_index]
                )
                db.add(visit)
                inserted_count["documents"] += 1

                def create_entity(EntityClass, text, field_name, attr_mapping, extra_cpr=None, is_unverified=False, corrected_from=None):
                    field_id = str(uuid.uuid4())
                    
                    status = VerificationStatus.PENDING if is_unverified else VerificationStatus.AUTO_PASSED
                    if corrected_from:
                        status = VerificationStatus.HUMAN_VERIFIED
                        
                    field = ExtractedField(
                        field_id=field_id,
                        document_id=doc_id,
                        field_name=field_name,
                        raw_value=text,
                        confidence_score=0.45 if is_unverified or corrected_from else 0.95,
                        verification_status=status
                    )
                    db.add(field)

                    # Create actual entity
                    entity = EntityClass(
                        id=str(uuid.uuid4()),
                        patient_id=custom_id,
                        source_field_id=field_id,
                        raw_text=text
                    )
                    for attr, val in attr_mapping.items():
                        setattr(entity, attr, val)
                    db.add(entity)
                    
                    if corrected_from:
                        # Write correction log
                        doctor = db.query(User).filter(User.email == "doctor@demo.com").first()
                        if doctor:
                            from app.models.correction_log import CorrectionLog
                            log = CorrectionLog(
                                id=uuid.uuid4(),
                                extracted_field_id=uuid.UUID(field_id),
                                document_id=uuid.UUID(doc_id),
                                action="edit",
                                before_value=corrected_from,
                                after_value=text,
                                field_name=field_name,
                                confidence_score=0.45,
                                reviewer_id=doctor.id if isinstance(doctor.id, uuid.UUID) else uuid.UUID(doctor.id),
                                reviewer_role="doctor"
                            )
                            db.add(log)
                    
                    return field_id, entity

                # Document Date Canonical Record
                doc_date_field_id = str(uuid.uuid4())
                db.add(ExtractedField(
                    field_id=doc_date_field_id, document_id=doc_id, field_name="document_date",
                    raw_value=doc_data["date"], confidence_score=1.0, verification_status=VerificationStatus.AUTO_PASSED
                ))
                db.add(CanonicalPatientRecord(
                    record_id=str(uuid.uuid4()), document_id=doc_id,
                    source_field_id=doc_date_field_id, field_name="document_date", value=doc_data["date"]
                ))
                
                for diag in doc_data.get("diagnoses", []):
                    create_entity(Diagnosis, diag["text"], "diagnoses", {"icd10_code": diag.get("code")}, corrected_from=diag.get("corrected_from"))
                    inserted_count["diagnoses"] += 1
                    
                for diag in doc_data.get("diagnoses_unverified", []):
                    create_entity(Diagnosis, diag["text"], "diagnoses", {"icd10_code": diag.get("code")}, is_unverified=True)
                    inserted_count["diagnoses"] += 1
                
                for med in doc_data.get("medications", []):
                    attrs = {"rxnorm_code": med.get("code"), "status": med.get("status")}
                    if med.get("reason"): attrs["discontinued_reason"] = med.get("reason")
                    if med.get("disc_date"): attrs["discontinued_date"] = med.get("disc_date")
                    create_entity(Medication, med["text"], "medications", attrs)
                    inserted_count["medications"] += 1
                    if med.get("status") == "active": inserted_count["meds_active"] += 1
                    else: inserted_count["meds_discontinued"] += 1
                    
                for lab in doc_data.get("labs", []):
                    attrs = {
                        "test_name": lab.get("test_name"),
                        "value_numeric": lab.get("value"),
                        "unit": lab.get("unit"),
                        "loinc_code": lab.get("code"),
                        "flag": lab.get("flag"),
                        "recorded_at": doc_data["date"]
                    }
                    create_entity(LabResult, lab["text"], "lab_results", attrs)
                    inserted_count["labs"] += 1
                    
                for proc in doc_data.get("procedures", []):
                    attrs = {"code": proc.get("code"), "date": proc.get("date")}
                    create_entity(Procedure, proc["text"], "procedures", attrs)
                    
                for allg in doc_data.get("allergies", []):
                    attrs = {"allergen": allg.get("allergen"), "reaction": allg.get("reaction"), "severity": allg.get("severity")}
                    create_entity(Allergy, allg["text"], "allergies", attrs)
                    inserted_count["allergies"] += 1


            # Create RAG chunk for clinical note
            try:
                text = patient_data["note"]
                chunks = chunk_text(text)
                for chunk in chunks:
                    embedding = get_embedding(chunk)
                    rag_chunk = PatientRAGChunk(
                        id=str(uuid.uuid4()),
                        patient_id=custom_id,
                        source_document_id=doc_id, # Link to last doc for simplicity
                        content=chunk,
                        embedding=embedding,
                        metadata_json={"type": "clinical_note"}
                    )
                    db.add(rag_chunk)
            except Exception as e:
                print(f"Warning: Failed to create embeddings for {patient_data['name']}: {e}")

        # Sync user access
        doctor = db.query(User).filter(User.email == "doctor@demo.com").first()
        nurse = db.query(User).filter(User.email == "nurse@demo.com").first()
        if not doctor or not nurse:
            print("Warning: doctor@demo.com / nurse@demo.com not found — run `DEV_MODE=true python scripts/seed_users.py` first")
        else:
            all_pt_ids = [pt.patient_id for pt in db.query(Patient).all()]
            for u in [doctor, nurse]:
                current_access = u.patient_access or []
                for pid in all_pt_ids:
                    if pid not in current_access:
                        current_access.append(pid)
                # re-assign to trigger sqlalchemy change
                u.patient_access = list(current_access)
        
        # Write Audit Log Entries
        if inserted_count["patients"] > 0 and doctor:
            from app.services.audit_service import write_entry
            doc_uuid = doctor.id if isinstance(doctor.id, uuid.UUID) else uuid.UUID(doctor.id)
            write_entry(db, doc_uuid, "canonical_record_write", "MRN-2010 correction written.")
            write_entry(db, doc_uuid, "rag_query", "Queried why Glimepiride was discontinued for MRN-2001.")
            write_entry(db, doc_uuid, "patient_created", "Seeded demo patients.")
            inserted_count["audit_entries"] += 3

        db.commit()
        print(f"\nSeed Complete!")
        print(f"Patients: {inserted_count['patients']} inserted, {skipped_count} skipped")
        print(f"Documents: {inserted_count['documents']}")
        print(f"Diagnoses: {inserted_count['diagnoses']}")
        print(f"Medications: {inserted_count['medications']} ({inserted_count['meds_active']} active, {inserted_count['meds_discontinued']} discontinued)")
        print(f"Lab Results: {inserted_count['labs']}")
        print(f"Allergies: {inserted_count['allergies']}")
        print(f"Audit Entries: {inserted_count['audit_entries']}")
        
        print("\nNote: MRN-2006 and MRN-2007 form a near-duplicate pair for patient_matching_service.match_patient testing. (Currently not surfaced in UI/API).")
        
    except Exception as e:
        print(f"Error seeding demo data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting rich demo data seeding...")
    seed_demo_data()
