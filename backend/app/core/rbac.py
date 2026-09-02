from fastapi import Request, HTTPException, status, Depends
from typing import Dict, Set
from app.core.security import get_current_user, User
from app.models.user import UserRole

# Declarative table mapping route prefixes to allowed roles
RBAC_MATRIX: Dict[str, Set[UserRole]] = {
    # Intake & Validation (Upload, Layout, Fields, Timeline, Canonical Records, Review)
    "/api/v1/documents": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/layout": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/fields": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/timeline": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/canonical-records": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/review": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/dashboards": {UserRole.HOSPITAL_ADMIN, UserRole.DEPARTMENT_HEAD},

    # Patients (read, create, update, ask)
    "/api/v1/patients": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    
    # Dashboards
    "/api/v1/dashboards": {UserRole.DOCTOR, UserRole.HOSPITAL_ADMIN},
    
    # Policy Chatbot
    "/api/v1/policy-chat/upload": {UserRole.HOSPITAL_ADMIN, UserRole.IT, UserRole.COMPLIANCE},
    "/api/v1/policy-chat": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    
    # Audit Logs (correction-logs)
    "/api/v1/correction-logs": {UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE},
    "/api/v1/audit-log": {UserRole.COMPLIANCE},
}

def check_rbac(request: Request, current_user: User = Depends(get_current_user)):
    """
    Centralized RBAC dependency that resolves the JWT once and validates
    the user's role against the declarative RBAC_MATRIX.
    """
    path = request.url.path
    
    best_match = ""
    allowed_roles = set()
    for prefix, roles in RBAC_MATRIX.items():
        if path.startswith(prefix) and len(prefix) > len(best_match):
            best_match = prefix
            allowed_roles = roles
            
    if not allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: no role mapping found for this endpoint."
        )
        
    if current_user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: role '{current_user.role.value}' is not permitted for this endpoint."
        )
        
    request.state.user = current_user
    return current_user
