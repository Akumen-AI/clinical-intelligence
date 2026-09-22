import glob
import re
import os

files_to_fix = [
    "app/api/canonical_records.py",
    "app/api/timeline.py",
    "app/api/v1/patient_dashboards.py",
    "app/routers/rag_context_compliance.py",
    "app/routers/review.py",
    "app/services/rag_service.py"
]

for filepath in files_to_fix:
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r") as f:
        content = f.read()

    # E.g. RbacAccessGuard().assert_can_query_patient(current_user, patient_id)
    # E.g. RbacAccessGuard().assert_can_query_patient(http_request.state.user, doc.patient_id if doc else None)
    content = re.sub(
        r"RbacAccessGuard\(\)\.assert_can_query_patient\(([^,]+),\s*([^)]+)\)",
        r"AuthorizationService.verify_access(\1, ResourceType.PATIENT, Operation.READ, \2)",
        content
    )

    with open(filepath, "w") as f:
        f.write(content)
