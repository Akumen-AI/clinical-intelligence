from fastapi import Request, HTTPException, status, Depends
from typing import Dict, Set, Union
from app.core.security import get_current_user, User
from app.models.user import UserRole

import re

# Declarative table mapping route prefixes to allowed roles
RBAC_MATRIX: Dict[str, Union[Set[UserRole], Dict[str, Set[UserRole]]]] = {
    # Intake & Validation (Upload, Layout, Fields, Timeline, Canonical Records, Review)
    "/api/v1/documents/{id}/extract": {
        "POST": {UserRole.NURSE}
    },
    "/api/v1/documents/config/watched-folder": {UserRole.HOSPITAL_ADMIN},
    "/api/v1/documents/upload-logs": {UserRole.COMPLIANCE},
    "/api/v1/documents": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/timeline": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/canonical-records": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/review": {
        "GET": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
        "PATCH": {UserRole.NURSE},
        "PUT": {UserRole.HOSPITAL_ADMIN}
    },
    "/api/v1/dashboards": {UserRole.HOSPITAL_ADMIN, UserRole.DEPARTMENT_HEAD},
    "/api/v1/dashboards/patient": {UserRole.DOCTOR, UserRole.HOSPITAL_ADMIN},

    # Patients (read, create, update, ask)
    "/api/v1/patients/{id}/ask": {UserRole.DOCTOR},
    "/api/v1/patients": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    
    # Policy Chatbot
    "/api/v1/policy-chat/upload": {UserRole.HOSPITAL_ADMIN, UserRole.IT, UserRole.COMPLIANCE},
    "/api/v1/policy-chat": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    
    # Audit Logs (correction-logs)
    "/api/v1/correction-logs": {UserRole.HOSPITAL_ADMIN, UserRole.COMPLIANCE},
    "/api/v1/audit-log": {UserRole.COMPLIANCE},
    
    # Notes (Per-method configuration)
    "/api/v1/notes": {
        "POST": {UserRole.DOCTOR, UserRole.NURSE},
        "GET": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN, UserRole.DEPARTMENT_HEAD}
    },
    
    # RAG Context Compliance
    "/api/v1/rag": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
    "/api/v1/context-panel": {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN},
}

def check_rbac(request: Request, current_user: User = Depends(get_current_user)):
    """
    Centralized RBAC dependency that resolves the JWT once and validates
    the user's role against the declarative RBAC_MATRIX.
    """
    path = request.url.path
    
    best_match = ""
    allowed_roles = set()
    for prefix, config in RBAC_MATRIX.items():
        pattern = "^" + re.sub(r'\{[^}]+\}', '[^/]+', prefix)
        if re.match(pattern, path) and len(prefix) > len(best_match):
            best_match = prefix
            if isinstance(config, dict):
                allowed_roles = config.get(request.method, set())
            else:
                allowed_roles = config
            
    if not allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: no role mapping found for this endpoint."
        )
        
    user_role = current_user.role
    if isinstance(user_role, str):
        try:
            user_role = UserRole(user_role)
        except ValueError:
            pass
            
    if user_role not in allowed_roles:
        role_val = getattr(user_role, "value", user_role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: role '{role_val}' is not permitted for this endpoint."
        )
        
    request.state.user = current_user
    return current_user
