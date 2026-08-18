import pytest
from uuid import uuid4
from unittest.mock import MagicMock
from app.models.user import User, UserRole
from app.services.rag.rbac_access_guard import RbacAccessGuard, AccessDeniedError

PATIENT_ID = uuid4()


def make_user(role: UserRole, patient_access: list[str] = None) -> User:
    u = MagicMock(spec=User)
    u.id = uuid4()
    u.role = role
    u.patient_access = patient_access or []
    return u


guard = RbacAccessGuard()

# ── Admin & Compliance roles ──────────────────────────────────────────────────────────────

def test_admin_always_permitted():
    """Admin may query any patient regardless of patient_access list."""
    user = make_user(UserRole.HOSPITAL_ADMIN)
    guard.assert_can_query_patient(user, PATIENT_ID)  # must not raise

def test_compliance_always_permitted():
    """Compliance may query any patient regardless of patient_access list."""
    user = make_user(UserRole.COMPLIANCE)
    guard.assert_can_query_patient(user, PATIENT_ID)  # must not raise


# ── Doctor role ─────────────────────────────────────────────────────────────

def test_doctor_permitted_when_in_access_list():
    user = make_user(UserRole.DOCTOR, patient_access=[str(PATIENT_ID)])
    guard.assert_can_query_patient(user, PATIENT_ID)  # must not raise


def test_doctor_denied_when_not_in_access_list():
    user = make_user(UserRole.DOCTOR, patient_access=[str(uuid4())])  # different patient
    with pytest.raises(AccessDeniedError):
        guard.assert_can_query_patient(user, PATIENT_ID)


def test_doctor_denied_when_access_list_empty():
    user = make_user(UserRole.DOCTOR, patient_access=[])
    with pytest.raises(AccessDeniedError):
        guard.assert_can_query_patient(user, PATIENT_ID)

def test_doctor_denied_when_patient_id_is_none():
    user = make_user(UserRole.DOCTOR, patient_access=[str(PATIENT_ID)])
    with pytest.raises(AccessDeniedError):
        guard.assert_can_query_patient(user, None)


# ── Reviewer role ───────────────────────────────────────────────────────────

def test_reviewer_permitted_when_in_access_list():
    user = make_user(UserRole.NURSE, patient_access=[str(PATIENT_ID)])
    guard.assert_can_query_patient(user, PATIENT_ID)  # must not raise


def test_reviewer_denied_when_not_in_access_list():
    user = make_user(UserRole.NURSE, patient_access=[])
    with pytest.raises(AccessDeniedError):
        guard.assert_can_query_patient(user, PATIENT_ID)


# ── Department Head ─────────────────────────────────────────────────────────────

def test_department_head_always_denied():
    user = make_user(UserRole.DEPARTMENT_HEAD)
    with pytest.raises(AccessDeniedError):
        guard.assert_can_query_patient(user, PATIENT_ID)

# ── Unknown role ─────────────────────────────────────────────────────────────

def test_unknown_role_always_denied():
    user = make_user(MagicMock())  # role not in enum
    with pytest.raises(AccessDeniedError):
        guard.assert_can_query_patient(user, PATIENT_ID)
