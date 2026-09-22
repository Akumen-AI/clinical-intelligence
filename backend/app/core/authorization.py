from enum import Enum
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
import structlog

from app.models.user import UserRole
from app.core.security import User
from app.models.document import Document
from app.models.patient import Patient

log = structlog.get_logger(__name__)

class ResourceType(str, Enum):
    PATIENT = "patient"
    DOCUMENT = "document"
    DASHBOARD = "dashboard"
    REPORT = "report"
    AUDIT_LOG = "audit_log"
    SYSTEM_CONFIG = "system_config"

class Operation(str, Enum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EXPORT = "export"

class AuthorizationService:
    @staticmethod
    def _has_global_access(user: User, resource: ResourceType, operation: Operation) -> bool:
        """Evaluate access against the authorization matrix for global roles."""
        role = getattr(user, "role", None)

        if role in (UserRole.HOSPITAL_ADMIN, "hospital_admin"):
            return True

        if role in (UserRole.COMPLIANCE, "compliance"):
            if resource == ResourceType.AUDIT_LOG and operation in (Operation.READ, Operation.EXPORT):
                return True
            return False

        if role in (UserRole.IT, "it"):
            if resource == ResourceType.SYSTEM_CONFIG:
                return True
            return False

        return False

    @staticmethod
    def assert_can_access_patient(user: User, patient_id: str, operation: Operation = Operation.READ) -> None:
        """
        Verify the user has permission to perform the operation on the specified patient.
        """
        if AuthorizationService._has_global_access(user, ResourceType.PATIENT, operation):
            return

        role = getattr(user, "role", None)
        
        # Doctor / Nurse checks
        if role in (UserRole.DOCTOR, UserRole.NURSE, "doctor", "nurse"):
            if operation not in (Operation.READ, Operation.WRITE):
                log.warning("authz.access_denied", user_id=str(user.id), role=str(role), resource="patient", operation=operation.value)
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted to perform this operation.")
            
            patient_access = getattr(user, "patient_access", []) or []
            if patient_id in patient_access:
                return
            
            log.warning("authz.access_denied", user_id=str(user.id), role=str(role), resource="patient", patient_id=patient_id)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to access patient {patient_id}")
        
        log.warning("authz.access_denied", user_id=str(user.id), role=str(role), resource="patient", patient_id=patient_id)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted to access patient records.")

    @staticmethod
    def assert_can_access_document(db: Session, user: User, document_id: str, operation: Operation = Operation.READ) -> None:
        """
        Verify the user has permission to perform the operation on the specified document.
        Uses the document's patient_id to determine access if it is linked.
        """
        if AuthorizationService._has_global_access(user, ResourceType.DOCUMENT, operation):
            return

        role = getattr(user, "role", None)

        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

        # If a document is unlinked, doctors/nurses can generally access it (for the purpose of reviewing/linking)
        # But let's restrict it to write operations for linking, or read operations.
        if doc.patient_id is None:
            if role in (UserRole.DOCTOR, UserRole.NURSE, "doctor", "nurse"):
                return
            else:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted to access unlinked documents.")

        # If it is linked, defer to patient access.
        AuthorizationService.assert_can_access_patient(user, doc.patient_id, operation)

    @staticmethod
    def assert_can_access_dashboard(user: User, department: Optional[str] = None) -> None:
        """
        Verify the user has permission to view the operational dashboards.
        """
        if AuthorizationService._has_global_access(user, ResourceType.DASHBOARD, Operation.READ):
            return

        role = getattr(user, "role", None)
        
        if role in (UserRole.DEPARTMENT_HEAD, "department_head"):
            if not department:
                log.warning("authz.access_denied", user_id=str(user.id), role=str(role), reason="Department Heads cannot access the hospital-wide dashboard.")
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Department Heads are not authorized to view the hospital-wide dashboard.")
            
            import json
            department_access = getattr(user, "department_access", []) or []
            if isinstance(department_access, str):
                try:
                    department_access = json.loads(department_access)
                except json.JSONDecodeError:
                    pass
            
            if department in department_access:
                return
            
            log.warning("authz.access_denied", user_id=str(user.id), role=str(role), resource="dashboard", department=department)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to view dashboard for department '{department}'.")
        
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted to access operational dashboards.")

    @staticmethod
    def assert_can_export_report(user: User, department: Optional[str] = None) -> None:
        """
        Verify the user has permission to export reports.
        """
        if AuthorizationService._has_global_access(user, ResourceType.REPORT, Operation.EXPORT):
            return
            
        role = getattr(user, "role", None)
        
        if role in (UserRole.DEPARTMENT_HEAD, "department_head"):
            if not department:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Department Heads cannot export hospital-wide reports.")
            
            print("DEPT:", repr(department), "ACCESS:", repr(department_access), "TYPE:", type(department_access), "ROLE:", repr(role))

            department_access = getattr(user, "department_access", []) or []
            if department in department_access:
                return
            
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Not authorized to export reports for department '{department}'.")

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted to export reports.")

    @staticmethod
    def assert_can_access_audit_logs(user: User) -> None:
        if AuthorizationService._has_global_access(user, ResourceType.AUDIT_LOG, Operation.READ):
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted to read audit logs.")

    @staticmethod
    def assert_can_access_system_config(user: User, operation: Operation) -> None:
        if AuthorizationService._has_global_access(user, ResourceType.SYSTEM_CONFIG, operation):
            return
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Role not permitted to access system configuration.")

