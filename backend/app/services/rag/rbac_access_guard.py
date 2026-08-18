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
      - UserRole.admin  → always permitted (no patient_access restriction)
      - UserRole.doctor → permitted only if patient_id is in user.patient_access
      - UserRole.reviewer → permitted only if patient_id is in user.patient_access
      - Any other role  → always denied
    """

    def assert_can_query_patient(self, user: User, patient_id: UUID) -> None:
        """
        Raises AccessDeniedError if user may not query this patient.
        Returns None (implicitly) if access is permitted.
        """
        user_role = getattr(user, "role", None)
        if user_role == UserRole.HOSPITAL_ADMIN or user_role == "hospital_admin":
            return

        if user_role in (UserRole.DOCTOR, UserRole.NURSE, "doctor", "nurse"):
            access_list = getattr(user, "patient_access", []) or []
            if str(patient_id) in access_list:
                return

            log.warning(
                "rag.access_denied",
                user_id=str(user.id),
                user_role=str(user.role),
                patient_id=str(patient_id),
            )
            raise AccessDeniedError(
                f"User {user.id} ({user.role}) is not authorized to access patient {patient_id}"
            )

        log.warning(
            "rag.access_denied",
            user_id=str(getattr(user, "id", "")),
            user_role=str(user_role),
            patient_id=str(patient_id),
        )
        raise AccessDeniedError(
            f"Role '{user_role}' is not permitted to use the RAG query endpoint"
        )
