"""
Dev database seed script to populate users with patient_access permissions.
"""
import uuid
from app.database import SessionLocal, engine, Base
from app.models.user import User, UserRole

# Ensure tables exist
Base.metadata.create_all(bind=engine)


def seed_dev_users():
    session = SessionLocal()
    try:
        sample_patient_id_1 = str(uuid.uuid4())
        sample_patient_id_2 = str(uuid.uuid4())

        # Admin user (no restriction)
        admin = session.query(User).filter(User.role == "admin").first()
        if not admin:
            admin = User(
                id=uuid.uuid4(),
                email="admin@clinic.org",
                role=UserRole.admin,
                patient_access=[],
            )
            session.add(admin)

        # Doctor user with specific patient access
        doctor = session.query(User).filter(User.role == "doctor").first()
        if not doctor:
            doctor = User(
                id=uuid.uuid4(),
                email="doctor@clinic.org",
                role=UserRole.doctor,
                patient_access=[sample_patient_id_1, sample_patient_id_2],
            )
            session.add(doctor)
        else:
            doctor.patient_access = [sample_patient_id_1, sample_patient_id_2]

        # Reviewer user with specific patient access
        reviewer = session.query(User).filter(User.role == "reviewer").first()
        if not reviewer:
            reviewer = User(
                id=uuid.uuid4(),
                email="reviewer@clinic.org",
                role=UserRole.reviewer,
                patient_access=[sample_patient_id_1],
            )
            session.add(reviewer)
        else:
            reviewer.patient_access = [sample_patient_id_1]

        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed_dev_users()
    print("Dev users seeded with patient_access successfully.")
