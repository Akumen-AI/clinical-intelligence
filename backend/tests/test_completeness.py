import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patient import Patient
from app.models.department import Department
from app.models.department_completeness_setting import DepartmentCompletenessSetting
from app.services.completeness_service import CompletenessService
from app.config.complaint_checklists import COMPLAINT_CHECKLISTS
from app.core.security import create_access_token


@pytest.mark.asyncio
async def test_t1_patient_missing_allergies_and_travel(db_session: AsyncSession):
    p = Patient(
        patient_id=str(uuid.uuid4()),
        name="John Test",
        status="active"
    )
    db_session.add(p)
    await db_session.commit()

    dept_id = uuid.uuid4()
    svc = CompletenessService(db_session)
    res = await svc.check(patient_id=p.id, complaint_type="respiratory", department_id=dept_id)

    assert res.feature_enabled is True
    missing_labels = [item.field_label for item in res.missing_fields]
    assert "Known allergies" in missing_labels
    assert "Travel history (last 30 days)" in missing_labels


@pytest.mark.asyncio
async def test_t2_patient_all_respiratory_fields_populated(db_session: AsyncSession):
    p = Patient(
        patient_id=str(uuid.uuid4()),
        name="Fully Documented",
        status="active"
    )
    setattr(p, "onset_date", "2026-09-01")
    setattr(p, "duration", "3 days")
    setattr(p, "cough_character", "Dry")
    setattr(p, "smoking_history", "Never")
    setattr(p, "occupational_exposure", "None")
    setattr(p, "travel_history", "None")
    setattr(p, "allergies", "Penicillin")
    setattr(p, "current_medications", "Multivitamin")
    setattr(p, "vaccination_history", "Up to date")

    db_session.add(p)
    await db_session.commit()

    dept_id = uuid.uuid4()
    svc = CompletenessService(db_session)
    res = await svc.check(patient_id=p.id, complaint_type="respiratory", department_id=dept_id)

    assert res.feature_enabled is True
    assert len(res.missing_fields) == 0
    assert res.total_documented == len(COMPLAINT_CHECKLISTS["respiratory"])


@pytest.mark.asyncio
async def test_t3_unknown_complaint_type_fallback_to_general(db_session: AsyncSession):
    p = Patient(patient_id=str(uuid.uuid4()), name="Unknown Complaint", status="active")
    db_session.add(p)
    await db_session.commit()

    dept_id = uuid.uuid4()
    svc = CompletenessService(db_session)
    res = await svc.check(patient_id=p.id, complaint_type="unknown_type", department_id=dept_id)

    assert res.complaint_type == "unknown_type"
    assert res.total_required == len(COMPLAINT_CHECKLISTS["general"])


@pytest.mark.asyncio
async def test_t4_department_toggle_disabled(db_session: AsyncSession):
    dept_id = uuid.uuid4()
    setting = DepartmentCompletenessSetting(
        id=uuid.uuid4(),
        department_id=str(dept_id),
        enabled=False
    )
    db_session.add(setting)
    p = Patient(patient_id=str(uuid.uuid4()), name="Disabled Dept Patient", status="active")
    db_session.add(p)
    await db_session.commit()

    svc = CompletenessService(db_session)
    res = await svc.check(patient_id=p.id, complaint_type="respiratory", department_id=dept_id)

    assert res.feature_enabled is False
    assert len(res.missing_fields) == 0
    assert res.total_required == 0


@pytest.mark.asyncio
async def test_t5_put_settings_disabled_and_check(db_session: AsyncSession, async_client):
    p_id = str(uuid.uuid4())
    dept_id = str(uuid.uuid4())
    p = Patient(patient_id=p_id, name="Integration Patient", status="active")
    db_session.add(p)
    await db_session.commit()

    admin_token = create_access_token({"sub": str(uuid.uuid4()), "role": "hospital_admin", "email": "admin@clinic.org"})
    headers = {"Authorization": f"Bearer {admin_token}"}

    resp = await async_client.put(
        f"/api/v1/completeness/settings/{dept_id}",
        json={"enabled": False},
        headers=headers
    )
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    check_resp = await async_client.post(
        f"/api/v1/completeness/check?department_id={dept_id}",
        json={"patient_id": p_id, "complaint_type": "respiratory"},
        headers=headers
    )
    assert check_resp.status_code == 200
    data = check_resp.json()
    assert data["feature_enabled"] is False
    assert len(data["missing_fields"]) == 0


def test_t6_non_admin_calling_settings_put_forbidden(client_as):
    doctor_client = client_as("doctor")
    nurse_client = client_as("nurse")
    dept_id = str(uuid.uuid4())

    resp = doctor_client.put(f"/api/v1/completeness/settings/{dept_id}", json={"enabled": False})
    assert resp.status_code == 403

    resp = nurse_client.put(f"/api/v1/completeness/settings/{dept_id}", json={"enabled": False})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_t7_doctor_role_calling_completeness_check_allowed(db_session: AsyncSession, async_client):
    p_id = str(uuid.uuid4())
    dept_id = str(uuid.uuid4())
    p = Patient(patient_id=p_id, name="Doctor Check Patient", status="active")
    db_session.add(p)
    await db_session.commit()

    token = create_access_token({"sub": str(uuid.uuid4()), "role": "doctor", "email": "doctor@clinic.org"})
    headers = {"Authorization": f"Bearer {token}"}

    resp = await async_client.post(
        f"/api/v1/completeness/check?department_id={dept_id}",
        json={"patient_id": p_id, "complaint_type": "respiratory"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature_enabled"] is True


def test_t8_validate_label_banned_phrase_diagnosis_likely():
    svc = CompletenessService(db=None)
    with pytest.raises(ValueError, match="banned phrase 'diagnosis'"):
        svc._validate_label("Diagnosis likely")


def test_t9_validate_label_banned_phrase_may_indicate_condition():
    svc = CompletenessService(db=None)
    with pytest.raises(ValueError, match="banned phrase"):
        svc._validate_label("May indicate condition")


def test_t10_all_checklist_labels_valid():
    svc = CompletenessService(db=None)
    for c_type, labels in COMPLAINT_CHECKLISTS.items():
        for label in labels:
            svc._validate_label(label)
