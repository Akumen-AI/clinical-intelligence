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

# Ensure tables exist
Base.metadata.create_all(bind=engine)

SYNTHETIC_PATIENTS = [
    {"mrn": "MRN-1001", "name": "John Doe", "dob": "1980-05-12", "sex": "Male"},
    {"mrn": "MRN-1002", "name": "Jane Smith", "dob": "1992-08-24", "sex": "Female"},
    {"mrn": "MRN-1003", "name": "Alice Johnson", "dob": "1975-11-03", "sex": "Female"},
    {"mrn": "MRN-1004", "name": "Bob Williams", "dob": "1960-02-17", "sex": "Male"},
    {"mrn": "MRN-1005", "name": "Charlie Brown", "dob": "2000-07-09", "sex": "Male"},
    {"mrn": "MRN-1006", "name": "Diana Prince", "dob": "1985-04-20", "sex": "Female"},
    {"mrn": "MRN-1007", "name": "Edward Elric", "dob": "1999-02-03", "sex": "Male"},
    {"mrn": "MRN-1008", "name": "Fiona Gallagher", "dob": "1990-12-11", "sex": "Female"},
    {"mrn": "MRN-1009", "name": "George Washington", "dob": "1955-06-06", "sex": "Male"},
    {"mrn": "MRN-1010", "name": "Hannah Abbott", "dob": "1988-09-30", "sex": "Female"},
    {"mrn": "MRN-1011", "name": "Ian Malcolm", "dob": "1972-03-15", "sex": "Male"},
    {"mrn": "MRN-1012", "name": "Julia Child", "dob": "1965-08-14", "sex": "Female"}
]

def seed_patients():
    db: Session = SessionLocal()
    try:
        inserted_count = 0
        skipped_count = 0

        for patient_data in SYNTHETIC_PATIENTS:
            # Check if patient with this MRN already exists
            existing = db.query(Patient).filter(Patient.mrn == patient_data["mrn"]).first()
            if existing:
                print(f"Skipping {patient_data['name']} (MRN: {patient_data['mrn']}) - already exists.")
                skipped_count += 1
                continue

            # Generate a nice-looking custom UUID starting with P
            custom_id = f"P{str(uuid.uuid4())[1:]}"
            
            new_patient = Patient(
                patient_id=custom_id,
                mrn=patient_data["mrn"],
                name=patient_data["name"],
                dob=patient_data["dob"],
                sex=patient_data["sex"]
            )
            db.add(new_patient)
            inserted_count += 1

        db.commit()
        print(f"\nSeed Complete! Inserted: {inserted_count}, Skipped: {skipped_count}")
        
        # Verify
        total = db.query(Patient).count()
        print(f"Total patients in database: {total}")
        
    except Exception as e:
        print(f"Error seeding patients: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting patient seeding...")
    seed_patients()
