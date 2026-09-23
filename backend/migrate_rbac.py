import glob
import re

files_to_fix = [
    "app/api/canonical_records.py",
    "app/api/timeline.py",
    "app/api/v1/patient_dashboards.py",
    "app/routers/rag_context_compliance.py",
    "app/routers/review.py",
    "app/services/rag_service.py"
]

for filepath in files_to_fix:
    with open(filepath, "r") as f:
        content = f.read()

    # Imports
    content = re.sub(
        r"from app\.core\.patient_access_guard import RbacAccessGuard.*",
        "from app.core.authorization import AuthorizationService, ResourceType, Operation\nfrom fastapi import HTTPException",
        content
    )
    content = content.replace("from app.core.patient_access_guard import AccessDeniedError", "from fastapi import HTTPException")

    # AccessDeniedError -> HTTPException(status_code=403, detail="...")
    content = re.sub(r"raise AccessDeniedError\((.*?)\)", r"raise HTTPException(status_code=403, detail=\1)", content)

    # RbacAccessGuard usage
    # E.g. RbacAccessGuard.check_patient_access(current_user, patient_id)
    content = re.sub(
        r"RbacAccessGuard\.check_patient_access\(([^,]+),\s*([^)]+)\)",
        r"AuthorizationService.verify_access(\1, ResourceType.PATIENT, Operation.READ, \2)",
        content
    )

    with open(filepath, "w") as f:
        f.write(content)

import os
if os.path.exists("app/core/patient_access_guard.py"):
    os.remove("app/core/patient_access_guard.py")
if os.path.exists("tests/core/test_patient_access_guard.py"):
    os.remove("tests/core/test_patient_access_guard.py")
