from typing import Optional
from uuid import UUID
import structlog

from app.models.user import User, UserRole

log = structlog.get_logger(__name__)


class AccessDeniedError(Exception):
    """Raised when a user is not authorized to query a patient's data."""


class RbacAccessGuard:
    """
    Checks whether a user is authorized to retrieve data for a given patient_id.

    Rules:
      - UserRole.admin, UserRole.compliance → always permitted
      - UserRole.doctor, UserRole.nurse → permitted only if patient_id is in user.patient_access
      - UserRole.department_head → always denied
      - Any other role  → always denied
    """

    def assert_can_query_patient(self, user: User, patient_id: Optional[UUID | str] = None) -> None:
        """
        Raises AccessDeniedError if user may not query this patient.
        Returns None (implicitly) if access is permitted.
        """
        user_role = getattr(user, "role", None)
        if user_role in (UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE, "hospital_admin", "compliance"):
            return

        if user_role in (UserRole.DOCTOR, UserRole.NURSE, "doctor", "nurse"):
            if not patient_id:
                log.warning(
                    "rag.access_denied",
                    user_id=str(getattr(user, "id", "")),
                    user_role=str(user_role),
                    reason="No patient_id provided for patient-scoped view",
                )
                raise AccessDeniedError(
                    f"User {getattr(user, 'id', '')} ({user_role}) is not authorized to access global patient records"
                )

            access_list = getattr(user, "patient_access", []) or []
            if str(patient_id) in access_list:
                return

            log.warning(
                "rag.access_denied",
                user_id=str(getattr(user, "id", "")),
                user_role=str(user_role),
                patient_id=str(patient_id),
            )
            raise AccessDeniedError(
                f"User {getattr(user, 'id', '')} ({user_role}) is not authorized to access patient {patient_id}"
            )

        log.warning(
            "rag.access_denied",
            user_id=str(getattr(user, "id", "")),
            user_role=str(user_role),
            patient_id=str(patient_id),
        )
        raise AccessDeniedError(
            f"Role '{user_role}' is not permitted to use patient-scoped endpoints"
        )
