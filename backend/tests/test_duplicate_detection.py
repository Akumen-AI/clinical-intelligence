import uuid
import pytest
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.models.patient import Patient
from app.models.user import User, UserRole
from app.models.patient_duplicate_flag import PatientDuplicateFlag
from app.models.document import Document
from app.models.visit import Visit
from app.models.note import Note
from app.models.clinical_entities import Medication, Diagnosis, LabResult, Vital, Procedure
from app.models.audit_log import AuditLogEntry
from app.services.duplicate_detection import DuplicateDetectionService, normalize_name
from app.tasks.duplicate_scan import scan_duplicates_task


def test_normalize_name():
    assert normalize_name("John A. Doe") == "a doe john"
    assert normalize_name("DOE, JOHN") == "doe john"
    assert normalize_name(None) == ""


@pytest.mark.asyncio
async def test_duplicate_detection_scan(db_session: AsyncSession):
    # Patient A & B: Similar names, exact DOB, matching MRN prefix
    p_a = Patient(
        patient_id=str(uuid.uuid4()),
        name="Johnathan A. Doe",
        dob="1980-01-15",
        mrn="MRN12345678",
        status="active"
    )
    p_b = Patient(
        patient_id=str(uuid.uuid4()),
        name="Johnathan Doe",
        dob="1980-01-15",
        mrn="MRN12399999",  # First 6 chars match: MRN123
        status="active"
    )
    # Patient C: Different name & DOB
    p_c = Patient(
        patient_id=str(uuid.uuid4()),
        name="Alice Smith",
        dob="1992-05-20",
        mrn="MRN99999999",
        status="active"
    )
    db_session.add_all([p_a, p_b, p_c])
    await db_session.commit()

    service = DuplicateDetectionService()
    flags = await service.scan_all_patients(db_session)

    assert len(flags) == 1
    flag = flags[0]
    assert flag.status == "pending"
    assert flag.similarity_score >= 0.80
    assert "name" in flag.match_reasons
    assert "dob" in flag.match_reasons
    assert "partial_id" in flag.match_reasons
    pair = {str(flag.patient_a_id), str(flag.patient_b_id)}
    assert pair == {str(p_a.id), str(p_b.id)}

    # Scan again: should skip creating existing pair
    second_flags = await service.scan_all_patients(db_session)
    assert len(second_flags) == 0


@pytest.mark.asyncio
async def test_merge_patients_ac3_compliance(db_session: AsyncSession):
    p_keep = Patient(
        patient_id=str(uuid.uuid4()),
        name="Robert Miller",
        dob="1975-03-10",
        mrn="MRN444111",
        status="active"
    )
    p_discard = Patient(
        patient_id=str(uuid.uuid4()),
        name="Robert A. Miller",
        dob="1975-03-10",
        mrn="MRN444222",
        status="active"
    )
    db_session.add_all([p_keep, p_discard])
    await db_session.commit()

    # Add associated records to discarded patient (include raw_uri and filetype for Document)
    doc = Document(document_id=str(uuid.uuid4()), filename="test.pdf", raw_uri="uploads/test.pdf", filetype="application/pdf", patient_id=str(p_discard.id))
    visit = Visit(visit_id=str(uuid.uuid4()), patient_id=str(p_discard.id))
    note = Note(id=uuid.uuid4(), patient_id=p_discard.id, author_id=uuid.uuid4(), author_role="doctor", content="Note content")
    med = Medication(id=str(uuid.uuid4()), patient_id=str(p_discard.id), source_field_id=str(uuid.uuid4()), raw_text="Aspirin 81mg")
    
    # AC-3 Check: Add a Diagnosis for p_discard to ensure it is NEVER touched or modified
    diag_id = str(uuid.uuid4())
    diag = Diagnosis(id=diag_id, patient_id=str(p_discard.id), source_field_id=str(uuid.uuid4()), raw_text="Hypertension")

    db_session.add_all([doc, visit, note, med, diag])
    await db_session.commit()

    # Create flag
    flag = PatientDuplicateFlag(
        id=uuid.uuid4(),
        patient_a_id=p_keep.id,
        patient_b_id=p_discard.id,
        similarity_score=0.88,
        match_reasons=["name", "dob"],
        status="pending"
    )
    db_session.add(flag)
    await db_session.commit()

    # Execute merge
    admin_user = User(id=uuid.uuid4(), email="admin@clinic.org", role=UserRole.HOSPITAL_ADMIN)
    service = DuplicateDetectionService()
    merged_patient = await service.merge_patients(
        db=db_session,
        flag_id=flag.id,
        keep_patient_id=p_keep.id,
        current_user=admin_user
    )

    assert str(merged_patient.id) == str(p_keep.id)

    # Verify reassignment
    await db_session.refresh(doc)
    await db_session.refresh(visit)
    await db_session.refresh(note)
    await db_session.refresh(med)
    assert str(doc.patient_id) == str(p_keep.id)
    assert str(visit.patient_id) == str(p_keep.id)
    assert str(note.patient_id) == str(p_keep.id)
    assert str(med.patient_id) == str(p_keep.id)

    # AC-3 Invariant: Diagnosis table record MUST remain untouched for p_discard
    diag_db = (await db_session.execute(select(Diagnosis).where(Diagnosis.id == diag_id))).scalar_one_or_none()
    assert diag_db is not None
    assert str(diag_db.patient_id) == str(p_discard.id)  # Diagnosis was NOT reassigned/touched!

    # Verify flag and discarded patient status
    await db_session.refresh(flag)
    await db_session.refresh(p_discard)
    assert flag.status == "merged"
    assert str(flag.merged_into_id) == str(p_keep.id)
    assert p_discard.status == "merged"
    assert str(p_discard.duplicate_of) == str(p_keep.id)

    # Verify audit log
    audit_res = await db_session.execute(select(AuditLogEntry).where(AuditLogEntry.action_type == "patient_merge"))
    audit_log = audit_res.scalar_one_or_none()
    assert audit_log is not None
    assert str(audit_log.patient_id) == str(p_keep.id)


@pytest.mark.asyncio
async def test_ignore_flag(db_session: AsyncSession):
    flag = PatientDuplicateFlag(
        id=uuid.uuid4(),
        patient_a_id=uuid.uuid4(),
        patient_b_id=uuid.uuid4(),
        similarity_score=0.82,
        match_reasons=["name"],
        status="pending"
    )
    db_session.add(flag)
    await db_session.commit()

    admin_user = User(id=uuid.uuid4(), email="admin@clinic.org", role=UserRole.HOSPITAL_ADMIN)
    service = DuplicateDetectionService()
    updated_flag = await service.ignore_flag(db_session, flag.id, admin_user)

    assert updated_flag.status == "ignored"
    assert str(updated_flag.resolved_by) == str(admin_user.id)
    assert updated_flag.resolved_at is not None


def test_api_duplicates_queue_and_rbac(client_as):
    # Nurse / Doctor can GET queue
    doctor_client = client_as("doctor")
    resp = doctor_client.get("/api/v1/duplicates")
    assert resp.status_code == 200

    nurse_client = client_as("nurse")
    resp = nurse_client.get("/api/v1/duplicates")
    assert resp.status_code == 200

    # Doctor / Nurse CANNOT call merge, ignore, or scan (403)
    dummy_flag_id = str(uuid.uuid4())
    dummy_keep_id = str(uuid.uuid4())

    resp = doctor_client.post(f"/api/v1/duplicates/{dummy_flag_id}/merge", json={"keep_patient_id": dummy_keep_id})
    assert resp.status_code == 403

    resp = doctor_client.post(f"/api/v1/duplicates/{dummy_flag_id}/ignore")
    assert resp.status_code == 403

    resp = doctor_client.post("/api/v1/duplicates/scan")
    assert resp.status_code == 403

    # Admin CAN call merge, ignore, scan
    admin_client = client_as("hospital_admin")
    resp = admin_client.post("/api/v1/duplicates/scan")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "created_flags_count" in data
